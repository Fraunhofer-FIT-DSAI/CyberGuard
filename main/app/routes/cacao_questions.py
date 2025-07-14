from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from portkey_ai import PORTKEY_GATEWAY_URL

from langserve.schema import CustomUserType

from app.utils.get_vector_store import get_vector_store
from app.utils.portkey import portkey_headers
from app.utils.prompts import (
    persona_pattern,
    use_context_prompt,
    dont_know_prompt,
    reflection_pattern,
    zero_shot_cot,
)

question_context_template = (
    "user",
    """
        Question: {question}
        Context: {context} 
        Answer:
    """,
)


class Input(CustomUserType):
    question: str = ""
    open_ai_model: str = "gpt-4o-2024-05-13"
    information_source_url: str = (
        "https://docs.oasis-open.org/cacao/security-playbooks/v2.0/cs01/security-playbooks-v2.0-cs01.html"
    )


def build_chain(open_ai_model, information_source_url):
    # Retrieve relevant documents given a query
    retriever = get_vector_store(information_source_url).as_retriever(
        search_kwargs={"k": 20}
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
            question_context_template,
        ]
    )

    setup_and_retrieval = {
        "context": retriever,
        "question": RunnablePassthrough(),
    }

    return setup_and_retrieval | prompt | llm | StrOutputParser()


def handler(input: Input):
    open_ai_model, question, information_source_url = (
        input.open_ai_model,
        input.question,
        input.information_source_url,
    )
    chain = build_chain(open_ai_model, information_source_url)

    return chain.invoke(question)
