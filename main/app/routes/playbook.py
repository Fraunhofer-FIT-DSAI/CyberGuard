from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langserve.schema import CustomUserType
from operator import itemgetter

from portkey_ai import PORTKEY_GATEWAY_URL


from app.utils.get_vector_store import get_vector_store
from app.utils.portkey import portkey_headers
from app.utils.prompts import (
    persona_pattern,
    use_context_prompt,
    dont_know_prompt,
    reflection_pattern,
    zero_shot_cot,
)
from app.utils.files import get_unstructured_playbook_content


question_playbook_context_template = (
    "user",
    """
        Playbook: {playbook}
        Question: {question}
        Context: {context} 
        Answer:
    """,
)


class Input(CustomUserType):
    question: str = ""
    playbook_file_name: str = "AWS_IAM_Account_Locking.json"
    open_ai_model: str = "gpt-4o-2024-05-13"
    information_source_url: str = (
        "https://docs.oasis-open.org/cacao/security-playbooks/v2.0/cs01/security-playbooks-v2.0-cs01.html"
    )


def build_chain(open_ai_model, information_source_url):
    retriever = get_vector_store(information_source_url).as_retriever(
        search_kwargs={"k": 4}
    )

    llm = ChatOpenAI(
        model=open_ai_model,
        base_url=PORTKEY_GATEWAY_URL,
        default_headers=portkey_headers,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            persona_pattern,
            use_context_prompt,
            dont_know_prompt,
            reflection_pattern,
            zero_shot_cot,
            question_playbook_context_template,
        ]
    )
    setup_and_retrieval = {
        "context": itemgetter("question")
        | retriever,  # https://github.com/langchain-ai/langchain/discussions/16421
        "question": itemgetter("question"),
        "playbook": itemgetter("playbook"),
    }

    return setup_and_retrieval | prompt | llm | StrOutputParser()


def handler(input: Input):
    open_ai_model, question, playbook_file_name, information_source_url = (
        input.open_ai_model,
        input.question,
        input.playbook_file_name,
        input.information_source_url,
    )
    chain = build_chain(open_ai_model, information_source_url)

    playbook_content = get_unstructured_playbook_content(playbook_file_name)

    return chain.invoke({"question": question, "playbook": playbook_content})
