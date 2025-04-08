import sys
import os
import json
import random
import time
import requests
from serpapi import GoogleSearch
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup
from scholarly import scholarly, ProxyGenerator
from scidownl import scihub_download


_ = load_dotenv(find_dotenv())

ROOT_DIR = "/content/drive/MyDrive/Work-related/THT/app"


# # List of proxy servers (Replace with real working proxies)
# proxies = [
#     "http://username:password@proxy1.com:port",
#     "http://username:password@proxy2.com:port",
#     "http://username:password@proxy3.com:port"
# ]

# def get_random_proxy():
#     return {"http": random.choice(proxies), "https": random.choice(proxies)}


"""### Collecting relevant articles from Google Scholar"""


def search_scholar_with_scholarly(keyword: str, years: int = 10) -> list[dict]:
    results = []
    current_year = time.gmtime().tm_year
    query = f"{keyword} after:{current_year - years}"

    # # Set up a proxy generator for scholarly
    # pg = ProxyGenerator()
    # proxy = random.choice(proxies)  # Pick a random proxy
    # pg.SingleProxy(http=proxy, https=proxy)
    # scholarly.use_proxy(pg)

    # Set up a ProxyGenerator object to use free proxies
    # This needs to be done only once per session
    # pg = ProxyGenerator()
    # success = pg.FreeProxies()
    # if not success:
    #   print("Could not set up free proxy. Exiting.")
    #   return

    # scholarly.use_proxy(pg)

    # search_query = scholarly.search_pubs(keyword)
    search_query = scholarly.search_pubs(query)
    print(f"{'-' * 30}\n{search_query}\n{'-' * 30}")

    # Introduce a random delay between API calls to avoid detection
    time.sleep(random.uniform(3, 7))

    # for i in range(5):  # Fetch top 5 results
    while True:
        try:
            article = next(search_query)
            results.append(
                {
                    "title": article.get("bib", {}).get("title", "No Title"),
                    "author": article.get("bib", {}).get("author", "No Author"),
                    "year": article.get("bib", {}).get("pub_year", "No Year"),
                    "url": article.get("pub_url", "No URL"),
                }
            )

        except StopIteration:
            break

    return results


def search_scholar_with_serpapi(keyword, filename="scholar_results.json", years=10):
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

    # Save results to a JSON file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"Saved {len(results)} articles to {filename}")


"""### Cleaning up Google Scholar search results"""


# Preprocess the JSON to filter out results that do not fit the time period or the keyphrase
def cleanup_scholar_results(
    results: list[dict],
    keywords: list[str],
    current_year: int = 2025,
    start_year: int = 2015,
) -> list[dict]:
    to_remove = []

    print(f"Num articles before: {len(results)}")
    for res in results:
        year = int(res["year"]) if res["year"] not in ["No Year", "NA"] else -1
        # print(year)
        if not ((year <= current_year) and (year >= start_year)):
            # print(f"Removing: ({year}) {res['title']}")
            to_remove.append(res)
            continue

        for k in keywords:
            if k.lower() not in res["title"].lower():
                # print(f"Removing: {res['title']}")
                to_remove.append(res)
                break

    print(f"\nTo remove: {len(to_remove)}")
    # Save to_remove to a JSON file
    removed_filename = "removed_" + results_filename
    removed_filepath = os.path.join(ROOT_DIR, "json", removed_filename)
    with open(removed_filepath, "w", encoding="utf-8") as f:
        json.dump(to_remove, f, indent=4)

    print(f"Saved {len(to_remove)} articles to {removed_filename}")

    updated_results = [res for res in results if res not in to_remove]
    # new_results = list(set(results) - set(to_remove))
    print(f"Num articles after: {len(updated_results)}")

    # Save new_results to a JSON file
    updated_filename = "updated_" + results_filename
    updated_filepath = os.path.join(ROOT_DIR, "json", updated_filename)
    with open(updated_filepath, "w", encoding="utf-8") as f:
        json.dump(updated_results, f, indent=4)

    print(f"Saved {len(updated_results)} articles to {updated_filename}")

    return updated_results


"""### Finding the link to an article on Sci-hub from the html (incomplete)"""


def find_link_to_pdf(url, keyword):
    try:
        headers = {
            "User-Agent": random.choice(
                [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                ]
            )
        }

        response = requests.get(url, headers=headers)  # , proxies=get_random_proxy())
        response.raise_for_status()

        time.sleep(random.uniform(5, 10))

        soup = BeautifulSoup(response.text, "html.parser")

        pdf_links = []
        for embed in soup.find_all("embed", src=True):
            pdf_links.append(embed["src"])

        return pdf_links

    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching data: {e}"}


def search_and_download_from_scihub(articles: list):
    downloaded = os.listdir(os.path.join(ROOT_DIR, "pdf"))
    print(downloaded)
    print(len(downloaded))

    for i, res in enumerate(articles):
        try:
            title = res["title"]
            if title + ".pdf" in downloaded:
                continue

            print(f"\n\n------\nTrying: {title}")
            scihub_download(
                keyword=title,
                paper_type="title",
                out=os.path.join(ROOT_DIR, "pdf", title),
            )
        except Exception as e:
            print(f"Exception for idx {i}: {e}")


def load_results_from_json_file(filename: str):
    # results_filepath = os.path.join(ROOT_DIR, 'json', filename)
    results_filepath = "/content/drive/MyDrive/Work-related/THT/app/json/leopards_scholarly_results.json"
    results_filename = results_filepath.split("/")[-1]
    print(results_filename)
    results = None
    with open(results_filepath, "r", encoding="utf-8") as f:
        results = json.load(f)
    print(results[:5])

    return results


"""## Pipeline
1.   Search for a keyphrase and extract results from Google Scholar in a JSON
2.   Preprocess the JSON to filter out results that do not fit the time period or the keyphrase
3.   Search for each title on Science Hub and try downloading it if it hasn't been downloaded already
4.   Embed and save the new docs in the vector db
"""

if __name__ == "__main__":
    # ------------------------------------------------------
    # Search for a keyphrase and extract results from Google Scholar in a JSON
    keyphrase = "leopards in india"  # INPUT 1
    years = 1  # INPUT 2
    results_filename = (
        "_".join(keyphrase.split() + ["scholarly", "results", str(years) + "years"])
        + ".json"
    )
    results_filepath = os.path.join(ROOT_DIR, "json", results_filename)
    print(results_filepath)
    results = search_scholar_with_scholarly(keyword=keyphrase, years=years)

    # Save results to a JSON file
    with open(results_filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"Saved {len(results)} articles to {results_filepath}")

    # ------------------------------------------------------
    # Or load the JSON if you have the results saved already
    # filepath = os.path.join(ROOT_DIR, 'json', filename)
    results_filepath = "/content/drive/MyDrive/Work-related/THT/app/json/leopards_scholarly_results.json"
    results_filename = results_filepath.split("/")[-1]
    print(results_filename)
    results = None
    with open(results_filepath, "r", encoding="utf-8") as f:
        results = json.load(f)
    print(results[:5])

    # ------------------------------------------------------
    # Clean up the search results based on year and title
    keywords = ["leopard", "India"]  # INPUT 3
    updated_results = cleanup_scholar_results(results, keywords)

    # ------------------------------------------------------
    # Search for each title on Science Hub and try downloading it if it hasn't been downloaded already
    search_and_download_from_scihub(updated_results)
