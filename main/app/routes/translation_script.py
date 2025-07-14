import time
from typing import Literal

from langserve import CustomUserType

from app.routes.main import (
    OPEN_SOURCE_MODELS,
    Dependencies,
    MetadataDependencies,
    PromptPatterns,
    WorkflowDependencies,
)
from app.utils.cacao_builder import get_start_step_id, insert_cacao_static_fields
from app.utils.db import export, remove, retrieve
from app.extraction.metadata import extract_metadata
from app.extraction.variables import extract_variables
from app.extraction.workflow import extract_workflow
from app.utils.files import get_file_content
from app.utils.tokens import TokenManager
from app.extraction.syntactic_refinement import syntactic_refinement 

Model = Literal[
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-2024-08-06",
    "llama3.1",
]

Case = Literal[
    "baseline",
    "persona",
    "reason",
    "knowledge",
    "one_shot",
    "all_without_one_shot",
    "strongest",
]

cases = get_file_content("./app/evaluation/cases.json")
playbooks_to_evaluate = get_file_content(
    "../playbooks/evaluation_dataset/playbooks.json"
)


class Dependencies(CustomUserType):
    model: Model = "llama3.1"
    playbook_file_name: str = ""
    ignore_cache: bool = True
    should_export_db: bool = False
    is_open_source: bool = False
    temperature: float = 0.0
    include_post_processing: bool = True
    metadata: MetadataDependencies
    workflow: WorkflowDependencies
    prompt_patterns: PromptPatterns

    def to_dict(self):
        return {
            "model": self.model,
            "playbook_file_name": self.playbook_file_name,
            "ignore_cache": self.ignore_cache,
            "should_export_db": self.should_export_db,
            "is_open_source": self.is_open_source,
            "temperature": self.temperature,
            "include_post_processing": self.include_post_processing,
            "metadata": self.metadata.to_dict(),
            "workflow": self.workflow.to_dict(),
            "prompt_patterns": self.prompt_patterns.to_dict(),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            playbook_file_name=data.get("playbook_file_name", ""),
            model=data.get("model", "llama3.1"),
            ignore_cache=data.get("ignore_cache", True),
            is_open_source=data.get("is_open_source", False),
            should_export_db=data.get("should_export_db", False),
            temperature=data.get("temperature", 0.0),
            include_post_processing=data.get("include_post_processing", True),
            metadata=MetadataDependencies.from_dict(data.get("metadata", {})),
            workflow=WorkflowDependencies.from_dict(data.get("workflow", {})),
            prompt_patterns=PromptPatterns.from_dict(data.get("prompt_patterns", {})),
        )


class CustomDependencies(CustomUserType):
    model: Model = "llama3.1"
    case: Case = "baseline"
    table_to_export = "translation"


def handler(dependencies: CustomDependencies):
    # for case_name, case in cases.items():
    case_name = dependencies.case
    case = cases[case_name]

    translation_dependencies = Dependencies.from_dict(
        {
            "prompt_patterns": case,
            "is_open_source": dependencies.model in OPEN_SOURCE_MODELS,
            "model": dependencies.model,
        }
    )
    performed_iterations = 0
    for vendor, playbooks in playbooks_to_evaluate.items():
        for playbooks_list in playbooks.values():
            for playbook_name in playbooks_list:
                try:
                    performed_iterations += 1
                    translation_dependencies.playbook_file_name = playbook_name

                    translation = retrieve(
                        translation_dependencies, table=dependencies.table_to_export, model=dependencies.model
                    )
                    unstructured_playbook_content = get_unstructured_playbook(playbook_name, vendor)
                    if should_skip_translation(translation):
                        print(
                            f"Case {case_name}: Playbook {playbook_name} from {vendor} already translated iteration {performed_iterations}"
                        )
                        
                        syntactic_refinement = retrieve(
                            translation_dependencies, table="syntactic_refinement", model=dependencies.model
                        )
                        if syntactic_refinement is not None:
                            print(
                                f"Case {case_name}: Syntactic refinement for playbook {playbook_name} from {vendor} already exists iteration {performed_iterations}"
                            )
                            continue    

                        handle_syntactic_refinement(unstructured_playbook_content, translation["result"], translation_dependencies,table_to_export="syntactic_refinement",
                        model=dependencies.model)
                        
                        continue
                    remove(translation_dependencies, table=dependencies.table_to_export, model=dependencies.model)
                    print(
                        f"Case {case_name}: Translating playbook {playbook_name} from {vendor} iteration {performed_iterations}"
                    )

                    translate_playbook(
                        translation_dependencies,
                        unstructured_playbook_content,
                        table_to_export=dependencies.table_to_export,
                        model=dependencies.model,
                    )
                    print(
                        f"Case {case_name}: Successfully translated playbook {playbook_name} from {vendor} iteration {performed_iterations}"
                    )
                except Exception as e:
                    print(
                        f"Case {case_name}: Error translating playbook {playbook_name}: {str(e)} iteration {performed_iterations}"
                    )
                    raise

    

