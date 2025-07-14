import time

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import (
    ChatMessageHistory,
)
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.exceptions import OutputParserException

from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List

from app.utils.prompts import (
    KNOWLEDGE_PLACEHOLDER,
    create_prompt,
    get_variable_names_few_shot_examples,
    persona_pattern,
    dont_know_prompt,
    reflection_pattern,
    zero_shot_cot,
    json_answer_prompt,
)
from app.utils.cacao_builder import (
    generate_id,
)
from app.utils.tokens import TokenManager
from app.extraction.utils import (
    LocalCache,
    export_variables_result,
    get_field_value,
    get_llm,
    get_prompt,
    remove_null_values,
    run_question,
)
from app.utils.cacao_spec import (
    PLAYBOOK_VARIABLES,
    PLAYBOOK_VARIABLES_CONSTANT,
    PLAYBOOK_VARIABLES_DESCRIPTION,
    PLAYBOOK_VARIABLES_EXTERNAL,
    PLAYBOOK_VARIABLES_TYPES,
    PLAYBOOK_VARIABLES_TYPES_VALID,
    PLAYBOOK_VARIABLES_VALUES,
)
from app.utils.files import get_file_content
from app.utils.db import export

SQL_CACHE_PATH = "sql/variables"


def extract_variables(
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
            json_answer_prompt,
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
        "variables",
        dependencies.playbook_file_name,
        dependencies.model,
    )
    try:
        variable_names_result = extract_variable_names(
            runnable_with_history,
            unstructured_playbook_content,
            memory_store,
            sql_store,
            token_manager,
            dependencies,
        )
    except OutputParserException as e:
        variable_names_result = []

    final_result = {}
    intermediate = []
    try:
        is_cached = cache.does_cache_exist()
        if is_cached and not dependencies.ignore_cache:
            intermediate = get_file_content(cache.get_cache_key())
            for variable in intermediate:
                if variable["name"] is None:
                    continue
                final_result[variable["id"]] = {
                    "name": variable["name"],
                }
        else:
            for variable in variable_names_result:
                if variable is None or variable.get("name", None) is None:
                    continue
                id = generate_id()
                intermediate.append(
                    {
                        "id": id,
                        "name": variable["name"],
                    }
                )
                final_result[id] = {
                    "name": variable["name"],
                }
            cache.write_cache(intermediate)
        for intermediate_variable in intermediate:
            final_result[intermediate_variable["id"]] = {}
            variable = final_result[intermediate_variable["id"]]
            
            variable["name"] = intermediate_variable["name"]
            try:
                variable["description"] = extract_variable_description(
                    intermediate_variable,
                    runnable_with_history,
                    unstructured_playbook_content,
                    memory_store,
                    sql_store,
                    token_manager,
                    dependencies,
                )
            except OutputParserException as e:
                variable["description"] = None
            try:
                variable["type"], variable["value"] = extract_variable_type_and_value(
                    intermediate_variable,
                    runnable_with_history,
                    unstructured_playbook_content,
                    memory_store,
                    sql_store,
                    token_manager,
                    dependencies,
                )
            except OutputParserException as e:
                variable["type"] = None
                variable["value"] = None
            try:
                external = extract_variable_external(
                    intermediate_variable,
                    runnable_with_history,
                    unstructured_playbook_content,
                    memory_store,
                    sql_store,
                    token_manager,
                    dependencies,
                )
            except OutputParserException as e:
                external = None
            if external:
                variable["external"] = True
            try:
                constant = extract_variable_constant(
                    intermediate_variable,
                    runnable_with_history,
                    unstructured_playbook_content,
                    memory_store,
                    sql_store,
                    token_manager,
                    dependencies,
                )
            except OutputParserException as e:
                constant = None
            if constant:
                variable["constant"] = True
            final_result[intermediate_variable["id"]] = variable
    except Exception as e:
        end_time = time.time()
        return {
            "playbook_variables": final_result,
            "tokens": token_manager.get_variables_usage(),
            "time": round(end_time - start_time, 2),
            "error": str(e),
        }
    final_result = map_variable_ids_to_names(final_result)
    
    if dependencies.include_post_processing:
        for variable_name, variable in final_result.items():
            final_result[variable_name] = remove_null_values(variable)

    export_variables_result(final_result, dependencies)
    end_time = time.time()

    total_time = round(end_time - start_time, 2)
    tokens = token_manager.get_variables_usage()
    
    if dependencies.should_export_db:
        export(dependencies, final_result, total_time, tokens,model=dependencies.model)
        
    return {
        "playbook_variables": final_result,
        "tokens": tokens,
        "time": total_time,
    }


class BaseExtraction(BaseModel):
    def __getitem__(self, name):
        return getattr(self, name)


def extract_variable_names(
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
):
    class VariableNameExtraction(BaseExtraction):
        name: str = Field(default=None)
        reason: str = Field(default=None)

    class VariableNames(BaseExtraction):
        variables: List[VariableNameExtraction] = Field(default=None)

    schema = VariableNames

    session_id = "variables.names"
    path_prefix = "/names"
    return_field_name = "variables"
    question = f"""
        What is the CACAO translation for the supplied playbook? 
        Extract a list of global playbook variable names.
        {KNOWLEDGE_PLACEHOLDER}
        Remember, do not extract variables that are defined in individual workflow steps. Extract only variables that apply to the whole playbook.
    """

    knowledge = [
        {"specification": PLAYBOOK_VARIABLES},
    ]

    question = create_prompt(
        question,
        dependencies.prompt_patterns,
        "name",
        "string",
        knowledge,
        {"array_name": return_field_name, "entity_name": "variable"},
    )
    
    examples = None
    if dependencies.prompt_patterns.include_few_shot_prompting:
        few_shot_prompt = get_variable_names_few_shot_examples(
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
        examples=examples
    )
    return get_field_value(return_field_name, result)


