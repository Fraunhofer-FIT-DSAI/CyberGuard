import time

from app.evaluation.syntactic import evaluate_playbook as syntactic_evaluate_playbook
from app.extraction.utils import get_llm, get_prompt
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

from app.utils.prompts import (
    RESPONSE_FORMAT,
    filter_empty_spaces_and_new_lines,
    persona_pattern,
    zero_shot_cot,
    json_answer_prompt,
)
from app.utils.tokens import TokenManager
from app.utils.db import export


def syntactic_refinement(
    unstructured_playbook_content,
    translation,
    token_manager: TokenManager,
    dependencies,
    threshold,
):
    start_time = time.time()

    results = []

    results.append(
        {
            "result": translation,
            "evaluation": syntactic_evaluate_playbook(translation),
            "error_delta": 0,
        }
    )

    for iteration_id in range(threshold):
        initial_evaluation = syntactic_evaluate_playbook(translation)
        if initial_evaluation["length"] == 0:
            break

        errors = [
            {"message": error["message"], "path": error["path"]}
            for error in initial_evaluation["errors"]
        ]

        llm = get_llm(dependencies)

        prompt = get_prompt(
            [
                persona_pattern,
                json_answer_prompt,
                zero_shot_cot,
                ("human", "Playbook: {playbook}"),
                ("human", "Translation: {translation}"),
                ("human", "Question: {question}"),
                ("ai", "Answer: "),
            ]
        )

        question = filter_empty_spaces_and_new_lines(
            f"""
            You have received a semi-structured playbook and a corresponding translation for it. The translation contains several errors. Can you identify and correct the errors in the translation?
            Here are the errors: {errors}
            {RESPONSE_FORMAT}
                ```json {{
                    \"corrected_translation\": 
                        {{}}
                }}```
        """
        )
        chain_input = {
            "playbook": unstructured_playbook_content,
            "translation": translation,
            "question": question,
        }
        prompt_text = prompt.invoke(chain_input).to_string()

        token_manager.add_query(f"iteration_id_{iteration_id}", prompt_text)

        chain = prompt | llm | JsonOutputParser()

        try:
            result = chain.invoke(chain_input)
            result = (
                result.get("corrected_translation", None)
                if result is not None and isinstance(result, dict)
                else None
            )
        except OutputParserException as e:
            results.append(
                {
                    "result": None,
                    "error": str(e),
                    "evaluation": None,
                    "error_delta": 0,
                }
            )
            break
        if result is None:
            break

        result = translation | result

        final_evaluation = syntactic_evaluate_playbook(result)

        error_delta = initial_evaluation["length"] - final_evaluation["length"]

        translation = result
        results.append(
            {
                "result": result,
                "evaluation": final_evaluation,
                "error_delta": error_delta,
            }
        )
    end_time = time.time()
    tokens = token_manager.get_syntactic_refinement_usage()
    total_time = round(end_time - start_time, 2)

    if dependencies.should_export_db:
        export(dependencies, results, total_time, tokens, model=dependencies.model)

    return {
        "time": total_time,
        "tokens": tokens,
        "results": results,
        "error": results[-1].get("error", None),
    }
