import os
import sys
from langchain_chroma import Chroma
# from langchain_openai import ChatOpenAI,

# from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import chromadb
import chromadb.utils.embedding_functions as chroma_ef
import pandas as pd
import re
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import utils.print_utils as prnt
import src.config as cfg

from dotenv import load_dotenv, find_dotenv


_ = load_dotenv(find_dotenv())

llm = cfg.PROVIDERS[cfg.LLM_PROVIDER]["langchain_llm"]
embeddings = cfg.PROVIDERS[cfg.EMBEDDINGS_PROVIDER]["langchain_embeddings"]

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_ef = chroma_ef.OpenAIEmbeddingFunction(
    api_key=openai_api_key, model_name="text-embedding-3-small"
)

curr_dir = os.path.dirname(__file__)
DEFAULT_PERSIST_DIR = str(os.path.join(curr_dir, "..", "test_db"))
# DEFAULT_PERSIST_DIR = str(os.path.join(curr_dir, "..", "chroma_db"))

chromadb_client = chromadb.PersistentClient(path=DEFAULT_PERSIST_DIR)
RAG_DIR = os.path.join(curr_dir, "..", "rag")


rag_pipeline_user_prompt = """
    "Answer the given question based on the given context. General instructions:
    - DO NOT allude to 'the context' or 'the provided information' in your response.
    - If you find the answer:
        - Also mention the source like a URL or a filename from which the answer was derived.
    - If you can find only partial answer, that's also okay. Tell the user what you know but DO NOT make up stuff.
    - Make sure the answer is well-formatted to make it easy for the user to read.
    - If you can't find the answer, say so honestly. 

    Think step by step.
    
    Question: {question}
    
    Context: {context}
"""

rag_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You're a helpful assistant. Answer the user's question based on the given context.",
        ),
        ("human", rag_pipeline_user_prompt),
    ]
)


def load_vectordb(collection_name, embedding_function):
    try:
        vectordb = Chroma(
            client=chromadb_client,
            persist_directory=DEFAULT_PERSIST_DIR,
            collection_name=collection_name,
            embedding_function=embedding_function,
        )
        return vectordb
    except Exception as e:
        prnt.prRed(f"Exception while trying to load collection {collection_name}: {e}")

    return None


def retrieve_docs(vectordb, query: str, debug: bool = False):
    """
    Given a query, retrieve the documents with the closest embeddings.
    """

    retriever = vectordb.as_retriever(
        search_type="mmr", search_kwargs={"k": 5, "fetch_k": 10}
    )

    relevant_docs = retriever.invoke(query)

    if debug:
        for i, doc in enumerate(relevant_docs):
            prnt.prLightPurple(f"{'-' * 10}\nDocument {i} ({doc.metadata})\n")
            print(f"{doc.page_content}")

    return relevant_docs


def retrieve_docs_alt(
    collection_name: str,
    # title: str,
    metadata_filters: dict,
    query: str,
    debug: bool = False,
    embedding_function=embeddings,
):
    """
    Given a query, retrieve the documents with the closest embeddings.
    """
    vectordb = load_vectordb(
        collection_name=collection_name, embedding_function=embedding_function
    )

    search_params = {"k": 3, "fetch_k": 10}
    if metadata_filters:
        search_params["filter"] = metadata_filters

    retriever = vectordb.as_retriever(search_type="mmr", search_kwargs=search_params)

    relevant_docs = retriever.invoke(query)

    if debug:
        for i, doc in enumerate(relevant_docs):
            prnt.prLightPurple(f"{'-' * 10}\nDocument {i} ({doc.metadata})\n")
            print(f"{doc.page_content}")

    return relevant_docs


def rag_chroma_without_history(
    query: list[str],
    collection_name: str = "ckbh",
    embedding_function=openai_ef,
):
    """
    Query a vector db to fetch the most relevant documents and answer a query based on those using an LLM.
    Use ChromaDB methods for retrieval.
    """
    prnt.prPurple("Running RAG pipeline with Chroma methods")

    global chromadb_client

    collection = chromadb_client.get_collection(
        name=collection_name, embedding_function=embedding_function
    )

    query_results = collection.query(
        query_texts=[query],
        n_results=10,
        include=["documents", "metadatas", "distances"],
        # where={"metadata_field": "is_equal_to_this"},
        # where_document={"$contains":"search_string"}
    )

    # prnt.prLightPurple(f"{type(query_results)}, {query_results.keys()}")
    # prnt.prLightPurple(f"Num of query results: {len(query_results)}")
    # print(f"\n{json.dumps(query_results, indent=2)}")

    # query_results is a dict (keys: ['ids', 'embeddings', 'documents', 'uris', 'data', 'metadatas', 'distances', 'included']) where each key's value is a list of lists, one list for each query.
    relevant_docs = query_results["documents"][0]  # list
    relevant_metadata = query_results["metadatas"][0]  # list
    distances = query_results["distances"][0]  # list

    unique_sources = "Sources:\n" + "\n".join({m["source"] for m in relevant_metadata})
    print(f"\n{unique_sources}")

    relevant_docs = [re.sub(r"\n{3,}", "\n\n", doc) for doc in relevant_docs]
    for i, doc in enumerate(relevant_docs):
        # doc = re.sub(r"\n{2,}", "\n", doc)
        prnt.prLightPurple(
            f"\n\n-------------\nDocument {i} (Source: {relevant_metadata[i]['source']})\n"
        )
        print(doc)

    print(f"\nDistances: {distances}")

    context = "\n\n".join(relevant_docs) + "\n" + unique_sources

    # prnt.prLightPurple(f"\nContext:\n{context}")

    output_parser = StrOutputParser()
    rag_chain = rag_prompt | llm | output_parser
    rag_answer = rag_chain.invoke({"context": context, "question": query})

    # prnt.prLightPurple(f"\nQuestion: {query}")
    # print(f"RAG answer: {rag_answer}\n")
    prnt.prYellow("RAG answer from chroma:\n")
    print(f"{rag_answer}\n")