class ExtractVariableInput:
    id: str
    name: str


def extract_variable_description(
    variable: ExtractVariableInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
):
    class VariableDescriptionExtraction(BaseExtraction):
        description: str = Field(default=None)
        reason: str = Field(default=None)

    schema = VariableDescriptionExtraction

    session_id = f"variables.description.{variable['id']}"
    path_prefix = "/description"
    question = f"""
        Here is the previously extracted global variable from the playbook: {variable}.
        What is the corresponding CACAO 'description' of the variable?
        {KNOWLEDGE_PLACEHOLDER}
        If there is no value for the 'description' field, please provide null.
    """
    knowledge = [
        {"specification": PLAYBOOK_VARIABLES},
        {"specification": PLAYBOOK_VARIABLES_DESCRIPTION},
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
    )
    return get_field_value("description", result)


def extract_variable_constant(
    variable: ExtractVariableInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
):
    class VariableConstantExtraction(BaseExtraction):
        constant: bool = Field(default=None)
        reason: str = Field(default=None)

    schema = VariableConstantExtraction

    session_id = f"variables.constant.{variable['id']}"
    path_prefix = "/constant"
    question = f"""
        Here is the previously extracted global variable from the playbook: {variable}.
        What is the corresponding CACAO 'constant' field value of the variable?
        {KNOWLEDGE_PLACEHOLDER}
        If there is no value for the 'constant' field, please provide null.
    """
    knowledge = [
        {"specification": PLAYBOOK_VARIABLES},
        {"specification": PLAYBOOK_VARIABLES_CONSTANT},
    ]
    question = create_prompt(
        question, dependencies.prompt_patterns, "constant", "boolean", knowledge
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
    )
    return get_field_value("constant", result)


def extract_variable_external(
    variable: ExtractVariableInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
):
    class VariableExternalExtraction(BaseExtraction):
        external: bool = Field(default=None)
        reason: str = Field(default=None)

    schema = VariableExternalExtraction

    session_id = f"variables.external.{variable['id']}"
    path_prefix = "/external"
    question = f"""
        Here is the previously extracted global variable from the playbook: {variable}.
        What is the corresponding CACAO 'external' field value of the variable?
        {KNOWLEDGE_PLACEHOLDER}
        If there is no value for the 'external' field, please provide null.
    """
    knowledge = [
        {"specification": PLAYBOOK_VARIABLES},
        {"specification": PLAYBOOK_VARIABLES_EXTERNAL},
    ]

    question = create_prompt(
        question, dependencies.prompt_patterns, "external", "boolean", knowledge
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
    )
    return get_field_value("external", result)


def extract_variable_type_and_value(
    variable: ExtractVariableInput,
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    token_manager: TokenManager,
    dependencies,
):
    class VariableTypeExtraction(BaseExtraction):
        type: str = Field(default=None)
        reason: str = Field(default=None)

    schema = VariableTypeExtraction

    type_session_id = f"variables.type.{variable['id']}"
    path_prefix = "/type"
    question = f"""
        Here is the previously extracted global variable from the playbook: {variable}.
        What is the corresponding CACAO 'type' of the variable?
        {KNOWLEDGE_PLACEHOLDER}
    """
    knowledge = [
        {"specification": PLAYBOOK_VARIABLES},
        {
            "specification": PLAYBOOK_VARIABLES_TYPES,
            "valid_message": "Here are the valid variable 'type' values:",
            "valid_values": PLAYBOOK_VARIABLES_TYPES_VALID,
        },
    ]

    question = create_prompt(
        question, dependencies.prompt_patterns, "type", "string", knowledge
    )

    type_result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        type_session_id,
        schema,
        question,
        path_prefix,
    )

    variable_with_type = variable | {"type": get_field_value("type", type_result)}

    class VariableTypeExtraction(BaseExtraction):
        value: str = Field(default=None)
        reason: str = Field(default=None)

    schema = VariableTypeExtraction

    value_session_id = f"variables.value.{variable['id']}"
    path_prefix = "/value"
    question = f"""
        Here is the previously extracted global variable from the playbook: {variable_with_type}.
        What is the corresponding CACAO 'value' of the variable?
        {KNOWLEDGE_PLACEHOLDER}
        If there is no value for the 'value' field, provide null regardless of the variable type. 
    """
    knowledge = [
        {"specification": PLAYBOOK_VARIABLES_VALUES},
    ]

    question = create_prompt(
        question, dependencies.prompt_patterns, "value", "string", knowledge
    )

    value_result = run_question(
        runnable_with_history,
        unstructured_playbook_content,
        memory_store,
        sql_store,
        SQL_CACHE_PATH,
        token_manager,
        dependencies,
        value_session_id,
        schema,
        question,
        path_prefix,
        previous_session_id=type_session_id,
    )

    return get_field_value("type", type_result), get_field_value("value", value_result)

def map_variable_ids_to_names(final_result):
    variable_names = {}
    for  variable in final_result.values():
        variable_copy = variable.copy()
        del variable_copy["name"]
        variable_names[map_name_to_cacao_name(variable["name"])] = variable_copy
    return variable_names

def map_name_to_cacao_name(name):
    return f"__{name.replace(" ", "_").lower()}__"
