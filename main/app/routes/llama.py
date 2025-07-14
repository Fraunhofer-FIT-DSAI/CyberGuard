from langserve import CustomUserType
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate

from langchain_core.output_parsers import JsonOutputParser


from app.utils.files import get_unstructured_playbook_content
from app.utils.cacao import field_config_mapping
from app.utils.prompts import (
    persona_pattern,
    dont_know_prompt,
    reflection_pattern,
    zero_shot_cot,
    json_answer_prompt,
)

class Input(CustomUserType):
    playbook_file_name: str = "AWS_IAM_Account_Locking.json"
    llama_model: str = "llama3"
    field: str


question_playbook_template = (
    "user",
    """
        Playbook: {playbook} 
        Question: {question}
        Answer:
    """,
)


def handler(input: Input):
    playbook_content = get_unstructured_playbook_content(input.playbook_file_name)
    field_config = field_config_mapping[input.field]
    llm = Ollama(model=input.llama_model)

    prompt = ChatPromptTemplate.from_messages(
        [
            persona_pattern,
            dont_know_prompt,
            reflection_pattern,
            zero_shot_cot,
            question_playbook_template,
            json_answer_prompt,
        ]
    )

    parser = JsonOutputParser(pydantic_object=field_config["schema"])

    chain = prompt | llm | parser
    question = field_config["prompt"]

    return chain.invoke({"question": question, "playbook": playbook_content})
