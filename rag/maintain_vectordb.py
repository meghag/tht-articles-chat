"""### Imports"""

import os
import sys

from langchain_community.document_loaders import (
    TextLoader,
    WebBaseLoader,
    # BSHTMLLoader,
    # UnstructuredHTMLLoader,
    # UnstructuredURLLoader,
    Docx2txtLoader,
    PyPDFLoader,
)

# from langchain_unstructured import UnstructuredLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.docstore.document import Document

from llama_parse import LlamaParse

# from llama_index.core import SimpleDirectoryReader
# from pandasai import SmartDataframe
from uuid import uuid4
from dotenv import load_dotenv, find_dotenv
import chromadb
import chromadb.utils.embedding_functions as chroma_ef
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

# from markdownify import markdownify
import json
import pprint


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import utils.print_utils as prnt
import src.config as cfg
# import src.rag_query as rag

"""### Setup"""

_ = load_dotenv(find_dotenv())

openai_api_key = os.getenv("OPENAI_API_KEY")

llama_parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"), result_type="markdown"
)

openai_embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small", api_key=openai_api_key
)
openai_ef = chroma_ef.OpenAIEmbeddingFunction(
    api_key=openai_api_key, model_name="text-embedding-3-small"
)

curr_dir = os.path.dirname(__file__)
DOCS_DIR = os.path.join(curr_dir, "..", "results", "leopard_scholar_1years", "pdf")
RAG_DIR = os.path.join(curr_dir, "..", "rag")

DEFAULT_PERSIST_DIR = str(os.path.join(curr_dir, "..", "test_db"))
chromadb_client = chromadb.PersistentClient(path=DEFAULT_PERSIST_DIR)

"""### Loading"""


def load_single_source(
    source: str, filepath: str = None, addnl_metadata: dict = {}
) -> list:
    """Load a data source into text document(s) with some associated metadata"""
    prnt.prYellow(f"\n{'-' * 30}- LOADING {'-' * 30}")
    print(f"\nTrying to load '{source}'")

    data = None
    if (not source.startswith("http")) and (not filepath):
        filepath = os.path.join(DOCS_DIR, source)

    if source.startswith("http"):
        ## URL to text
        # loader = WebBaseLoader(source)
        # loader = UnstructuredLoader(web_url=source)
        # loader = UnstructuredURLLoader([source])

        ## URL to HTML markdown
        # firecrawl
        try:
            data = load_url_markdown(source)
        except Exception as e:
            prnt.prRed(f"Exception while loading {source}: {e}")
            return None

    elif source.endswith(".txt"):
        loader = TextLoader(filepath, encoding="utf-8")
        try:
            data = loader.load()
        except Exception as e:
            prnt.prRed(f"Exception while loading {source}: {e}")
            return None

        for idx, d in enumerate(data):
            d.metadata["type"] = "text_file"
            d.metadata["id"] = f"{source}_page-{idx}"
            # for key, val in addnl_metadata.items():
            #     d.metadata[key] = val

    elif source.endswith(".xlsx") or source.endswith(".xls"):
        sheet_tabs = None
        prnt.prLightPurple(f"Loading Excel File: {source}")

        try:
            sheet_tabs = llama_parser.load_data(filepath)
        except Exception as e:
            prnt.prRed(f"Exception while loading {source}: {e}")
            return None

        prnt.prLightPurple(f"Sheet tabs length and type: {type(sheet_tabs)}")
        # prnt.prLightPurple(f"\n{type(sheet_tabs[0])}\n{sheet_tabs[1]}")
        print(f"\n{sheet_tabs[0].text}\n")
        filename = source.split("/")[-1]
        data = convert_sheet_tabs_to_langchain_docs(filename, sheet_tabs)
        prnt.prLightPurple(f"Got {len(data)} LangChain docs.")

    elif source.endswith(".docx"):
        loader = Docx2txtLoader(filepath)
        prnt.prLightPurple(f"Loading docx File: {source}")
        try:
            data = loader.load()
        except Exception as e:
            prnt.prRed(f"Exception while loading {source}: {e}")
            return None

        for idx, d in enumerate(data):
            # print(d.page_content)
            d.metadata["type"] = "docx_file"
            d.metadata["id"] = f"{source}_page-{idx}"
            # for key, val in addnl_metadata.items():
            #     d.metadata[key] = val
    elif source.endswith(".pdf"):
        loader = PyPDFLoader(filepath)
        try:
            data = loader.load()
        except Exception as e:
            prnt.prRed(f"Exception while loading {source}: {e}")
            return None

        for idx, d in enumerate(data):
            d.metadata["source"] = source
            d.metadata["type"] = "pdf_file"
            d.metadata["id"] = f"{source}_page-{idx}"
            # for key, val in addnl_metadata.items():
            #     d.metadata[key] = val

    # prnt.prLightPurple(f"\nLoaded:\nType: {type(data)}, Length: {len(data)}\nFirst page type: {type(data[0])}\nFirst page metadata: {data[0].metadata}")

    if data:
        for d in data:
            for key, val in addnl_metadata.items():
                d.metadata[key] = val

    return data


