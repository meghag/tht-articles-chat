import os
import sys
import json
from dotenv import load_dotenv, find_dotenv
from serpapi import GoogleSearch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


import utils.print_utils as prnt
from datetime import datetime, timedelta
from utils.data_utils import save_to_json, remove_duplicates
import src.config as cfg


_ = load_dotenv(find_dotenv())

curr_dir = os.path.dirname(__file__)
print(curr_dir)
RESULTS_DIR = os.path.join(curr_dir, "..", "results")
print(f"RESULTS DIR: {RESULTS_DIR}")

DEBUG = 0
prnt.prYellow(f"DEBUG = {DEBUG}")

serp_api_key = os.getenv("SERPAPI_KEY")


def google_search(
    keyphrase: str,
    start_date: str,  # in MM/DD/YYYY format
    end_date: str,  # in MM/DD/YYYY format
    filename: str,
    offset: int = 0,
):
    params = {
        "q": keyphrase,
        "tbm": "nws",  # to search only Google News
        "location": "India",
        "hl": "en",  # define the language of the results
        "tbs": f"cdr:1,cd_min:{start_date},cd_max:{end_date},sbd:1",  # custom date range, language, and sorted by date # lr=lang_en
        "start": offset,  # the number of results to skip in the beginning
        "num": 100,  # max number of results to return, may not work correctly
        "api_key": os.getenv("SERPAPI_KEY"),
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    news_results = []
    if results["search_information"].get("total_results"):
        print(f"Found {results['search_information']['total_results']} results.")
        news_results = results["news_results"]
    else:
        prnt.prRed("Some error occured. Didn't get results.")
        return news_results

    # Save results to a JSON file
    with open(
        os.path.join(curr_dir, "..", "json", filename),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(news_results, f, indent=4)

    print(f"Saved {len(news_results)} articles to {filename}")

    return news_results


def fetch_news_paginated(keyphrase: str, start_date: str, end_date: str) -> list:
    prnt.prPurple(f"Fetching news from {start_date} to {end_date}...")

    all_results = []

    params = {
        "q": keyphrase,
        "tbm": "nws",
        "location": "India",
        "hl": "en",
        "tbs": f"cdr:1,cd_min:{start_date},cd_max:{end_date}",
        # "num": 10,  # Fetching smaller batches
        "api_key": serp_api_key,
    }

    # for offset in range(0, pages * 10, 10):  # Adjust pagination step if needed
    offset = 0
    while True:
        # for _ in range(2):
        params["start"] = offset
        results = {}

        # response = requests.get("https://serpapi.com/search", params=params)
        # data = response.json()
        try:
            prnt.prLightPurple(
                f"\nStarting search for {start_date} to {end_date} with offset {offset}..."
            )
            search = GoogleSearch(params)
            results = search.get_dict()

        except Exception as e:
            prnt.prRed(f"Exception while searching: {e}")
            break

        if "news_results" in results:
            print(f"Found {len(results['news_results'])} results.")
            news_results = results["news_results"]
            all_results += news_results

            if len(news_results) < 10:
                # all pages seem to have been exhausted for this time range
                break
        else:
            prnt.prRed("Didn't get any results.")
            break

        offset += 10

    return all_results


def get_start_end_dates(year, month, period: str):
    start, end = None, None

    if period == "first-half":
        start = datetime(year, month, 1).strftime("%m/%d/%Y")
        end = datetime(year, month, 15).strftime("%m/%d/%Y")
    elif period == "second-half":
        start = datetime(year, month, 16).strftime("%m/%d/%Y")
        end = datetime(year, month, 1) + timedelta(days=32)
        end = end.replace(day=1) - timedelta(days=1)
        end = end.strftime("%m/%d/%Y")

    return start, end


def fetch_news_for_date_range(
    keyphrase: str, start_date: str, end_date: str, results_dirname: str
):
    current_date = datetime.strptime(start_date, "%m/%d/%Y")
    end_date = datetime.strptime(end_date, "%m/%d/%Y")

    all_articles = []
    while current_date <= end_date:
        month = current_date.month
        year = current_date.year

        # Define two periods per month
        for half in ["first-half", "second-half"]:
            period_start, period_end = get_start_end_dates(year, month, period=half)
            period = f"{str(period_start).replace('/', '-')}_{str(period_end).replace('/', '-')}"
            articles = fetch_news_paginated(keyphrase, period_start, period_end)
            all_articles.extend(articles)
            save_to_json(
                dirname=os.path.join(results_dirname, "temp_files"),
                filename=f"{period}.json",
                results=articles,
            )

        # Move to next month
        current_date = datetime(year, month, 28) + timedelta(
            days=4
        )  # Ensures we reach the next month
        current_date = current_date.replace(day=1)

    return all_articles


if __name__ == "__main__":
    keyphrase = cfg.google_news_inputs["keyphrase"]  # "leopard india"  # INPUT 4
    dirname = cfg.google_news_inputs["dirname"]  # "leopard_news"  # INPUT 5
    start_date = cfg.google_news_inputs["start_date"]  # "01/01/2025"  # INPUT 6
    end_date = cfg.google_news_inputs["end_date"]  # "03/31/2025"  # INPUT 7

    overall_period = (
        f"{str(start_date).replace('/', '-')}_{str(end_date).replace('/', '-')}"
    )
    results_dirname = os.path.join(RESULTS_DIR, dirname, overall_period)

    # Fetch news in 2-week intervals from Jan 1, 2025, to Mar 31, 2025
    news_articles = fetch_news_for_date_range(
        keyphrase, start_date, end_date, results_dirname
    )
    prnt.prYellow(f"\nTotal articles fetched: {len(news_articles)}")
    save_to_json(
        dirname=results_dirname,
        filename=f"{overall_period}.json",
        results=news_articles,
    )

    remove_duplicates(dirname=results_dirname, filename=f"{overall_period}.json")
