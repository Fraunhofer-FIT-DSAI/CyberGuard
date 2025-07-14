import time

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import MessagesPlaceholder

from operator import itemgetter

from app.utils.get_vector_store import get_vector_store
from app.utils.cacao import (
    field_config_mapping,
)

from app.utils.prompts import (
    get_few_shot_examples,
    persona_pattern,
    use_context_prompt,
    dont_know_prompt,
    reflection_pattern,
    zero_shot_cot,
    json_answer_prompt,
    create_prompt,
)
from app.utils.tokens import TokenManager
from app.extraction.utils import (
    export_metadata_result,
    get_llm,
    get_prompt,
)
from app.utils.db import export


def extract_metadata(
    unstructured_playbook_content,
    token_manager: TokenManager,
    dependencies,
):
    start_time = time.time()

    cacao_fields_to_extract = get_cacao_fields_to_extract(
        field_config_mapping.keys(), dependencies
    )
    if len(cacao_fields_to_extract) == 0:
        return

    cacao_playbook = {}
    for field in cacao_fields_to_extract:
        try:
            cacao_playbook[field] = extract_field(
                field,
                field_config_mapping,
                unstructured_playbook_content,
                token_manager,
                dependencies=dependencies,
            )
        except OutputParserException as e:
            cacao_playbook[field] = None
        except Exception as e:
            end_time = time.time()
            tokens = token_manager.get_usage(len(cacao_fields_to_extract))
            return {
                "cacao_playbook": cacao_playbook,
                "time": token_manager.get_usage(len(cacao_fields_to_extract)),
                "tokens": tokens,
                "error": str(e),
            }

    export_metadata_result(cacao_playbook, dependencies)
    end_time = time.time()

    total_time = round(end_time - start_time, 2)
    tokens = token_manager.get_usage(len(cacao_fields_to_extract))

    if dependencies.should_export_db:
        export(
            dependencies, cacao_playbook, total_time, tokens, model=dependencies.model
        )

    return {
        "cacao_playbook": cacao_playbook,
        "time": total_time,
        "tokens": tokens,
    }


def extract_field(
    field,
    field_config_mapping,
    unstructured_playbook_content,
    token_manager: TokenManager,
    dependencies,
):
    field_config = field_config_mapping[field]

    question = create_prompt(
        field_config["question"],
        dependencies.prompt_patterns,
        field_config["field_name"],
        field_config["field_type"],
        field_config["knowledge"],
        field_config["multiple"] if "multiple" in field_config else None,
    )

    chain_input = {
        "question": question,
        "playbook": unstructured_playbook_content,
    }

    if dependencies.prompt_patterns.include_few_shot_prompting:
        few_shot_prompt = get_few_shot_examples(
            field,
            question,
            dependencies.prompt_patterns.examples_to_include,
            dependencies.playbook_file_name,
        )

        few_shot_invocation = few_shot_prompt.invoke(
            {"examples": few_shot_prompt.examples}
        )
        token_manager.update_few_shot_tokens_used(few_shot_invocation.to_string())

        chain_input["examples"] = few_shot_invocation.to_messages()

    llm = get_llm(dependencies)

    llm_with_parser = llm | JsonOutputParser(pydantic_object=field_config["schema"])

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
            use_context_prompt if dependencies.metadata.use_rag else "",
            ("system", "Context: {context}") if dependencies.metadata.use_rag else "",
            (MessagesPlaceholder(variable_name="examples", optional=True)),
            ("human", "Playbook: {playbook}"),
            ("human", "Question: {question}"),
            ("ai", "Answer: "),
        ]
    )

    prompt_text = prompt.invoke(
        {
            "question": chain_input["question"],
            "playbook": chain_input["playbook"],
            "context": "",
        }
    ).to_string()

    token_manager.update_prompt_tokens_used(prompt_text)

    chain = prompt | llm_with_parser

    if dependencies.metadata.use_rag:
        chain = get_rag_chain(
            prompt,
            llm_with_parser,
            field_config["documents_to_include"],
            token_manager,
            dependencies,
        )

    result = chain.invoke(chain_input)
    if "mapResponse" in field_config:
        return field_config["mapResponse"](result)

    return get_field_value(field, result)


information_source_url: str = (
    "https://docs.oasis-open.org/cacao/security-playbooks/v2.0/cs01/security-playbooks-v2.0-cs01.html"
)


def get_rag_chain(
    prompt,
    llm_with_parser,
    documents_to_include,
    token_manager: TokenManager,
    dependencies,
):
    def update_tokens(inputs):
        token_manager.update_rag_tokens_used(str(inputs["context"]))
        return inputs

    get_retriever_input = lambda inputs: (
        inputs["question"]
        if dependencies.metadata.use_playbook_in_retriever
        else inputs["question"] + str(inputs["playbook"])
    )

    retriever = get_vector_store(information_source_url).as_retriever(
        search_kwargs={
            "k": documents_to_include,
        },
    )

    setup_and_retrieval = {
        "context": RunnableLambda(get_retriever_input) | retriever,
        "question": itemgetter("question"),
        "playbook": itemgetter("playbook"),
    }

    if dependencies.prompt_patterns.include_few_shot_prompting:
        setup_and_retrieval["examples"] = itemgetter("examples")

    return (
        setup_and_retrieval | RunnableLambda(update_tokens) | prompt | llm_with_parser
    )


def get_cacao_fields_to_extract(defined_fields, dependencies):
    cacao_fields = (
        defined_fields
        if dependencies.metadata.include_all_fields
        else dependencies.metadata.fields_to_extract
    )

    filter_cacao_fields = lambda cacao_fields, defined_fields: [
        field for field in cacao_fields if field in defined_fields
    ]

    return filter_cacao_fields(cacao_fields, defined_fields)


def get_field_value(field, result):
    return result[field] if field in result else result