def translate_playbook(dependencies, unstructured_playbook_content, table_to_export,model):
    start_time = time.time()
    token_manager = TokenManager(
        model=dependencies.model,
    )
    print("Extracting metadata started")
    metadata_result = extract_metadata(
        unstructured_playbook_content,
        token_manager,
        dependencies,
    )
    print(f"Extracting metadata finished {"successfully" if metadata_result.get("error", None) is None else "with error"}")

    print("Extracting workflow started")
    workflow_result = extract_workflow(
        unstructured_playbook_content, token_manager, dependencies
    )
    print(f"Extracting workflow finished {"successfully" if workflow_result.get("error", None) is None else "with error"}")

    print("Extracting variables started")
    variables_result = extract_variables(
        unstructured_playbook_content, token_manager, dependencies
    )
    print(f"Extracting variables finished {"successfully" if variables_result.get("error", None) is None else "with error"}")

    playbook = insert_cacao_static_fields(
        metadata_result["cacao_playbook"]
        | {
            "workflow_start": get_start_step_id(workflow_result["workflow"]),
            "workflow": workflow_result["workflow"],
        }
        | {"playbook_variables": variables_result["playbook_variables"]}
    )

    end_time = time.time()
    total_time = round(end_time - start_time, 2)

    tokens = (
        {"metadata_tokens": metadata_result["tokens"]}
        | {"workflow_tokens": workflow_result["tokens"]}
        | {"variable_tokens": variables_result["tokens"]}
    )

    errors = (
        {"metadata_error": metadata_result.get("error", None)}
        | {"workflow_error": workflow_result.get("error", None)}
        | {"variable_error": variables_result.get("error", None)}
    )

    export(
        dependencies, playbook, total_time, tokens, errors=errors, table=table_to_export, model=model
    )

    return playbook

def handle_syntactic_refinement(unstructured_playbook_content,translation, dependencies, table_to_export,model):
    start_time = time.time()
    token_manager = TokenManager(
        model=model,
    )
    print("Syntactic Refinement started")
    result = syntactic_refinement(unstructured_playbook_content,translation,token_manager,dependencies,threshold=5)
    print("Syntactic Refinement ended")
    
    end_time = time.time()
    total_time = round(end_time - start_time, 2)
    tokens = result["tokens"]

    export(
        dependencies, result["results"], total_time, tokens, errors=result["error"], table=table_to_export, model=model
    )


def get_unstructured_playbook(playbook_file_name, vendor):
    unstructured_path = f"../playbooks/evaluation_dataset/{vendor}/{playbook_file_name}"
    return get_file_content(unstructured_path)


def should_skip_translation(translation):
    return (
        translation is not None
        and translation["errors"]["metadata_error"] is None
        and translation["errors"]["workflow_error"] is None
        and translation["errors"]["variable_error"] is None
    )
