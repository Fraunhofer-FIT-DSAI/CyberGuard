import time

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import (
    ChatMessageHistory,
)
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.exceptions import OutputParserException

from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional, List

from app.utils.prompts import (
    KNOWLEDGE_PLACEHOLDER,
    create_prompt,
    get_workflow_names_few_shot_examples,
    persona_pattern,
    dont_know_prompt,
    reflection_pattern,
    zero_shot_cot,
    json_answer_prompt,
)
from app.utils.cacao_builder import (
    generate_cacao_id,
    generate_id,
    is_valid_uuid,
)
from app.utils.tokens import TokenManager
from app.extraction.utils import (
    LocalCache,
    export_workflow_result,
    get_field_value,
    get_llm,
    get_prompt,
    remove_null_values,
)
from app.utils.cacao_spec import (
    WORKFLOW_STEP_DESCRIPTION_DESCRIPTION,
    WORKFLOW_STEP_IF_CONDITION_DESCRIPTION,
    WORKFLOW_STEP_IF_ON_FALSE_DESCRIPTION,
    WORKFLOW_STEP_IF_ON_TRUE_DESCRIPTION,
    WORKFLOW_STEP_NAMES_DESCRIPTION,
    WORKFLOW_STEP_ON_COMPLETION_DESCRIPTION,
    WORKFLOW_STEP_ON_FAILURE_DESCRIPTION,
    WORKFLOW_STEP_ON_SUCCESS_DESCRIPTION,
    WORKFLOW_STEP_TYPES_VALID,
    WORKFLOW_STEP_TYPES_DESCRIPTION,
)
from app.extraction.utils import (
    run_question,
)
from app.utils.files import get_file_content
from app.utils.db import export

SQL_CACHE_PATH = "sql/workflow"

INFER_VALUE_OR_NULL = (
    lambda field: f"Infer the value for the '{field}' field, if you can't do it, please provide null."
)


