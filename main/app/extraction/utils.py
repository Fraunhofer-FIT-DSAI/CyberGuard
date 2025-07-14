import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama

from app.utils.portkey import portkey_headers, PORTKEY_GATEWAY_URL
from app.utils.cacao_builder import get_start_step_id, insert_cacao_static_fields

OPEN_AI_SEED = 42


def get_llm(dependencies):
    return (
        ChatOpenAI(
            model=dependencies.model,
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=portkey_headers,
            temperature=dependencies.temperature,
            seed=OPEN_AI_SEED,
        )
        if not dependencies.is_open_source
        else Ollama(
            model=dependencies.model,
            temperature=dependencies.temperature,
        )
    )


def get_prompt(messages):
    filter_empty_strings = lambda array: [string for string in array if string != ""]
    return ChatPromptTemplate.from_messages(filter_empty_strings(messages))


def get_final_file_name(dependencies):
    file_name_without_extension = os.path.splitext(dependencies.playbook_file_name)[0]
    return f"outputs/{dependencies.model}.{file_name_without_extension}.json"


def read_playbook(dependencies):
    file_name = get_final_file_name(dependencies)
    try:
        with open(file_name, "r+") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def write_playbook(playbook, dependencies):
    file_name = get_final_file_name(dependencies)
    with open(file_name, "w+") as f:
        json.dump(playbook, f)


def export_workflow_result(workflow, dependencies):
    return
    playbook = read_playbook(dependencies)
    playbook["workflow"] = workflow
    playbook["workflow_start"] = get_start_step_id(playbook["workflow"])
    insert_cacao_static_fields(playbook)
    write_playbook(playbook, dependencies)


def export_variables_result(variables, dependencies):
    return
    playbook = read_playbook(dependencies)
    playbook["playbook_variables"] = variables
    insert_cacao_static_fields(playbook)
    write_playbook(playbook, dependencies)


def export_metadata_result(metadata, dependencies):
    return
    playbook = read_playbook(dependencies)
    for field, value in metadata.items():
        playbook[field] = value
    insert_cacao_static_fields(playbook)
    write_playbook(playbook, dependencies)


import os
import copy
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.chat_message_histories import (
    ChatMessageHistory,
    SQLChatMessageHistory,
)
from langchain_core.runnables import RunnableLambda

from app.utils.tokens import TokenManager


def run_question(
    runnable_with_history,
    unstructured_playbook_content,
    memory_store,
    sql_store,
    sql_cache_path,
    token_manager: TokenManager,
    dependencies,
    session_id,
    schema,
    question,
    path_prefix="",
    previous_session_id=None,
    examples=None,
):
    parser = JsonOutputParser(pydantic_object=schema)

    session_cached = is_session_cached(
        session_id, dependencies, sql_cache_path, path_prefix
    )

    def get_memory_store():
        return (
            ChatMessageHistory()
            if previous_session_id is None
            else copy.deepcopy(memory_store[previous_session_id])
        )

    memory_store[session_id] = get_memory_store()

    sql_store[session_id] = SQLChatMessageHistory(
        session_id,
        get_sql_connection(session_id, dependencies, sql_cache_path, path_prefix),
    )
    if session_cached and not dependencies.ignore_cache:
        memory_store[session_id].clear()
        load_store_messages(session_id, from_store=sql_store, to_store=memory_store)

        last_message = memory_store[session_id].messages[-1]
        result = (RunnableLambda(lambda x: last_message) | parser).invoke({})
    else:
        chain = runnable_with_history | parser

        chain_input = {"question": question, "playbook": unstructured_playbook_content}

        if examples is not None:
            chain_input = chain_input | {"examples": examples}

        result = chain.invoke(
            chain_input,
            config=get_history_config(session_id),
        )

        if dependencies.ignore_cache:
            sql_store[session_id].clear()

        load_store_messages(
            session_id,
            from_store=memory_store,
            to_store=sql_store,
        )

    contents = map_messages_to_contents(memory_store[session_id].messages)
    token_manager.add_query(session_id, str(contents))

    return result


def map_messages_to_contents(messages):
    return list(map(lambda message: message.content, messages))


def load_store_messages(session_id, from_store, to_store):
    to_store[session_id].add_messages(from_store[session_id].messages)


def is_session_cached(session_id, dependencies, sql_cache_path, path_prefix=""):
    return os.path.isfile(
        f"{sql_cache_path}{path_prefix}/{create_composed_session_id(session_id,dependencies)}.db"
    )


def create_composed_session_id(session_id, dependencies):
    return f"{session_id}.{dependencies.model}.{dependencies.playbook_file_name}"


def get_sql_connection(session_id, dependencies, sql_cache_path, path_prefix=""):
    return f"sqlite:///{sql_cache_path}{path_prefix}/{create_composed_session_id(session_id,dependencies)}.db"


def get_history_config(session_id):
    return {
        "configurable": {
            "session_id": session_id,
        }
    }


def get_field_value(field, result):
    if result is None:
        return None
    if not isinstance(result, dict):
        return None
    if field not in result:
        return None
    return result[field]


class LocalCache:
    def __init__(self, cache_path, cache_key, playbook_file_name, model):
        self.playbook_file_name = playbook_file_name
        self.model = model
        self.cache_path = cache_path
        self.cache_key = cache_key

    def does_cache_exist(self):
        return os.path.isfile(self.get_cache_key())

    def write_cache(self, data):
        with open(
            self.get_cache_key(),
            "w",
        ) as f:
            json.dump(data, f)

    def get_cache_key(self):
        file_name_without_extension = os.path.splitext(self.playbook_file_name)[0]
        return f"{self.cache_path}/{self.cache_key}.{self.model}.{file_name_without_extension}.json"


def remove_null_values(step):
    return {key: value for key, value in step.items() if value is not None}