def rag_langchain_without_history(
    query: str,
    collection_names: list[str],
    embedding_function=embeddings,
) -> str:
    """
    Query a vector db to fetch the most relevant documents and answer a query based on those using an LLM.
    Use LangChain methods for retrieval.
    """

    relevant_docs = []
    for collection_name in collection_names:
        vectordb = load_vectordb(
            collection_name=collection_name, embedding_function=embedding_function
        )
        if not vectordb:
            continue

        search_params = {
            "k": 5,
            "fetch_k": 15,
        }

        retriever = vectordb.as_retriever(
            search_type="mmr", search_kwargs=search_params
        )

        # relevant_docs = retrieve_docs(retriever=retriever, query=query, debug=True)
        relevant_docs += retriever.invoke(query)

    # for i, doc in enumerate(relevant_docs):
    #     prnt.prLightPurple(f"{'-' * 10}\nDocument {i} ({doc.metadata})\n")
    #     print(f"{doc.page_content}")

    unique_sources = ""
    if relevant_docs:
        unique_sources = "Sources:\n" + "\n".join(
            {doc.metadata["source"] for doc in relevant_docs}
        )
        # prnt.prLightPurple(f"--------\n{unique_sources}\n--------")

    context = (
        "\n\n".join([doc.page_content for doc in relevant_docs]) + "\n" + unique_sources
    )

    # retrieval = RunnableParallel(
    #     {"context": retriever, "question": RunnablePassthrough()}
    # )

    output_parser = StrOutputParser()
    # rag_chain = retrieval | rag_prompt | llm | output_parser
    rag_chain = rag_prompt | llm | output_parser
    rag_answer = rag_chain.invoke({"question": query, "context": context})
    # rag_answers = rag_chain.batch(query, config={"max_concurrency": 5})
    # prnt.prLightPurple(f"\nQuestion: {query}")
    # prnt.prYellow("\nRAG answer from langchain:\n")
    # print(f"{rag_answer}\n")

    return rag_answer


def rag_for_field_extraction(
    context: str,
    fields: dict,
    user_prompt: str,
    system_prompt: str = "You're a helpful assistant.",
):
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", user_prompt)]
    )

    output_parser = StrOutputParser()
    # rag_chain = retrieval | rag_prompt | llm | output_parser
    rag_chain = prompt | llm | output_parser
    rag_answer = rag_chain.invoke({"context": context, "fields_of_interest": fields})

    return rag_answer


def test_questions_on_the_go(collection_name: str) -> None:
    while True:
        question = input("\nQuestion: ")
        if question == "exit":
            break

        prnt.prYellow(f"\nQuestion: {question}\n")
        rag_langchain_without_history(
            query=question, collection_names=[collection_name]
        )
        # rag_chroma_without_history(question)


def test_predefined_questions_list():
    questions_df = pd.read_csv(
        os.path.join(RAG_DIR, "leopard_questions.csv")
    )  # , nrows=10)
    questions_df["Answers"] = questions_df["Question"].apply(
        rag_langchain_without_history
    )
    questions_df.to_csv(os.path.join(RAG_DIR, "leopard_answers.csv"), index=False)


if __name__ == "__main__":
    ### --- Answer all the questions in Questions.csv ---
    # test_predefined_questions_list()

    # --- Answer any question that is entered from the terminal ---
    # test_questions_on_the_go(collection_name="leopards_research_articles")
    # test_questions_on_the_go(collection_name="leopard_news")

    # print("Arguments received:", sys.argv[1])
    inputs = json.loads(sys.argv[1])
    answer = "None"

    if inputs["data_source"] == "news_scholar":
        answer = rag_langchain_without_history(
            query=inputs["question"],
            collection_names=[
                f"{inputs['collection_name_prefix']}_news",
                f"{inputs['collection_name_prefix']}_research_articles",
            ],
        )

    elif inputs["data_source"] == "link":
        answer = rag_langchain_without_history(
            query=inputs["question"],
            collection_names=[inputs["collection_name_prefix"]],
        )
    print(answer)