def extract_workflow(
    unstructured_playbook_content, token_manager: TokenManager, dependencies
):
    start_time = time.time()
    llm = get_llm(dependencies)

    prompt = get_prompt(
        [
            persona_pattern if dependencies.prompt_patterns.persona else "",
            dont_know_prompt,
            reflection_pattern if dependencies.prompt_patterns.reason else "",
            zero_shot_cot if dependencies.prompt_patterns.reason else "",
            (
                json_answer_prompt
                if dependencies.prompt_patterns.template_config.answer_json
                else ""
            ),
            MessagesPlaceholder(variable_name="examples", optional=True),
            ("human", "Playbook: {playbook}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "Question: {question}"),
            ("ai", "Answer: "),
        ]
    )

    prompt_text = prompt.invoke(
        {
            "playbook": unstructured_playbook_content,
            "question": "",
            "history": [],
        }
    ).to_string()
    token_manager.update_prompt_tokens_used(prompt_text)

    memory_store = {}
    sql_store = {}

    def get_session_history(session_id: str):
        if session_id not in memory_store:
            memory_store[session_id] = ChatMessageHistory()
        return memory_store[session_id]

    chain = prompt | llm

    runnable_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )

    cache = LocalCache(
        SQL_CACHE_PATH,
        "workflow",
        dependencies.playbook_file_name,
        dependencies.model,
    )
    try:
        step_names_result, name_session_id = extract_step_names(
            runnable_with_history,
            unstructured_playbook_content,
            memory_store,
            sql_store,
            token_manager,
            dependencies,
        )
    except OutputParserException as e:
        step_names_result = []

    final_result = {}
    intermediate_steps = []
    try:
        is_cached = cache.does_cache_exist()
        if is_cached and not dependencies.ignore_cache:
            intermediate_steps = get_file_content(cache.get_cache_key())
            for step in intermediate_steps:
                final_result[step["id"]] = {
                    "name": step["name"],
                }
        else:
            for step in step_names_result:
                if step is None or step.get("name", None) is None:
                    continue
                id = generate_id()
                intermediate_steps.append(
                    {
                        "id": id,
                        "name": step["name"],
                    }
                )
                final_result[id] = {
                    "name": step["name"],
                }
            cache.write_cache(intermediate_steps)
        for intermediate_step in intermediate_steps:
            final_result[intermediate_step["id"]] = {}
            step = final_result[intermediate_step["id"]]

            step["name"] = intermediate_step["name"]
            try:
                step["type"], type_session_id = extract_step_type(
                    intermediate_step,
                    runnable_with_history,
                    unstructured_playbook_content,
                    memory_store,
                    sql_store,
                    token_manager,
                    dependencies,
                    previous_session_id=name_session_id,
                )
            except OutputParserException as e:
                step["type"] = None
                type_session_id = None
            try:
                step["description"] = extract_step_description(
                    intermediate_step,
                    runnable_with_history,
                    unstructured_playbook_content,
                    memory_store,
                    sql_store,
                    token_manager,
                    dependencies,
                    previous_session_id=name_session_id,
                )
            except OutputParserException as e:
                step["description"] = None

            if step["type"] != "end":
                try:
                    step["on_completion"] = extract_step_on_completion(
                        intermediate_steps,
                        intermediate_step | {"type": step["type"]},
                        runnable_with_history,
                        unstructured_playbook_content,
                        memory_store,
                        sql_store,
                        token_manager,
                        dependencies,
                        previous_session_id=type_session_id,
                        use_retry=True,
                    )
                except OutputParserException as e:
                    step["on_completion"] = None

            if step["type"] != "start" and step["type"] != "end":
                try:
                    step["on_success"] = extract_step_on_success(
                        intermediate_steps,
                        intermediate_step | {"type": step["type"]},
                        runnable_with_history,
                        unstructured_playbook_content,
                        memory_store,
                        sql_store,
                        token_manager,
                        dependencies,
                        previous_session_id=type_session_id,
                        use_retry=True,
                    )
                except OutputParserException as e:
                    step["on_success"] = None
                try:
                    step["on_failure"] = extract_step_on_failure(
                        intermediate_steps,
                        intermediate_step | {"type": step["type"]},
                        runnable_with_history,
                        unstructured_playbook_content,
                        memory_store,
                        sql_store,
                        token_manager,
                        dependencies,
                        previous_session_id=type_session_id,
                        use_retry=True,
                    )
                except OutputParserException as e:
                    step["on_failure"] = None

            if step["type"] == "if-condition":
                try:
                    step["condition"] = extract_if_step_condition(
                        intermediate_step | {"type": step["type"]},
                        runnable_with_history,
                        unstructured_playbook_content,
                        memory_store,
                        sql_store,
                        token_manager,
                        dependencies,
                        previous_session_id=type_session_id,
                    )
                except OutputParserException as e:
                    step["condition"] = None
                try:
                    step["on_true"] = extract_if_step_on_true(
                        intermediate_steps,
                        intermediate_step | {"type": step["type"]},
                        runnable_with_history,
                        unstructured_playbook_content,
                        memory_store,
                        sql_store,
                        token_manager,
                        dependencies,
                        previous_session_id=type_session_id,
                        use_retry=True,
                    )
                except OutputParserException as e:
                    step["on_true"] = None
                try:
                    step["on_false"] = extract_if_step_on_false(
                        intermediate_steps,
                        intermediate_step | {"type": step["type"]},
                        runnable_with_history,
                        unstructured_playbook_content,
                        memory_store,
                        sql_store,
                        token_manager,
                        dependencies,
                        previous_session_id=type_session_id,
                        use_retry=True,
                    )
                except OutputParserException as e:
                    step["on_false"] = None

            if dependencies.include_post_processing:
                step = merge_step_connections(step)

            final_result[intermediate_step["id"]] = step

        if dependencies.workflow.construct_parallel_steps:
            parallel_steps, source_steps = construct_parallel_steps(
                final_result, "on_completion"
            )
            # Update connections
            for parallel_step_id, parallel_step in parallel_steps.items():
                final_result[parallel_step_id] = parallel_step

            for source_step_id, value in source_steps:
                final_result[source_step_id]["on_completion"] = value

    except Exception as e:
        end_time = time.time()
        return {
            "workflow": final_result,
            "tokens": token_manager.get_workflow_usage(),
            "time": round(end_time - start_time, 2),
            "error": str(e),
        }

    final_result = map_ids_to_cacao_ids(final_result)

    if dependencies.include_post_processing:
        for step_id, step in final_result.items():
            final_result[step_id] = remove_null_values(step)

    export_workflow_result(final_result, dependencies)
    end_time = time.time()

    total_time = round(end_time - start_time, 2)
    tokens = token_manager.get_workflow_usage()

    if dependencies.should_export_db:
        export(dependencies, final_result, total_time, tokens, model=dependencies.model)
    return {
        "workflow": final_result,
        "tokens": tokens,
        "time": total_time,
    }


class BaseExtraction(BaseModel):
    def __getitem__(self, name):
        return getattr(self, name)


