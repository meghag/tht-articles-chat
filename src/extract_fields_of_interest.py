import sys
import os
import json

from dotenv import load_dotenv, find_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# import src.config as cfg
import utils.data_utils as dut
import rag.maintain_vectordb as vec
import src.rag_query as rag

_ = load_dotenv(find_dotenv())

ROOT_DIR = "/content/drive/MyDrive/Work-related/THT/app"
curr_dir = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(curr_dir, "..", "results")

extract_fields_user_prompt = """
    "You are given relevant excerpts from a research article. Extract the information described below from the excerpts if possible.
    
    General instructions:
        - DO NOT make up stuff.
        - If you can find only partial answer, that's also okay. Respond with what you know but DO NOT make up stuff.
        - Return a JSON with the following keys and nothing else. If the value of any key can't be found, then return the value as 'Not found':
        {fields_of_interest}
        
    Excerpts: {context}
"""

# """
# "location": name of the place that the article is about.
#             "PA_name": name of the protected area(s) that the article is about.
#             "study_area": the physical area or a qualitative description of the area that was covered in the research/study.
#             "research_questions": Any ecological or research questions that have been tried to be answered in the research.
#             "org": affiliations of the author(s).
#             "summary": a well-rounded summary of the premise, methodologies, and key findings of the research.
#             "people_reaction": Reaction of the ordinary citizens to the scenario described in the research.
#             "context": the situation or the context in which the animal was studied (eg., camera trapped, attacked a human, attacked an animal, road kill, electrocuted, snared, poached, killed in retaliation etc.)
# """


extract_fields_system_prompt = "You're a helpful assistant. Extract the required information from the given context."


def find_and_save_rag_answer(
    fields: dict,
    article: dict,
    collection_name: str,
    metadata_filters: dict = {},
):
    #   - Title, author(s), year (of publication), and URL (not the scihub one) are already there.
    #   - Fetch relevant docs with metadata filtering (source = title).
    #   - RAG query to extract site name/ location, PA name, extent of the study, any ecological questions/reason for the study, PI/Organization name, summary, people's reaction, context/Situation (eg., camera trapped, attacked a human, attacked an animal, road kill, electrocuted, snared, poached, killed in retaliation etc.)
    relevant_content = []
    print("Getting relevant docs...")
    for field_name, field_description in fields.items():
        # print(f"Getting relevant docs for {field_name}")
        relevant_docs = rag.retrieve_docs_alt(
            collection_name=collection_name,
            # title=article["title"],
            # metadata_filters={"title": {"$eq": article["title"]}},
            metadata_filters=metadata_filters,
            query=field_description,
            debug=False,
        )

        relevant_content.extend([doc.page_content for doc in relevant_docs])

    context = "\n\n".join([content for content in relevant_content])

    print("Finding RAG answer...")
    answer = rag.rag_for_field_extraction(
        context,
        fields,
        user_prompt=extract_fields_user_prompt,
        # .format(
        #     fields_of_interest=fields, context=context
        # )
        system_prompt=extract_fields_system_prompt,
    )
    print(f"{answer}\n\n")

    try:
        answer = answer.replace("```json", "")
        answer = answer.replace("```", "")
        answer = json.loads(answer.strip())
        for key, val in answer.items():
            article[key] = val
    except Exception as e:
        print(f"Exception while parsing LLM output: {e}")

    return article


if __name__ == "__main__":
    # Load the JSON file containing the search results from Google Scholar into a list.
    json_filepath = "/Users/megha-personal/Documents/THT/app/trial_results/leopards_scholarly_results_trial.json"
    all_articles = dut.load_json(json_filepath)
    if all_articles:
        print(f"Sample article info:\n{all_articles[0]}\n")

    # List all the downloaded files.
    downloaded_files_dir = "/Users/megha-personal/Documents/THT/app/trial_results/pdf"
    downloaded_articles = os.listdir(downloaded_files_dir)
    print(f"Num articles downloaded: {len(downloaded_articles)}\n")

    # For each article in the search results:
    #   - Get title and check for it in the downloaded list. If present:
    #       - Embed the downloaded article in the vector DB.
    #       - Add source_type (scholar/news/etc.) and title to metadata.
    fields = dut.load_json(
        "/Users/megha-personal/Documents/THT/app/rag/leopard_research_articles_questions.json"
    )
    # print(fields)

    processed_articles = []
    for article in all_articles:
        title = article["title"]
        title = title.replace(":", "_") + ".pdf"
        if title in downloaded_articles:
            print(f"\nFound in downloaded list: '{title}'\n")

            print("Adding to the vector db if not present...")
            vec.add_update_docs(
                [title],
                collection_name="leopards_research_articles",
                addnl_metadata={"source_type": "scholar", "title": article["title"]},
                dir_name=downloaded_files_dir,
                update=False,
            )

            if "location" not in article:
                updated_article = find_and_save_rag_answer(fields, article)
                if "location" in updated_article:
                    processed_articles.append(updated_article)

    dut.save_to_json(
        results=processed_articles,
        dirname="/Users/megha-personal/Documents/THT/app/trial_results",
        filename="leopards_scholarly_processed_results_trial.json",
    )

    # else:
    #     print(f"\nDidn't find {title} in downloaded list.\n")
