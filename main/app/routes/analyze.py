from langserve import CustomUserType

from app.routes.main import OPEN_SOURCE_MODELS
from app.utils.files import get_file_content
from app.routes.translation_script import (
    Dependencies as TranslationDependencies,
    Model,
)
from app.utils.db import export_result, retrieve
from app.routes.evaluation_script import get_best_result


cases = get_file_content("./app/evaluation/cases.json")
playbooks_to_evaluate = get_file_content(
    "../playbooks/evaluation_dataset/playbooks.json"
)


class Dependencies(CustomUserType):
    model: Model = "llama3.1"
    translation_table = "translation"
    evaluation_table = "evaluation"


def handler(dependencies: Dependencies):
    results_per_case = {}

    for case_name, case in cases.items():
        evaluated_semantic_playbooks = 0
        evaluated_syntactic_playbooks = 0
        results_per_case[case_name] = {
            "original": {
                "metadata": {"total": 0, "data": []},
                "workflow": {"total": 0, "data": []},
                "variables": {"total": 0, "data": []},
                "graph_edit_distance": {"total": 0, "data": []},
                "syntactic": {"total": 0, "data": []},
            },
            "syntactic_refinement": {
                "metadata": {"total": 0, "data": []},
                "workflow": {"total": 0, "data": []},
                "variables": {"total": 0, "data": []},
                "graph_edit_distance": {"total": 0, "data": []},
                "syntactic": {"total": 0, "data": []},
            },
            "time": {"total": 0, "data": []},
        }

        translation_dependencies = TranslationDependencies.from_dict(
            {
                "prompt_patterns": case,
                "is_open_source": dependencies.model in OPEN_SOURCE_MODELS,
                "model": dependencies.model,
            }
        )
        for playbooks in playbooks_to_evaluate.values():
            for playbooks_list in playbooks.values():
                for playbook_name in playbooks_list:
                    translation_dependencies.is_open_source = (
                        dependencies.model in OPEN_SOURCE_MODELS
                    )
                    translation_dependencies.playbook_file_name = playbook_name

                    translation = retrieve(
                        translation_dependencies,
                        table=dependencies.translation_table,
                        model=dependencies.model,
                    )
                    if not translation:
                        continue

                    semantic_evaluation = retrieve(
                        translation_dependencies,
                        table=f"semantic_{dependencies.evaluation_table}",
                        model=dependencies.model,
                    )
                    syntactic_evaluation = retrieve(
                        translation_dependencies,
                        table=f"syntactic_{dependencies.evaluation_table}",
                        model=dependencies.model,
                    )

                    syntactic_refinement_result = retrieve(
                        translation_dependencies,
                        table="syntactic_refinement",
                        model=dependencies.model,
                    )
                    semantic_evaluation_syntactic_refinement = retrieve(
                        translation_dependencies,
                        table="semantic_evaluation_syntactic_refinement",
                        model=dependencies.model,
                    )

                    results_per_case[case_name]["time"]["total"] += translation["time"]
                    results_per_case[case_name]["time"]["data"].append(
                        translation["time"]
                    )
                    if syntactic_evaluation:
                        results_per_case[case_name]["original"]["syntactic"][
                            "total"
                        ] += syntactic_evaluation["result"]["length"]
                        results_per_case[case_name]["original"]["syntactic"][
                            "data"
                        ].append(syntactic_evaluation["result"]["length"])

                        if syntactic_refinement_result:
                            best_result = get_best_result(syntactic_refinement_result)
                            results_per_case[case_name]["syntactic_refinement"][
                                "syntactic"
                            ]["total"] += best_result["length"]
                            results_per_case[case_name]["syntactic_refinement"][
                                "syntactic"
                            ]["data"].append(best_result["length"])

                        evaluated_syntactic_playbooks += 1

                    def update_semantic(type, evaluation):
                        results_per_case[case_name][type]["metadata"][
                            "total"
                        ] += evaluation["result"]["metadata"]["total"]
                        results_per_case[case_name][type]["metadata"]["data"].append(
                            evaluation["result"]["metadata"]["total"]
                        )

                        results_per_case[case_name][type]["workflow"][
                            "total"
                        ] += evaluation["result"]["workflow"]["total"]

                        results_per_case[case_name][type]["workflow"]["data"].append(
                            evaluation["result"]["workflow"]["total"]
                        )

                        results_per_case[case_name][type]["variables"][
                            "total"
                        ] += evaluation["result"]["variables"]["total"]
                        results_per_case[case_name][type]["variables"]["data"].append(
                            evaluation["result"]["variables"]["total"]
                        )

                        results_per_case[case_name][type]["graph_edit_distance"][
                            "total"
                        ] += evaluation["result"]["graph_edit_distance"]
                        results_per_case[case_name][type]["graph_edit_distance"][
                            "data"
                        ].append(evaluation["result"]["graph_edit_distance"])

                    if semantic_evaluation:
                        evaluated_semantic_playbooks += 1
                        update_semantic("original", semantic_evaluation)
                        if semantic_evaluation_syntactic_refinement:
                            update_semantic(
                                "syntactic_refinement",
                                semantic_evaluation_syntactic_refinement,
                            )

        

    export_result(results_per_case, model=dependencies.model)