def extract_step_names(
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
):
    class StepNameExtraction(BaseModel):
        name: str = Field(default=None)
        reason: str = Field(default=None)

    class WorkflowStepNames(BaseExtraction):
        steps: List[StepNameExtraction] = Field(default=None)

    schema = WorkflowStepNames
    session_id = "workflow.step_names"
    path_prefix = "/step_names"
    return_field_name = "steps"
    question = f"""
        What is the CACAO translation for the supplied playbook? 
        Extract a list of workflow step names.
        {KNOWLEDGE_PLACEHOLDER}
    """
    knowledge = [
        {
            "specification": WORKFLOW_STEP_NAMES_DESCRIPTION,
        }
    ]

    question = create_prompt(
        question,
        dependencies.prompt_patterns,
        "name",
        "string",
        knowledge,
        {"array_name": return_field_name, "entity_name": "step"},
    )
    examples = None
    if dependencies.prompt_patterns.include_few_shot_prompting:
        few_shot_prompt = get_workflow_names_few_shot_examples(
            question,
            dependencies.prompt_patterns.examples_to_include,
            dependencies.playbook_file_name,
        )

        few_shot_invocation = few_shot_prompt.invoke(
            {"examples": few_shot_prompt.examples}
        )
        token_manager.update_few_shot_tokens_used(few_shot_invocation.to_string())

        examples = few_shot_invocation.to_messages()

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        examples=examples,
    )

    return_field_name = "steps" if "steps" in result else "workflow_steps"

    return result.get(return_field_name, []), session_id


class ExtractStepInput:
    id: str
    name: str