"""### Add/Update Vector DB"""


def load_csv_row(
    row_dict: dict,
    addnl_metadata: dict = {},
):
    url = row_dict["url"]
    data = None

    try:
        # create langchain doc out of text
        data = [Document(page_content=row_dict["content"], metadata={})]
        for idx, d in enumerate(data):
            d.metadata["source"] = url
            d.metadata["type"] = "plain_text"
            d.metadata["id"] = f"{url}_page-{idx}"
            # additional metadata fields
            d.metadata["title"] = row_dict["title"]
            d.metadata["date"] = row_dict["date_serpapi"]
            d.metadata["publisher"] = row_dict["source"]
            for key, val in addnl_metadata.items():
                d.metadata[key] = val
    except Exception as e:
        prnt.prRed(f"Exception while trying to load a CSV row: {e}")

    return data


def add_or_update_vectordb(
    data_to_add: list,
    collection_name: str,
    embedded_sources: set,
    update: bool = False,
    addnl_metadata: dict = {},
    dir_name: str = None,
):
    prnt.prPurple(f"\nAdding to vector db with update = {update}\n")

    for source in data_to_add:
        data = None
        if source.endswith(".csv"):
            df = pd.read_csv(os.path.join(dir_name, source))

            for index, row in df.iterrows():
                row_dict = row.to_dict()

                url = row_dict["url"]
                if url in embedded_sources:
                    prnt.prLightPurple(f"Already embedded. Skipping: {url}")
                    continue

                prnt.prLightPurple(f"Loading row {index}")
                data = load_csv_row(row_dict=row_dict, addnl_metadata=addnl_metadata)

                if not data:
                    prnt.prRed(f"Couldn't load {url}")
                    continue

                status = chunk_and_embed(url, data, collection_name)
                if status == "success":
                    embedded_sources.update({url})
        elif "Abstract: " in source:
            # an abstract has to be embedded
            data = None

            try:
                # create langchain doc out of text
                data = [Document(page_content=addnl_metadata["abstract"], metadata={})]
                for idx, d in enumerate(data):
                    d.metadata["source"] = source
                    d.metadata["type"] = "plain_text"
                    d.metadata["id"] = f"{source}_page-{idx}"
                    # additional metadata fields
                    for key, val in addnl_metadata.items():
                        d.metadata[key] = val
            except Exception as e:
                prnt.prRed(f"Exception while trying to load an abstract: {e}")

            if not data:
                prnt.prRed(f"Couldn't load {url}")
                continue

            status = chunk_and_embed(source, data, collection_name)
            if status == "success":
                embedded_sources.update({source})

        else:
            source_name = source if source.startswith("http") else source.split("/")[-1]

            # filename = source.split("/")[-1]
            if (not update) and (source_name in embedded_sources):
                prnt.prLightPurple(f"Already embedded. Skipping: {source_name}")
                continue

            filepath = None
            if dir_name:
                filepath = os.path.join(dir_name, source)
            data = load_single_source(source, filepath, addnl_metadata)

            if not data:
                prnt.prRed(f"Couldn't load {source}")
                continue

            status = chunk_and_embed(source, data, collection_name)
            if status == "success":
                embedded_sources.update({source_name})

    return embedded_sources


"""### Chunking"""


def chunk_and_embed(source, data, collection_name: str) -> str:
    chunks = create_chunks(data)

    # chunks = create_chunks(docs)
    # print(f"Example chunk content: {chunks[0].page_content}\n")
    # print(f"\nLen Sample chunk:\n{len(chunks[0].page_content)}")

    if not chunks:
        prnt.prRed(f"Error: No chunks created for {source}.")
        return "failed"

    if source.endswith(".csv"):
        print(f"Got {len(chunks)} chunks for '{source}'")
    else:
        print(f"Got {len(chunks)} chunks for '{source}'")

    for idx, c in enumerate(chunks):
        c.metadata["id"] += f"_chunk-{idx}"
    # chunks = add_chunk_headings(source, chunks)

    status = embed_and_store_chroma(chunks=chunks, collection_name=collection_name)
    if status != "success":
        prnt.prRed(f"Embedding of source {source} failed")
        return "failed"

    return "success"


