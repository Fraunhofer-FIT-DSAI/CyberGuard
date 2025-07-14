from langserve.schema import CustomUserType
from typing import Literal

from app.utils.files import (
    get_unstructured_playbook_content,
)
from app.utils.tokens import TokenManager
from app.extraction.metadata import extract_metadata
from app.extraction.workflow import extract_workflow
from app.extraction.variables import extract_variables
from app.extraction.syntactic_refinement import syntactic_refinement
from app.utils.db import retrieve

CLOSED_SOURCE_MODELS = [
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "gpt-3.5-turbo-0125",
]

OPEN_SOURCE_MODELS = [
    "mistral",
    "llama3",
    "llama3.1",
]

Model = Literal[
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-05-13",
    "gpt-3.5-turbo-0125",
    "llama3",
    "llama3.1",
    "mistral",
]

AVAILABLE_UNSTRUCTURED_PLAYBOOKS = Literal[
    "text_playbook",
    "Alert - Update SLA Details.json",
    "playbook-Email_Address_Enrichment_Generic_Test.yml",
    "AWS_IAM_Account_Locking.json",
    "AWS_IAM_Account_Unlocking.json",
    "Cisco_Umbrella_DNS_Denylisting.json",
    "Splunk_Attack_Analyzer_Dynamic_Analysis.json",
    "test_splunk_parallel.json",
    "test_splunk_parallel2.json",
    "test_splunk_parallel_combined.json",
    "splunk_if_condition.json",
    "create_ticket.json",
    "log4j_respond.json",
    "ThreatQ - Email Reputation.json",
    "Approval - On Create.json",
    "playbook-IP_Enrichment_-_Generic_-_Test.yml"
]


Flow = Literal["metadata", "workflow", "variables", "syntactic_refinement"]


class WorkflowDependencies(CustomUserType):
    construct_parallel_steps: bool = False

    def to_dict(self):
        return {
            "construct_parallel_steps": self.construct_parallel_steps,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            construct_parallel_steps=data.get("construct_parallel_steps", False),
        )


class MetadataDependencies(CustomUserType):
    include_all_fields: bool = True
    fields_to_extract: list[str] = [""]
    use_rag: bool = False
    use_playbook_in_retriever: bool = False

    def to_dict(self):
        return {
            "include_all_fields": self.include_all_fields,
            "fields_to_extract": self.fields_to_extract,
            "use_rag": self.use_rag,
            "use_playbook_in_retriever": self.use_playbook_in_retriever,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            include_all_fields=data.get("include_all_fields", True),
            fields_to_extract=data.get("fields_to_extract", [""]),
            use_rag=data.get("use_rag", False),
            use_playbook_in_retriever=data.get("use_playbook_in_retriever", False),
        )


class SyntacticalRefinementDependencies(CustomUserType):
    iterations: int = 2

    def to_dict(self):
        return {
            "iterations": self.iterations,
        }


class PromptPatterns(CustomUserType):
    persona: bool = True

    class TemplatePattern(CustomUserType):
        answer_json: bool = True
        include_reason: bool = True

        reason_first: bool = True

        def to_dict(self):
            return {
                "answer_json": self.answer_json,
                "include_reason": self.include_reason,
                "reason_first": self.reason_first,
            }

        @classmethod
        def from_dict(cls, data):
            return cls(
                answer_json=data.get("answer_json", True),
                include_reason=data.get("include_reason", True),
                reason_first=data.get("reason_first", True),
            )

    template: bool = True
    template_config: TemplatePattern

    class ReasonPattern(CustomUserType):
        in_detail: bool = True

        def to_dict(self):
            return {
                "in_detail": self.in_detail,
            }

        @classmethod
        def from_dict(cls, data):
            return cls(
                in_detail=data.get("in_detail", True),
            )

    reason: bool = True
    reason_config: ReasonPattern

    knowledge_injection: bool = True

    include_few_shot_prompting: bool = False
    examples_to_include: int = 1

    def to_dict(self):
        return {
            "persona": self.persona,
            "template": self.template,
            "template_config": self.template_config.to_dict(),
            "reason": self.reason,
            "reason_config": self.reason_config.to_dict(),
            "knowledge_injection": self.knowledge_injection,
            "include_few_shot_prompting": self.include_few_shot_prompting,
            "examples_to_include": self.examples_to_include,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            persona=data.get("persona", True),
            template=data.get("template", True),
            template_config=cls.TemplatePattern.from_dict(
                data.get("template_config", {})
            ),
            reason=data.get("reason", True),
            reason_config=cls.ReasonPattern.from_dict(data.get("reason_config", {})),
            knowledge_injection=data.get("knowledge_injection", True),
            include_few_shot_prompting=data.get("include_few_shot_prompting", True),
            examples_to_include=data.get("examples_to_include", 1),
        )


class Dependencies(CustomUserType):
    flow: Flow = "metadata"
    playbook_file_name: AVAILABLE_UNSTRUCTURED_PLAYBOOKS = (
        "AWS_IAM_Account_Locking.json"
    )
    model: Model = "gpt-4o-mini-2024-07-18"
    text_content: str = ""
    ignore_cache: bool = False
    is_open_source: bool = False
    should_export_db: bool = False
    temperature: float = 0.0
    include_post_processing: bool = True
    metadata: MetadataDependencies
    workflow: WorkflowDependencies
    syntactical_refinement: SyntacticalRefinementDependencies
    prompt_patterns: PromptPatterns

    def to_dict(self):
        return {
            "flow": self.flow,
            "playbook_file_name": self.playbook_file_name,
            "model": self.model,
            "text_content": self.text_content,
            "ignore_cache": self.ignore_cache,
            "is_open_source": self.is_open_source,
            "include_post_processing": self.include_post_processing,
            "temperature": self.temperature,
            "metadata": self.metadata.to_dict(),
            "workflow": self.workflow.to_dict(),
            "prompt_patterns": self.prompt_patterns.to_dict(),
            "syntactical_refinement": self.syntactical_refinement.to_dict(),
        }


def handler(dependencies: Dependencies):
    dependencies.is_open_source = dependencies.model in OPEN_SOURCE_MODELS
    token_manager = TokenManager(
        model=dependencies.model,
    )

    unstructured_playbook_content = (
        get_unstructured_playbook_content(dependencies.playbook_file_name)
        if dependencies.text_content == ""
        else dependencies.text_content
    )
    
    if dependencies.flow == "metadata":
        return extract_metadata(
            unstructured_playbook_content,
            token_manager,
            dependencies,
        )
    if dependencies.flow == "workflow":
        return extract_workflow(
            unstructured_playbook_content, token_manager, dependencies
        )
    if dependencies.flow == "variables":
        return extract_variables(
            unstructured_playbook_content, token_manager, dependencies
        )

    if dependencies.flow == "syntactic_refinement":
        return syntactic_refinement(
            unstructured_playbook_content, token_manager, dependencies
        )

    return
