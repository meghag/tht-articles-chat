import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import src.config as cfg
import utils.print_utils as pr
from models.scholar_search import ScholarSearch


if __name__ == "__main__":
    print("Arguments received:", sys.argv[1])
    # scholar_search = ScholarSearch(cfg.google_scholar_inputs)
    scholar_search = ScholarSearch(json.loads(sys.argv[1]))
    print(scholar_search)

    # 1. Search for a keyphrase and extract results from Google Scholar in a JSON
    # results = new_search.search_scholar_with_scholarly()
    scholar_search.search_scholar_with_serpapi(pages_per_year=1)

    # 2. Clean up the search results based on year and title, also remove duplicates
    scholar_search.cleanup_scholar_results()

    # 3. Search for each title on Semantic Scholar and try getting the abstract
    scholar_search.enrich_with_abstracts()

    # 4. Search for each title on Science Hub and try downloading it if it hasn't been downloaded already
    scholar_search.search_and_download_from_scihub()

    # 5. Embed the newly-downloaded articles in the vector DB
    scholar_search.embed_in_vectordb()

    # 6. Extract fields of interest and save them in a CSV
    scholar_search.extract_fields_of_interest()


"""
def search_scholar_with_serpapi(
    keyword, filename="scholar_results.json", years=10
) -> list:
    results = []
    current_year = time.gmtime().tm_year
    params = {
        "engine": "google_scholar",
        "q": f"{keyword} after:{current_year - years}",
        "api_key": os.getenv("SERPAPI_KEY"),
    }

    search = GoogleSearch(params)
    scholar_results = search.get("organic_results", [])

    for result in scholar_results[:5]:  # Fetch top 5 results
        results.append(
            {
                "title": result.get("title", "No Title"),
                "author": result.get("publication_info", {}).get(
                    "authors", "No Author"
                ),
                "year": result.get("publication_info", {}).get("year", "No Year"),
                "url": result.get("link", "No URL"),
            }
        )

    return results
"""
