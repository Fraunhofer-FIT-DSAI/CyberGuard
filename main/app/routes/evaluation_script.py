from typing import Literal
from langserve import CustomUserType
import time
import os
from app.routes.main import OPEN_SOURCE_MODELS
from app.utils.files import get_file_content
from app.evaluation.semantic import evaluate_playbook as semantic_evaluate_playbook
from app.evaluation.syntactic import evaluate_playbook as syntactic_evaluate_playbook
from app.evaluation.graph import handler as graph_evaluation
from app.routes.translation_script import (
    Case,
    Model,
    Dependencies as TranslationDependencies,
)
from app.utils.db import export, retrieve


cases = get_file_content("./app/evaluation/cases.json")
playbooks_to_evaluate = get_file_content(
    "../playbooks/evaluation_dataset/playbooks.json"
)


class Dependencies(CustomUserType):
    model: Model = "llama3.1"
    translation_table = "translation"
    evaluation_table = "evaluation"
    flow: Literal["syntactic", "semantic"] = "syntactic"


def handler(dependencies: Dependencies):
    evaluation_table_name = f"{dependencies.flow}_{dependencies.evaluation_table}"

    for case_name, case in cases.items():
        case = cases[case_name]
        translation_dependencies = TranslationDependencies.from_dict(
            {
                "prompt_patterns": case,
                "is_open_source": dependencies.model in OPEN_SOURCE_MODELS,
                "model": dependencies.model,
            }
        )
        performed_iterations = 0
        for vendor, playbooks in playbooks_to_evaluate.items():
            for playbook_type, playbooks_list in playbooks.items():
                for playbook_name in playbooks_list:
                    performed_iterations += 1
                    if (
                        dependencies.flow == "semantic"
                        and playbook_type == "non_translated"
                    ):
                        print(
                            f"Skipping semantic evaluation for playbook {playbook_name} from {vendor} iteration {performed_iterations}"
                        )
                        continue

                    translation_dependencies.playbook_file_name = playbook_name
                    translation = retrieve(
                        translation_dependencies,
                        table=dependencies.translation_table,
                        model=dependencies.model,
                    )

                    if not translation:
                        print(
                            f"Translation for playbook {playbook_name} from {vendor} not found iteration {performed_iterations}"
                        )
                        continue

                    evaluation = retrieve(
                        translation_dependencies,
                        table=evaluation_table_name,
                        model=dependencies.model,
                    )
                    if evaluation:
                        print(
                            f"Evaluation for playbook {playbook_name} from {vendor} already exists iteration {performed_iterations}"
                        )
                        continue

                    result = None
                    start_time = time.time()
                    print(
                        f"Evaluating playbook {playbook_name} from {vendor} iteration {performed_iterations}"
                    )

                    if dependencies.flow == "syntactic":
                        result = syntactic_evaluate_playbook(translation["result"])
                    if dependencies.flow == "semantic":
                        ground_truth = get_structured_playbook(playbook_name, vendor)
                        semantic_result = semantic_evaluate_playbook(
                            translation["result"], ground_truth
                        )
                        graph_result = graph_evaluation(
                            translation["result"]["workflow"], ground_truth["workflow"]
                        )
                        result = semantic_result | graph_result

                        syntactic_refinement_result = retrieve(
                            translation_dependencies,
                            table="syntactic_refinement",
                            model=dependencies.model,
                        )

                        if not syntactic_refinement_result:
                            print(
                                f"Syntactic refinement for playbook {playbook_name} from {vendor} not found iteration {performed_iterations}"
                            )
                        else:   
                            table_name = f"{evaluation_table_name}_syntactic_refinement"
                            syntactic_refinement_semantic_evaluation = retrieve(
                                translation_dependencies,
                                table=table_name,
                                model=dependencies.model,
                            )
                            if syntactic_refinement_semantic_evaluation:
                                print(
                                    f"Syntactic Refinement Evaluation for playbook {playbook_name} from {vendor} already exists iteration {performed_iterations}"
                                )
                                continue
                            best_result = get_best_result(syntactic_refinement_result)

                            try:
                                semantic_result = semantic_evaluate_playbook(
                                    best_result["result"], ground_truth
                                )
                            except Exception:
                                semantic_result = {
                                    "metadata": {"total": 0},
                                    "workflow": {"total": 0},
                                    "variables": {"total": 0},
                                }
                            graph_result = graph_evaluation(
                                best_result["result"]["workflow"], ground_truth["workflow"]
                            )

                            export(
                                translation_dependencies,
                                semantic_result | graph_result,
                                0,
                                table=table_name,
                                model=dependencies.model,
                            )

                    end_time = time.time()

                    total_time = round(end_time - start_time, 2)

                    export(
                        translation_dependencies,
                        result,
                        total_time,
                        table=evaluation_table_name,
                        model=dependencies.model,
                    )


def get_structured_playbook(playbook_file_name, vendor):
    file_name_without_extension = os.path.splitext(playbook_file_name)[0]
    unstructured_path = f"../playbooks/semantic_evaluation_dataset/{vendor}/{file_name_without_extension}.json"
    return get_file_content(unstructured_path)


def get_best_result(syntactic_refinement_result):
    best_result = min(
        syntactic_refinement_result["result"],
        key=lambda x: (
            x["evaluation"]["length"] if x["evaluation"] is not None else 1000000
        ),
    )
    did_fail_in_the_end = syntactic_refinement_result["errors"]

    return {
        "result": best_result["result"],
        "length": best_result["evaluation"]["length"],
        "errors": did_fail_in_the_end,
    }
