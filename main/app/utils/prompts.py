from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from app.utils.files import (
    get_translated_playbook_content,
    get_unstructured_playbook_content,
)
import re

persona_pattern = (
    "system",
    "You are an expert on cybersecurity playbooks and different cybersecurity formats.",
)

reflection_pattern = ("system", "Explain your reasoning.")
zero_shot_cot = ("system", "Let's think step by step.")

use_context_prompt = (
    "system",
    "Use the following pieces of retrieved context to answer the question.",
)
dont_know_prompt = (
    "system",
    "If you don't know the answer, just say that you don't know.",
)

json_answer_prompt = (
    "system",
    "Your output must be in valid JSON. Do not output anything other than the JSON.",
)

RESPONSE_FORMAT = "Here is the format of the response:"

JUSTIFY_ANSWER = "Justify your answer. Let's think step by step."

JUSTIFY_ANSWER_DETAIL = "Justify your answer in detail. Your reasoning should be based only on the playbook content. Let's think step by step."


ANSWER_BASED_ON_PLAYBOOK_AND_SPEC = (
    "Answer based on the playbook content and the CACAO specification."
)


def create_prompt(
    prompt,
    prompt_patterns,
    field_name,
    field_type,
    knowledge=None,
    multiple=None,
):
    return filter_empty_spaces_and_new_lines(
        f"""
        {inject_knowledge(prompt.strip(), knowledge, prompt_patterns)}
        {construct_reflection_prompt(prompt_patterns, multiple).strip()}
        {construct_json_response_prompt(prompt_patterns, field_name, field_type, multiple).strip()}
    """
    )


def filter_empty_spaces_and_new_lines(prompt):
    return re.sub(" +", " ", prompt.replace("\n", ""))


KNOWLEDGE_PLACEHOLDER = "KNOWLEDGE_PLACEHOLDER"


def inject_knowledge(prompt, knowledge, prompt_patterns):
    remove_placeholder_from_prompt = lambda prompt: "\n".join(
        line for line in prompt.splitlines() if KNOWLEDGE_PLACEHOLDER not in line
    )

    if not prompt_patterns.knowledge_injection or not knowledge:
        return remove_placeholder_from_prompt(prompt)

    def format_knowledge_item(item):
        specification_text = f"""
            CACAO Specification: {item['specification']}
        """.strip()

        if "valid_values" not in item:
            return specification_text

        return f"""
            {specification_text}
            {item["valid_message"]} {str(item["valid_values"])}
        """

    formatted_knowledge = "".join(format_knowledge_item(item) for item in knowledge)

    knowledge = f"""
        {ANSWER_BASED_ON_PLAYBOOK_AND_SPEC}
        {formatted_knowledge}
    """

    return prompt.replace(KNOWLEDGE_PLACEHOLDER, knowledge.strip())


def construct_reflection_prompt(prompt_patterns, multiple=None):
    if not prompt_patterns.reason:
        return ""

    JUSTIFY_ANSWER_PROMPT = (
        JUSTIFY_ANSWER_DETAIL
        if prompt_patterns.reason_config.in_detail
        else JUSTIFY_ANSWER
    )

    if multiple is not None and "entity_name" in multiple:
        return f"""
            For each extracted {multiple["entity_name"]} name, {JUSTIFY_ANSWER_PROMPT}
        """
    return f"""
        {JUSTIFY_ANSWER_PROMPT}
    """


def construct_json_response_prompt(
    prompt_patterns, field_name, field_type, multiple=None
):
    if not prompt_patterns.template:
        return ""

    if multiple is not None and "array_name" in multiple:
        if not prompt_patterns.template_config.include_reason:
            return f"""
                {RESPONSE_FORMAT}
                ```json {{
                    \"{multiple["array_name"]}\": [
                        {{
                            \"{field_name}\": \"{field_type}\"
                        }}
                    ]
                }}```
            """
        if not prompt_patterns.template_config.reason_first:
            return f"""
                {RESPONSE_FORMAT}
                ```json {{
                    \"{multiple["array_name"]}\": [
                        {{
                            \"{field_name}\": \"{field_type}\",
                            \"reason\": \"string\"
                        }}
                    ]
                }}```
            """
        return f"""
                {RESPONSE_FORMAT}
                ```json {{
                    \"{multiple["array_name"]}\": [
                        {{
                            \"reason\": \"string\",
                            \"{field_name}\": \"{field_type}\"
                        }}
                    ]
                }}```
        """

    if not prompt_patterns.template_config.include_reason:
        return f"""
            {RESPONSE_FORMAT}
            ```json {{
                \"{field_name}\": \"{field_type}\"
            }}```
        """
    if not prompt_patterns.template_config.reason_first:
        return f"""
            {RESPONSE_FORMAT}
            ```json {{
                \"{field_name}\": \"{field_type}\",
                \"reason\": \"string\"
            }}```
        """
    return f"""
        {RESPONSE_FORMAT}
        ```json {{
            \"reason\": \"string\",
            \"{field_name}\": \"{field_type}\"
        }}```
    """