def create_chunks(docs: list, chunk_size: int = 1500, chunk_overlap: int = 200):
    """Split the loaded text documents into smaller chunks"""

    print(f"\n{'-' * 30}- CHUNKING {'-' * 30}")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(docs)

    prnt.prLightPurple(f"{len(docs)} docs have been split into {len(chunks)} chunks.")
    return chunks


"""### Embed and Store in Vector DB"""


def embed_and_store_langchain(chunks: list, collection_name: str):
    """
    Create an embedding of each chunk using LangChain and store the embeddings in a vector database.
    """
    print(f"\n{'-' * 10}- EMBEDDING & STORING THE CHUNKS IN VECTOR DB {'-' * 10}")

    global chromadb_client

    vectordb = Chroma(
        client=chromadb_client,
        collection_name=collection_name,
        embedding_function=openai_embeddings,
    )

    # uuids = [str(uuid4()) for _ in range(len(chunks))]

    # ids_added = vectordb.add_documents(documents=chunks, ids=uuids)

    batch_size = 5461  # Maximum allowed batch size
    total_chunks = len(chunks)
    print(f"Total Chunks: {total_chunks}")

    # Process chunks in batches
    for i in range(0, total_chunks, batch_size):
        batch_chunks = chunks[i : i + batch_size]

        uuids = [str(uuid4()) for _ in range(len(batch_chunks))]

        ids_added = vectordb.add_documents(documents=batch_chunks, ids=uuids)

        print(
            f"Batch {i // batch_size + 1}: Added {len(ids_added)} documents to the database."
        )

    print(f"After Count: {len(ids_added)}")


def embed_and_store_chroma(
    chunks: list,
    collection_name: str,
    # persist_directory: str = DEFAULT_PERSIST_DIR,
):
    """
    Create an embedding of each chunk using Chroma and store the embeddings in a vector database.
    """
    print(f"\n{'-' * 10}- EMBEDDING & STORING THE CHUNKS IN VECTOR DB {'-' * 10}")

    global chromadb_client

    # chromadb_client = chromadb.PersistentClient(path=persist_directory)

    collection = chromadb_client.get_or_create_collection(
        name=collection_name, embedding_function=openai_ef
    )
    print(f"Before Count: {collection.count()}")

    documents = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    # ids = [str(uuid4()) for _ in range(len(chunks))]
    ids = [c.metadata["id"] for c in chunks]

    try:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        print(f"After Count: {collection.count()}")
    except Exception as e:
        prnt.prRed(f"Upsert to collection failed due to: {e}")
        print(f"After Count: {collection.count()}")
        return e

    return "success"


"""### Delete Embeddings"""


def delete_embeddings(
    embedded_sources: set, data_to_delete: list, collection_name: str
):
    global chromadb_client

    prnt.prPurple("\nDeleting from vector db")

    collection = chromadb_client.get_or_create_collection(
        name=collection_name, embedding_function=openai_ef
    )
    prnt.prLightPurple(f"Before Count: {collection.count()}")

    for source in data_to_delete:
        source_name = source if source.startswith("http") else source.split("/")[-1]
        print(f"Trying to delete {source_name}")

        try:
            collection.delete(where={"source": source_name})
            print(f"Deleted. New Count: {collection.count()}")
            embedded_sources.remove(source_name)
        except Exception as e:
            prnt.prRed(f"Delete operation failed due to: {e}")
            print(f"New Count: {collection.count()}")
            # return e

    prnt.prLightPurple(f"\nAfter Count: {collection.count()}")

    return embedded_sources


"""### Misc"""

# Sample metadata for webpages

# Doc metadata: {'source': 'https://www.ckbhospital.com/treatment/percutaneous-nephrolithotomy', 'title': 'Percutaneous Nephrolithotomy: Procedure & Recovery - CK Birla Hospital', 'description': 'Know about Percutaneous Nephrolithotomy (PCNL) for large kidney stones and explore treatment options at CK Birla Hospital .', 'language': 'en-US'}


