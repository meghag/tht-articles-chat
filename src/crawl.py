import asyncio
import os
import json
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import src.config as cfg
from utils.data_utils import (
    save_news_items_to_csv,
    save_to_json,
    save_single_news_item_to_csv,
)
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    # get_llm_strategy,
    # get_json_css_strategy,
)
import utils.print_utils as prnt

load_dotenv()

curr_dir = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(curr_dir, "..", "results")


async def crawl_news_items(
    data: list,
    parsed_urls: list,
    failed_urls: list,
    results_dirname: str,
    source_to_parse: str = "all",
):
    """
    Main function to crawl venue data from the website.
    """
    # Initialize configurations
    browser_config = get_browser_config()
    session_id = "news_items_crawl_session"

    # Initialize state variables
    article_number = 1
    all_news_items = []

    if source_to_parse != "all":
        data = [d for d in data if d["source"] == source_to_parse]

    # Start the web crawler context
    # https://docs.crawl4ai.com/api/async-webcrawler/#asyncwebcrawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for item in data:
            print(f"\n----{article_number}------")  # \n{item}\n")
            url = item["link"]
            if url in parsed_urls:
                prnt.prLightPurple("Item already parsed. Skipping it.")
                article_number += 1  # Move to the next article
                continue

            # Fetch and process data from the current page
            news_items = await fetch_and_process_page(
                crawler,
                item,
                session_id,
                cfg.REQUIRED_KEYS,
            )

            if not news_items:
                prnt.prRed(f"No news_items extracted from page {item['link']}.")
                # failed_items.append(item)
                failed_urls.append(url)
            else:
                # Add the news_items from this page to the total list
                all_news_items.extend(news_items)
                parsed_urls.append(url)
                if url in failed_urls:
                    failed_urls.remove(url)

                for news_item in news_items:
                    save_single_news_item_to_csv(
                        results_dirname, news_item, "parsed_news_items.csv"
                    )
            break
            article_number += 1  # Move to the next article

            # Pause between requests to be polite and avoid rate limits
            await asyncio.sleep(2)  # Adjust sleep time as needed

    # save_to_json(results=failed_items, filename="failed_news_items.json")
    save_to_json(
        dirname=results_dirname,
        filename="failed_urls.json",
        results=list(set(failed_urls)),
    )

    # TODO: Do this after every url, not at the end
    # Save the collected news_items to a CSV file
    if all_news_items:
        save_news_items_to_csv(
            all_news_items, "all_parsed_news_items.csv", results_dirname
        )
        save_to_json(
            dirname=results_dirname,
            filename="parsed_urls.json",
            results=list(set(parsed_urls)),
        )
    else:
        print("No news items were found during the crawl.")

    # Display usage statistics for the LLM strategy
    # llm_strategy.show_usage()


async def main():
    """
    Entry point of the script.
    """
    dirname = cfg.google_news_inputs["dirname"]  # same as INPUT 5 in google_news.py
    start_date = cfg.google_news_inputs[
        "start_date"
    ]  # same as INPUT 6 in google_news.py
    end_date = cfg.google_news_inputs["end_date"]  # same as INPUT 7 in google_news.py

    overall_period = (
        f"{str(start_date).replace('/', '-')}_{str(end_date).replace('/', '-')}"
    )
    results_dirname = os.path.join(RESULTS_DIR, dirname, overall_period)
    filename = f"{overall_period}.json"
    filepath = os.path.join(results_dirname, filename)
    parsed_urls_filepath = os.path.join(results_dirname, "parsed_urls.json")
    failed_urls_filepath = os.path.join(results_dirname, "failed_urls.json")

    data = None
    with open(filepath, "r", encoding="utf-8") as f1:
        data = json.load(f1)
        print(f"Number of URLs to parse: {len(data)}")
        # print(json.dumps(data[0], indent=2))

    parsed_urls = []
    with open(parsed_urls_filepath, "r", encoding="utf-8") as f2:
        parsed_urls = json.load(f2)
        print(f"\nNumber of parsed URLs: {len(parsed_urls)}")
        # print(parsed_urls)

    failed_urls = []
    with open(failed_urls_filepath, "r", encoding="utf-8") as f3:
        failed_urls = json.load(f3)
        print(f"\nNumber of failed URLs: {len(failed_urls)}")

    await crawl_news_items(
        data, parsed_urls, failed_urls, results_dirname
    )  # , source_to_parse="ThePrint")


if __name__ == "__main__":
    asyncio.run(main())