def get_variable_names_few_shot_examples(question, amount, playbook_file_name):
    AVAILABLE_TRANSLATED_PLAYBOOKS = [
        "AWS_IAM_Account_Locking.json",
        "AWS_IAM_Account_Unlocking.json",
        "Cisco_Umbrella_DNS_Denylisting.json",
        "Alert - Update SLA Details.json",
    ]

    filtered_playbooks = [
        playbook_name
        for playbook_name in AVAILABLE_TRANSLATED_PLAYBOOKS
        if playbook_file_name != playbook_name
    ]
    selected_example_translations = filtered_playbooks[:amount]
    examples = []
    for playbook_file_name in selected_example_translations:
        translated_playbook_content = get_translated_playbook_content(
            playbook_file_name
        )
        step_names = [
            {"name": variable_name[2:-2]}
            for variable_name in translated_playbook_content[
                "playbook_variables"
            ].keys()
        ]
        examples.append(
            {
                "input": get_unstructured_playbook_content(playbook_file_name),
                "question": question,
                "output": {"variables": step_names},
            }
        )

    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "Playbook: {input}"),
            ("human", "Question: {question}"),
            ("ai", "Answer: {output}"),
        ]
    )

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )
    return few_shot_prompt


def get_workflow_names_few_shot_examples(question, amount, playbook_file_name):
    AVAILABLE_TRANSLATED_PLAYBOOKS = [
        "AWS_IAM_Account_Locking.json",
        "AWS_IAM_Account_Unlocking.json",
        "Cisco_Umbrella_DNS_Denylisting.json",
        "Alert - Update SLA Details.json",
        "playbook-Email_Address_Enrichment_Generic_Test.json",
    ]

    filtered_playbooks = [
        playbook_name
        for playbook_name in AVAILABLE_TRANSLATED_PLAYBOOKS
        if playbook_file_name != playbook_name
    ]
    selected_example_translations = filtered_playbooks[:amount]
    examples = []
    for playbook_file_name in selected_example_translations:
        translated_playbook_content = get_translated_playbook_content(
            playbook_file_name
        )
        step_names = [
            {"name": step["name"]}
            for step in translated_playbook_content["workflow"].values()
            if "name" in step
        ]
        examples.append(
            {
                "input": get_unstructured_playbook_content(playbook_file_name),
                "question": question,
                "output": {"steps": step_names},
            }
        )

    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "Playbook: {input}"),
            ("human", "Question: {question}"),
            ("ai", "Answer: {output}"),
        ]
    )

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )
    return few_shot_prompt


def get_few_shot_examples(field, question, amount, playbook_file_name):
    prefix = "Few_Shot_Metadata_"
    AVAILABLE_TRANSLATED_PLAYBOOKS = [
        f"{prefix}AWS_IAM_Account_Locking.json",
        f"{prefix}Cisco_Umbrella_DNS_Denylisting.json",
    ]

    filtered_playbooks = [
        playbook_name
        for playbook_name in AVAILABLE_TRANSLATED_PLAYBOOKS
        if f"{prefix}{playbook_file_name}" != playbook_name
    ]
    selected_example_translations = filtered_playbooks[:amount]
    examples = [
        {
            "input": get_unstructured_playbook_content(playbook_file_name),
            "question": question,
            "output": {
                field: get_translated_playbook_content(playbook_file_name)[field]
            },
        }
        for playbook_file_name in selected_example_translations
    ]

    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "Playbook: {input}"),
            ("human", "Question: {question}"),
            ("ai", "Answer: {output}"),
        ]
    )

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )
    return few_shot_prompt