# Doc metadata: {'source': 'https://www.ckbhospital.com/blogs/joint-preservation-vs-replacement-understanding-options-for-joint-health', 'title': 'Joint Preservation vs. Replacement: Understanding Options for Joint Health - CK Birla Hospital', 'description': '"Learn joint preservation and replacement options for managing severe joint pain. Understand the benefits, drawbacks, and factors to consider for each approach."', 'language': 'en-US'}

# embedded_sources = {}


def webpage_to_markdown(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract main content (you may need to fine-tune this selector)
    main_content = soup.find("body")

    if not main_content:
        raise Exception("Could not find main content in webpage")

    # Convert HTML to Markdown
    markdown_text = markdownify(str(main_content))

    return markdown_text


def remove_header_footer(text):
    """Remove header and footer from the webpage markdown"""
    # remove header text
    header_end = ""
    header_end_idx = text.find(header_end)
    if header_end_idx != -1:
        text = text[header_end_idx + len(header_end) :].strip()

    # remove footer text
    footer_start = ""
    footer_start_idx = text.find(footer_start)
    if footer_start_idx != -1:
        text = text[:footer_start_idx].strip()
    # prnt.prLightPurple(f"\n\n{text}\n\n")

    return text


def load_url_markdown(url):
    ## URL to HTML doc
    # r = requests.get(url)
    # text = r.text

    text = webpage_to_markdown(url)
    cleaned_text = text
    # cleaned_text = remove_header_footer(text)
    # prnt.prYellow(cleaned_text)
    # cleaned_text = re.sub(r"\n{4,}", "\n\n\n", cleaned_text)
    cleaned_text = re.sub(r"\n{2}", "\n", cleaned_text)

    # prnt.prCyan("\n-----Here 2-------\n")
    # prnt.prLightPurple(cleaned_text)

    page_id = f"{url}_page-0" if not url.endswith("/") else f"{url[:-1]}_page-0"

    doc = Document(
        page_content=cleaned_text,
        metadata={
            "source": url,
            "type": "webpage",
            "id": page_id,
        },
    )

    # doc = add_metadata(url, doc)

    return [doc]


def convert_sheet_tabs_to_langchain_docs(filename, sheet_tabs):
    prnt.prPurple(f"Converting sheet tabs to docs for: {filename}")
    data = []

    for idx, tab in enumerate(sheet_tabs):
        matches = re.match(r"#([^\n]+)", tab.text)
        tab_title = matches.group(1).strip() if matches else f"{filename}_tab{idx}"
        print(tab_title)
        data.append(
            Document(
                page_content=tab.text,
                metadata={
                    "source": filename,
                    "title": tab_title,
                    "type": "spreadsheet",
                    "id": f"{filename}_{idx}",
                },
            )
        )

    return data


# def update_metadata(data_to_update: list, collection_name: str):
#     global chromadb_client

#     prnt.prPurple("\nUpdating given ids' metadata in the vector db")

#     collection = chromadb_client.get_or_create_collection(
#         name=collection_name, embedding_function=openai_ef
#     )
#     prnt.prLightPurple(f"Before Count: {collection.count()}")

#     for source in data_to_update:
#         source_name = source if source.startswith("http") else source.split("/")[-1]
#         print(f"Trying to update the metadata of {source_name}")
#         doc_id =
#         try:
#             collection.update(ids=None, metadatas=None)
#             print(f"Updated {source}")
#         except Exception as e:
#             prnt.prRed(f"Delete operation failed due to: {e}")
#             print(f"New Count: {collection.count()}")
#             # return e

#     prnt.prLightPurple(f"\nAfter Count: {collection.count()}")


def test_loading_chunking(sources: list):
    for source in sources:
        data = load_single_source(source)
        if not data:
            print(f"Could not load {source}")
            continue

        for d in data:
            print(f"\nMetadata: {d.metadata}\n")
            print(f"\nContent: {d.page_content}\n")
            break

        chunks = create_chunks(data)
        if not chunks:
            print("Some error while chunking")
            continue

        print(f"Got {len(chunks)} chunks for {source}")
        # chunks = add_chunk_headings(source, chunks)

        for i, chunk in enumerate(chunks):
            prnt.prYellow(f"\n~~~~~~~~~ Chunk {i} ~~~~~~~~\n")
            print(chunk.page_content)
            break

        break  # if you want to test only one source


def add_update_docs(
    data_to_add: list,
    collection_name: str,
    addnl_metadata: dict = {},
    dir_name: str = None,
    update: bool = False,
):
    """
    source_type: could be 'scholar', 'google_news', etc.
    """
    # collection_name = "grassland_biodiversity_india_Jan2025_Jan2025_news"
    print(f"Adding docs to collection: {collection_name}")
    parts = collection_name.split("_")
    embedded_sources_filepath = None
    if parts and parts[-1] == "news":
        embedded_sources_filepath = os.path.join(
            cfg.RESULTS_DIR, "_".join(parts[:-3]), parts[-1], "_".join(parts[-2:-4:-1])
        )
    elif parts and parts[-1] == "scholar":
        embedded_sources_filepath = os.path.join(
            cfg.RESULTS_DIR,
            "_".join(parts[:-3]),  # topic
            parts[-1],  # news or scholar
            f"{parts[-3][3:]}_{parts[-2][3:]}",  # years
        )
    else:
        # the collection is for a weblink
        embedded_sources_filepath = os.path.join(cfg.RESULTS_DIR, collection_name)

    print(f"embedded_sources_filepath: {embedded_sources_filepath}")

    embedded_sources_df = pd.read_csv(
        os.path.join(embedded_sources_filepath, "embedded_sources.csv")
        # os.path.join(RAG_DIR, collection_name + "_embedded_sources.csv")
    )
    embedded_sources = set(embedded_sources_df["Sources"].to_list())
    prnt.prPurple(f"Num embedded sources at the start: {len(embedded_sources)}")

    embedded_sources = add_or_update_vectordb(
        data_to_add=data_to_add,
        collection_name=collection_name,
        embedded_sources=embedded_sources,
        update=update,
        addnl_metadata=addnl_metadata,
        dir_name=dir_name,
    )

    # embedded_sources = delete_embeddings(embedded_sources, data_to_delete=urls1)

    embedded_sources_df = pd.DataFrame(list(embedded_sources), columns=["Sources"])
    embedded_sources_df.to_csv(
        os.path.join(embedded_sources_filepath, "embedded_sources.csv"),
        # os.path.join(RAG_DIR, collection_name + "_embedded_sources.csv"),
        index=False,
    )

    prnt.prPurple(f"\nNum embedded sources at the end: {len(embedded_sources)}")


def delete_docs(data_to_delete: list, collection_name: str):
    df = pd.read_csv(os.path.join(DOCS_DIR, "embedded_sources.csv"))
    embedded_sources = set(df["Sources"].to_list())
    prnt.prPurple(f"Num embedded sources at the start: {len(embedded_sources)}")

    embedded_sources = delete_embeddings(
        embedded_sources, data_to_delete, collection_name=collection_name
    )

    df = pd.DataFrame(list(embedded_sources), columns=["Sources"])
    df.to_csv(os.path.join(DOCS_DIR, "embedded_sources.csv"), index=False)

    prnt.prPurple(f"\nNum embedded sources at the end: {len(embedded_sources)}")


if __name__ == "__main__":
    dirname = "/Users/megha-personal/Documents/THT/app/results/leopards_india/scholar/2020_2025/pdf"
    scholar_docs = os.listdir(dirname)
    print(len(scholar_docs))

    sources = scholar_docs  # should be a list
    # for s in sources:
    #     print(s, type(s))

    ### --- Use this code to test loading and chunking of specific sources ----
    # test_loading_chunking(sources)

    ### --- Use this code to add or update docs in the db ---
    add_update_docs(
        sources,
        collection_name="leopards_india_Jan2020_Dec2025_scholar",
        addnl_metadata={"source_type": "scholar"},
        dir_name=dirname,
        update=False,
    )

    ### --- Use this code to delete docs from the db ---
    # delete_docs(sources)

    ### --- Answer all the questions in Questions.csv ---
    # rag.test_predefined_questions_list()

    # --- Answer any question that is entered from the terminal ---
    # rag.test_questions_on_the_go()

    # ---------------------------
    # collection = chromadb_client.get_collection(name="leopards_research_articles")
    # print(collection.count())
    # print(type(collection.peek(1)))

    # try:
    #     print(json.dumps(collection.peek(1), indent=2))
    # except:
    #     pprint.pp(collection.peek(1))

    # ---------------------------
    # add_or_update_csv(
    #     dir_name="/Users/megha-personal/Documents/THT/app/results/leopard_news/Nov2024_Nov2024",
    #     filename="parsed_news_items.csv",
    # )
