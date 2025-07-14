from app.utils.cacao import (
    field_config_mapping,
)
from jellyfish import damerau_levenshtein_distance


# This assumes a syntactically valid CACAO playbook
def evaluate_playbook(translation, ground_truth):
    return {
        "metadata": evaluate_metadata(translation, ground_truth),
        "workflow": evaluate_workflow(
            translation["workflow"], ground_truth["workflow"]
        ),
        "variables": evaluate_variables(
            translation["playbook_variables"], ground_truth["playbook_variables"]
        ),
    }


def evaluate_metadata(
    translation, ground_truth, fields_to_evaluate=field_config_mapping.keys()
):
    similarities = {
        "name": damerau_levenshtein_similarity,
        "description": damerau_levenshtein_similarity,
        "playbook_types": array_similarity,
        "playbook_activities": array_similarity,
        "labels": array_similarity,
        "created": damerau_levenshtein_similarity,
        "modified": damerau_levenshtein_similarity,
    }
    scores = {
        field: round(
            evaluate_similarity(field, ground_truth, translation, similarities), 2
        )
        for field in fields_to_evaluate
    }
    total = round(sum(scores.values()) / len(scores), 2)

    return scores | {"total": total}


# Recall
def array_similarity(a, b):
    if not a or not b:
        return 0

    true_positives = sum(x in b for x in a)
    false_negatives = sum(x not in b for x in a)

    if true_positives + false_negatives == 0:
        return 0

    return true_positives / (true_positives + false_negatives)

def evaluate_workflow(translation_workflow, ground_truth_workflow):
    scores = {}
    total = 0

    if len(ground_truth_workflow.items()) == 0:
        return {
            "total": 1 if len(translation_workflow.items()) == 0 else 0,
        }

    for step_id, step in ground_truth_workflow.items():
        evaluation = evaluate_step(step, translation_workflow, ground_truth_workflow)
        scores[step_id] = evaluation["score"]
        total += evaluation["total"]
    total = round(round(total, 2) / len(ground_truth_workflow.items()), 2)

    return scores | {"grouped": group_by_field(scores)} | {"total": total}


def group_by_field(scores):
    grouped = {}
    for score in scores.values():
        for field, value in score.items():
            if field not in grouped:
                grouped[field] = []
            grouped[field].append(value)
    for field, values in grouped.items():
        grouped[field] = round(sum(values) / len(values), 2)
    return grouped


def evaluate_step(step, translation_workflow, ground_truth_workflow):
    evaluation = {"identification": 0}
    evaluated_fields_count = 1

    if "name" not in step and "type" not in step:
        return construct_score(evaluation, evaluated_fields_count)

    similarities = get_workflow_similarities(
        {
            "ground_truth_workflow": ground_truth_workflow,
            "translation_workflow": translation_workflow,
        }
    )

    translated_step_id = identify_step(step, translation_workflow, similarities)

    if translated_step_id is None:
        return construct_score(evaluation, evaluated_fields_count)

    translated_step = translation_workflow[translated_step_id]
    if translated_step is None:
        return construct_score(evaluation, evaluated_fields_count)

    evaluation["identification"] = 1

    evaluation["name"] = evaluate_similarity(
        "name", step, translated_step, similarities
    )
    evaluated_fields_count += 1

    fields_to_evaluate = [
        "description",
        "type",
    ]
    evaluated_fields_count += len(fields_to_evaluate)

    for field in fields_to_evaluate:
        evaluation[field] = evaluate_similarity(
            field, step, translated_step, similarities
        )

    if step["type"] == "if-condition":
        fields_to_evaluate = ["condition"]
        evaluated_fields_count += len(fields_to_evaluate)

        for field in fields_to_evaluate:
            evaluation[field] = evaluate_similarity(
                field, step, translated_step, similarities
            )

    return construct_score(evaluation, evaluated_fields_count)


def construct_score(evaluation, evaluated_fields_count):
    evaluation["total"] = round(sum(evaluation.values()) / evaluated_fields_count, 2)

    return {
        "score": {key: round(value, 2) for key, value in evaluation.items()},
        "total": evaluation["total"],
    }


def damerau_levenshtein_similarity(a, b):
    if not a or not b:
        return 0
    return 1 - round(damerau_levenshtein_distance(a, b) / max(len(a), len(b)), 2)


def absolute_similarity(a, b):
    return a == b


