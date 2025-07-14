import os

from langchain_community.document_loaders import WebBaseLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from portkey_ai import PORTKEY_GATEWAY_URL

import hashlib

from app.utils.portkey import portkey_headers

def get_vector_store(information_source_url):
    # get the md5 hash of the url
    hash = hashlib.md5(information_source_url.encode()).hexdigest()
    persist_directory = f"./storage/chroma_db_{hash}"

    if os.path.exists(persist_directory):
        # Load the vectorstore from disk
        return Chroma(
            persist_directory=persist_directory,
            embedding_function=OpenAIEmbeddings(
                base_url=PORTKEY_GATEWAY_URL,
                default_headers=portkey_headers,
            ),
        )
    else:
        # Load information from url
        loader = WebBaseLoader(information_source_url)
        docs = loader.load()

        # Split the document into chunks so that the context window does not get overloaded
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, add_start_index=True
        )
        splits = text_splitter.split_documents(docs)
        # Embed the contents of each document split and insert it into a vectorstore
        return Chroma.from_documents(
            documents=splits,
            persist_directory=persist_directory,
            embedding=OpenAIEmbeddings(
                base_url=PORTKEY_GATEWAY_URL,
                default_headers=portkey_headers,
            ),
        )