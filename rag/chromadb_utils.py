import os
import sys
import chromadb
import sqlite3


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import src.rag_query as rag

curr_dir = os.path.dirname(__file__)
PERSIST_DIR = str(os.path.join(curr_dir, "..", "test_db"))
SQLITE_FILE = os.path.join(PERSIST_DIR, "chroma.sqlite3")
chromadb_client = chromadb.PersistentClient(path=PERSIST_DIR)


def get_collections():
    collections = chromadb_client.list_collections()

    # Get just the names
    # collection_names = [collection.name for collection in collections]

    return collections


def query_collection(selected_collection, user_input):
    return rag.rag_langchain_without_history(
        query=user_input, collection_names=[selected_collection]
    )


def delete_collection(collection_name):
    chromadb_client.delete_collection(name=collection_name)
    print(f"Deleted collection: {collection_name}")


def fetch_table_column_names():
    """for admin and debugging purpose only"""

    conn = sqlite3.connect(SQLITE_FILE)
    cursor = conn.cursor()

    # See what tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)

    # See columns in the collections table
    cursor.execute("PRAGMA table_info(collections);")
    columns = cursor.fetchall()
    print("Collections table columns:")
    for col in columns:
        print(col)

    # Get IDs of collections that still exist in DB
    try:
        cursor.execute("SELECT id FROM collections")
        ids_in_db = set(row[0] for row in cursor.fetchall())
        print("Active collection IDs:", ids_in_db)
    except sqlite3.OperationalError as e:
        print(f"Could not query DB: {e}")
        # conn.close()
        # return

    conn.close()


def get_example_questions(collection_name):
    return {
        "leopards_india_Jan2020_Dec2025_scholar": [
            "What is the current distribution and estimated population of leopards in India at national and regional scales?",
            "How reliable and recent are the population estimates of leopards in different Indian landscapes?",
            "Which regions have seen significant population increases or declines in leopards over the past two decades?",
            "What methods (camera trapping, DNA analysis, sign surveys) are used for leopard monitoring in India, and how standardized are they across landscapes?",
            "How is leopard presence being monitored outside Protected Areas, especially in human-dominated landscapes?",
            "How do leopard home range sizes and movement patterns vary across habitats (forest, scrub, agro-pastoral, peri-urban, etc.)?",
            "What do we know about leopard diet across different landscapes, and how much of it consists of livestock or feral prey?",
            "How do leopards coexist with other large carnivores like tigers, dholes, or wolves across overlapping habitats?",
            "What role do leopards play in ecosystem functioning where they are apex predators?",
            "What are the major threats facing leopards in India today—poaching, habitat loss, conflict, infrastructure, or others?",
            "How is leopard conservation addressed in policies and action plans (e.g., National Wildlife Action Plan, State Wildlife Boards)?",
            "Are there dedicated recovery programs or landscape-level strategies for leopard conservation in India?",
            "How have translocation or rescue-and-release operations impacted leopard behavior and survival?",
            "What is the status of leopard conservation outside tiger reserves—are they getting due attention in dry, arid, or mountain habitats?",
            "What are the patterns and drivers of leopard-human conflict in different parts of India?",
            "How do conflict mitigation strategies (e.g., early warning systems, livestock compensation, awareness campaigns) perform across states?",
            "How are urban leopards (e.g., in Mumbai, Bengaluru) adapting to city environments, and what are the implications for urban planning and coexistence?",
            "How are local communities, especially in high-conflict zones, involved in leopard conservation or conflict management?",
            "What are the gaps in leopard research in India, especially concerning non-protected areas and non-forest habitats?",
            "Is there a centralized, accessible database of leopard sightings, mortalities, conflict cases, and camera trap records?",
            "How are new technologies—like AI-powered image recognition, eDNA, or telemetry—being used in leopard studies?",
            "What are the genetic diversity patterns of leopards across India, and are there signs of inbreeding or population fragmentation?",
            "How effective is the current legal protection under the Wildlife Protection Act in safeguarding leopards?",
            "Are there specific state or local policies aimed at leopard management, and how are they implemented?",
            "What ethical concerns arise in the management of 'problem' leopards, including capture, holding, and release practices?",
        ],
        # "wildlife_articles": [
        #     "What are the major threats to tigers?",
        #     "Give me recent updates on elephant corridors in India.",
        # ],
    }.get(collection_name, [])


if __name__ == "__main__":
    fetch_table_column_names()