def identify_step(ground_truth_step, translation_workflow, similarities):
    max = 0
    found_step_id = None
    for step_id, step in translation_workflow.items():
        similarity_value = evaluate_similarity(
            "name", ground_truth_step, step, similarities
        )
        if similarity_value > max:
            max = similarity_value
            found_step_id = step_id

    threshold = 0.5
    if max >= threshold:
        return found_step_id

    # Find by type and name
    max = 0
    found_step_id = None
    for step_id, step in translation_workflow.items():
        name_similarity_value = evaluate_similarity(
            "name", ground_truth_step, step, similarities
        )
        type_similarity_value = evaluate_similarity(
            "type", ground_truth_step, step, similarities
        )
        if name_similarity_value >= max and type_similarity_value:
            max = name_similarity_value
            found_step_id = step_id

    threshold = 0.15
    if max >= threshold:
        return found_step_id

    return None


def evaluate_similarity(field, ground_truth, translation, similarities):
    metric = similarities[field]
    if field not in ground_truth:
        if field not in translation:
            return 1
        return 0
    if field not in translation:
        return 0

    if ground_truth[field] is None and translation[field] is None:
        return 1

    return metric(
        ground_truth[field],
        translation[field],
    )


def get_workflow_similarities(context):
    similarities = {
        "name": damerau_levenshtein_similarity,
        "description": damerau_levenshtein_similarity,
        "type": absolute_similarity,
    }

    def id_metric(id_a, id_b):
        if id_b not in context["translation_workflow"]:
            return 0

        ground_truth_step = context["ground_truth_workflow"][id_a]

        test_workflow = {id_b: context["translation_workflow"][id_b]}
        identified_id = identify_step(ground_truth_step, test_workflow, similarities)
        return 1 if identified_id == id_b else 0

    def multiple_id_metric(ids_a, ids_b):
        pointer_count = 0
        for id_a in ids_a:
            # Variant 1 based on identify_step
            ground_truth_step = context["ground_truth_workflow"][id_a]
            test_workflow = {
                id_b: context["translation_workflow"][id_b] for id_b in ids_b
            }
            identified_id = identify_step(
                ground_truth_step, test_workflow, similarities
            )
            pointer_count += 1 if identified_id == id_a else 0

        return pointer_count

    return similarities | {
        "on_completion": id_metric,
        "on_success": id_metric,
        "on_failure": id_metric,
        "condition": damerau_levenshtein_similarity,
        "on_true": id_metric,
        "on_false": id_metric,
        "next_steps": multiple_id_metric,
    }


def evaluate_variables(translation_variables, ground_truth_variables):
    scores = {}
    total = 0
    if len(ground_truth_variables.items()) == 0:
        return {
            "total": 1 if len(translation_variables.items()) == 0 else 0,
        }

    for variable_name, variable in ground_truth_variables.items():
        evaluation = evaluate_variable(variable_name, variable, translation_variables)
        scores[variable_name] = evaluation["score"]
        total += evaluation["total"]
    total = round(round(total, 2) / len(ground_truth_variables.items()), 2)

    return scores | {"grouped": group_by_field(scores)} | {"total": total}


def evaluate_variable(variable_name, variable, translation_variables):
    evaluation = {"identification": 0}
    evaluated_fields_count = 1

    similarities = {
        "name": strip_name_damerau_levenshtein_similarity,
        "description": damerau_levenshtein_similarity,
        "type": absolute_similarity,
        "value": damerau_levenshtein_similarity,
        "constant": absolute_similarity,
        "external": absolute_similarity,
    }

    translated_variable_name = identify_variable(
        variable_name, translation_variables, similarities
    )

    if translated_variable_name is None:
        return construct_score(evaluation, evaluated_fields_count)

    translated_variable = translation_variables[translated_variable_name]
    if translated_variable is None:
        return construct_score(evaluation, evaluated_fields_count)

    evaluation["identification"] = 1

    evaluation["name"] = similarities["name"](variable_name, translated_variable_name)
    evaluated_fields_count += 1

    fields_to_evaluate = [
        "description",
        "type",
        "value",
        "constant",
        "external",
    ]
    evaluated_fields_count += len(fields_to_evaluate)

    for field in fields_to_evaluate:
        evaluation[field] = evaluate_similarity(
            field, variable, translated_variable, similarities
        )

    return construct_score(evaluation, evaluated_fields_count)


def identify_variable(ground_truth_name, translation_variables, similarities):
    max = 0
    found_variable_name = None
    for translation_variable_name in translation_variables.keys():
        similarity_value = similarities["name"](
            ground_truth_name, translation_variable_name
        )
        if similarity_value > max:
            max = similarity_value
            found_variable_name = translation_variable_name

    threshold = 0.5
    if max >= threshold:
        return found_variable_name

    return None


def strip_name_damerau_levenshtein_similarity(name_a, name_b):
    stripped_a = name_a[2:-2]
    stripped_b = name_b[2:-2]
    return damerau_levenshtein_similarity(stripped_a, stripped_b)