def extract_step_type(
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
):
    class StepTypeExtraction(BaseExtraction):
        type: str = Field(default=None)
        reason: str = Field(default=None)

    schema = StepTypeExtraction

    session_id = f"workflow.step_types.{step['id']}"
    path_prefix = "/step_types"
    question = f"""
        Here is the previously extracted workflow step from the playbook: {step}.
        What is the corresponding CACAO 'type' of the step?
        {KNOWLEDGE_PLACEHOLDER}
        Do not answer with a value that is not in the list above.
    """
    knowledge = [
        {
            "specification": WORKFLOW_STEP_TYPES_DESCRIPTION,
            "valid_message": "Here are the valid step 'type' values:",
            "valid_values": WORKFLOW_STEP_TYPES_VALID,
        }
    ]

    question = create_prompt(
        question, dependencies.prompt_patterns, "type", "string", knowledge
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    step_type = get_field_value("type", result)

    return step_type, session_id


def extract_step_description(
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
):
    class StepDescriptionExtraction(BaseExtraction):
        description: str = Field(default=None)
        reason: str = Field(default=None)

    schema = StepDescriptionExtraction

    session_id = f"workflow.step_descriptions.{step['id']}"
    path_prefix = "/step_descriptions"
    question = f"""
        Here is the previously extracted workflow step from the playbook: {step}.
        What is the corresponding CACAO 'description' of the step?
        {KNOWLEDGE_PLACEHOLDER}
    """
    knowledge = [
        {
            "specification": WORKFLOW_STEP_DESCRIPTION_DESCRIPTION,
        }
    ]

    question = create_prompt(
        question, dependencies.prompt_patterns, "description", "string", knowledge
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    return get_field_value("description", result)


def get_connection_question_prompt(
    field, input_step, steps, specification, dependencies
):
    question = f"""
            Here is the previously extracted workflow step from the playbook: {input_step}.
            What is the id of the corresponding CACAO '{field}' field for the step?
            {KNOWLEDGE_PLACEHOLDER}
            {INFER_VALUE_OR_NULL(field)}
            Make sure that the extracted id for the '{field}' field is present in the list of previously extracted steps: {steps}
        """
    knowledge = [
        {
            "specification": specification,
        }
    ]

    question = create_prompt(
        question, dependencies.prompt_patterns, field, "string", knowledge
    )
    return question


def extract_step_on_completion(
    steps,
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
    use_retry=False,
):
    class StepOnCompletionExtraction(BaseExtraction):
        on_completion: Optional[str] = Field(default=None)
        reason: str = Field(default=None)

    schema = StepOnCompletionExtraction

    session_id = f"workflow.step_on_completion.{step['id']}"
    path_prefix = "/step_on_completion"
    question = get_connection_question_prompt(
        "on_completion",
        step,
        steps,
        WORKFLOW_STEP_ON_COMPLETION_DESCRIPTION,
        dependencies,
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    on_completion_value = get_field_value("on_completion", result)

    if use_retry and should_retry(on_completion_value, steps):
        retry_value = retry_connection(
            "on_completion",
            on_completion_value,
            steps,
            step,
            runnable_with_history,
            unstructured_playbook_content,
            memory_store,
            sql_store,
            token_manager,
            dependencies,
            previous_session_id=session_id,
        )
        return retry_value if retry_value is not None else on_completion_value

    return on_completion_value


def extract_step_on_success(
    steps,
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
    use_retry=False,
):
    class StepOnSuccessExtraction(BaseExtraction):
        on_success: Optional[str] = Field(default=None)
        reason: str = Field(default=None)

    schema = StepOnSuccessExtraction

    session_id = f"workflow.step_on_success.{step['id']}"
    path_prefix = "/step_on_success"
    question = get_connection_question_prompt(
        "on_success", step, steps, WORKFLOW_STEP_ON_SUCCESS_DESCRIPTION, dependencies
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    on_success_value = get_field_value("on_success", result)

    if use_retry and should_retry(on_success_value, steps):
        retry_value = retry_connection(
            "on_success",
            on_success_value,
            steps,
            step,
            runnable_with_history,
            unstructured_playbook_content,
            memory_store,
            sql_store,
            token_manager,
            dependencies,
            previous_session_id=session_id,
        )
        return retry_value if retry_value is not None else on_success_value
    return on_success_value


def extract_step_on_failure(
    steps,
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
    use_retry=False,
):
    class StepOnFailureExtraction(BaseExtraction):
        on_failure: Optional[str] = Field(default=None)
        reason: str = Field(default=None)

    schema = StepOnFailureExtraction

    session_id = f"workflow.step_on_failure.{step['id']}"
    path_prefix = "/step_on_failure"
    question = get_connection_question_prompt(
        "on_failure", step, steps, WORKFLOW_STEP_ON_FAILURE_DESCRIPTION, dependencies
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    on_failure_value = get_field_value("on_failure", result)

    if use_retry and should_retry(on_failure_value, steps):
        retry_value = retry_connection(
            "on_failure",
            on_failure_value,
            steps,
            step,
            runnable_with_history,
            unstructured_playbook_content,
            memory_store,
            sql_store,
            token_manager,
            dependencies,
            previous_session_id=session_id,
        )
        return retry_value if retry_value is not None else on_failure_value
    return on_failure_value


def retry_connection(
    field_name,
    value,
    steps,
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
    path_prefix=None,
):
    if path_prefix is None:
        path_prefix = field_name

    class StepIdExtraction(BaseExtraction):
        id: Optional[str] = Field(default=None)
        reason: str = Field(default=None)

    schema = StepIdExtraction

    retry_session_id = f"workflow.step_{path_prefix}_retry.{step['id']}"
    path_prefix = f"/step_{path_prefix}_retry"
    question = f"""
            You extracted the id '{value}' for the '{field_name}' field for the step {step}.
            To which of the previously extracted steps does the id '{value}' correspond?
            Make sure that the extracted id for the is present in the list of previously extracted steps: {steps}
            Answer based on the playbook content.
        """
    question = create_prompt(question, dependencies.prompt_patterns, "id", "string")

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        retry_session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    return get_field_value("id", result)


def extract_if_step_on_true(
    steps,
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
    use_retry=False,
):
    class StepOnTrueExtraction(BaseExtraction):
        on_true: Optional[str] = Field(default=None)
        reason: str = Field(default=None)

    schema = StepOnTrueExtraction

    session_id = f"workflow.step_if_on_true.{step['id']}"
    path_prefix = "/step_if_on_true"
    question = get_connection_question_prompt(
        "on_true", step, steps, WORKFLOW_STEP_IF_ON_TRUE_DESCRIPTION, dependencies
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    on_true_value = get_field_value("on_true", result)

    if use_retry and should_retry(on_true_value, steps):
        retry_value = retry_connection(
            "on_true",
            on_true_value,
            steps,
            step,
            runnable_with_history,
            unstructured_playbook_content,
            memory_store,
            sql_store,
            token_manager,
            dependencies,
            previous_session_id=session_id,
            path_prefix="if_on_true",
        )
        return retry_value if retry_value is not None else on_true_value

    return on_true_value


def extract_if_step_on_false(
    steps,
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
    use_retry=False,
):
    class StepOnFalseExtraction(BaseExtraction):
        on_false: Optional[str] = Field(default=None)
        reason: str = Field(default=None)

    schema = StepOnFalseExtraction

    session_id = f"workflow.step_if_on_false.{step['id']}"
    path_prefix = "/step_if_on_false"
    question = get_connection_question_prompt(
        "on_false", step, steps, WORKFLOW_STEP_IF_ON_FALSE_DESCRIPTION, dependencies
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )
    on_false_value = get_field_value("on_false", result)

    if use_retry and should_retry(on_false_value, steps):
        retry_value = retry_connection(
            "on_false",
            on_false_value,
            steps,
            step,
            runnable_with_history,
            unstructured_playbook_content,
            memory_store,
            sql_store,
            token_manager,
            dependencies,
            previous_session_id=session_id,
            path_prefix="if_on_false",
        )
        return retry_value if retry_value is not None else on_false_value

    return on_false_value


def extract_if_step_condition(
    step: ExtractStepInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
    previous_session_id,
):
    class StepConditionExtraction(BaseExtraction):
        condition: Optional[str] = Field(default=None)
        reason: str = Field(default=None)

    schema = StepConditionExtraction
    session_id = f"workflow.step_if_condition.{step['id']}"
    path_prefix = "/step_if_condition"
    question = f"""
        Here is the previously extracted workflow step from the playbook: {step}.
        What is the value of the corresponding CACAO 'condition' of the step? 
        {KNOWLEDGE_PLACEHOLDER}
    """
    knowledge = [
        {
            "specification": WORKFLOW_STEP_IF_CONDITION_DESCRIPTION,
        }
    ]

    question = create_prompt(
        question, dependencies.prompt_patterns, "condition", "string", knowledge
    )

    result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=previous_session_id,
    )

    condition_value = get_field_value("condition", result)
    # TODO: Add translation from extracted format to STIX Patterning Grammar
    return condition_value


def should_retry(value, steps):
    return value is not None and not is_step_id_valid(steps, value)


def is_step_id_valid(steps, step_id):
    for step in steps:
        if step_id == step["id"]:
            return True
    return False


# Post Processing


def construct_parallel_steps(final_result, field_name):
    steps_by = {}
    for step_id in final_result.keys():
        # For each step, check if there are other steps that have the on_completion field or on_success field equal to the id of the current step
        steps = []
        for connection_step_id, connection_step in final_result.items():
            connection_step_candidate = dict(connection_step)
            connection_step_candidate["id"] = connection_step_id
            if (
                "on_completion" in connection_step_candidate
                and connection_step_candidate["on_completion"] == step_id
            ) or (
                "on_success" in connection_step_candidate
                and connection_step_candidate["on_success"] == step_id
            ):
                steps.append(connection_step_candidate)
        if len(steps) < 2:
            continue
        steps_by[step_id] = steps

    def get_source_step_id(step):
        for source_step_id, source_step in final_result.items():
            if (
                field_has_value(source_step, field_name)
                and source_step[field_name] == step["id"]
            ):
                return source_step_id
        return None

    parallel_steps = {}
    steps_to_update = []
    for steps in steps_by.values():
        parallel_step_id = generate_id()
        parallel_step = {
            "type": "parallel",
            "next_steps": [step["id"] for step in steps],
        }
        source_steps = list(filter(None, [get_source_step_id(step) for step in steps]))
        if len(source_steps) == 0:
            continue
        source_step_id = source_steps[0]
        steps_to_update.append((source_step_id, parallel_step_id))

        parallel_steps[parallel_step_id] = parallel_step

    return parallel_steps, steps_to_update


# Delete on_success or on_failure if on_completion is present
def merge_step_connections(step):
    if field_has_value(step, "on_completion") and (
        field_has_value(step, "on_success") or field_has_value(step, "on_failure")
    ):
        del step["on_success"]
        del step["on_failure"]
    return step


def map_ids_to_cacao_ids(result):
    mapped_result = {}
    for step_id, step in result.items():
        mapped_step = dict(step)
        if "id" in mapped_step:
            del mapped_step["id"]
        primitive_fields_to_map = [
            "on_completion",
            "on_success",
            "on_failure",
            "on_true",
            "on_false",
        ]
        for field in primitive_fields_to_map:
            mapped_step[field] = map_inner_step_id(field, mapped_step, result)

        if "next_steps" in mapped_step:
            mapped_step["next_steps"] = map_inner_step_id(
                "next_steps", mapped_step, result
            )

        mapped_result[generate_cacao_id(step["type"], step_id)] = mapped_step
    return mapped_result


def map_inner_step_id(field, step, result):
    if field in step and step[field] is not None:
        if field == "next_steps":
            return list(
                map(
                    lambda id: generate_cacao_id(result[id]["type"], id),
                    step[field],
                )
            )
        if is_valid_uuid(step[field]) and step[field] in result:
            inner_step = result[step[field]]
            return generate_cacao_id(inner_step["type"], step[field])
    return None


def field_has_value(step, field):
    return field in step and step[field] is not None
