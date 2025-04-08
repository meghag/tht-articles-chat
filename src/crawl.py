import asyncio
import os
import json
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

from config import REQUIRED_KEYS
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.data_utils import save_news_items_to_csv, save_to_json
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    # get_llm_strategy,
    # get_json_css_strategy,
)

load_dotenv()

curr_dir = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(curr_dir)


async def crawl_news_items(data: list):
    """
    Main function to crawl venue data from the website.
    """
    # Initialize configurations
    browser_config = get_browser_config()
    # llm_strategy = get_llm_strategy()
    session_id = "news_items_crawl_session"

    # Initialize state variables
    article_number = 1
    all_news_items = []
    parsed_urls = []
    failed_items = []

    # Start the web crawler context
    # https://docs.crawl4ai.com/api/async-webcrawler/#asyncwebcrawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for item in data:
            print(f"\n----{article_number}------\n{item}\n")
            # Fetch and process data from the current page
            news_items = await fetch_and_process_page(
                crawler,
                item,
                # llm_strategy,
                # json_css_strategy,
                session_id,
                REQUIRED_KEYS,
            )

            if not news_items:
                print(f"No news_items extracted from page {item['link']}.")
                failed_items.append(item)
            else:
                # Add the news_items from this page to the total list
                all_news_items.extend(news_items)
                parsed_urls.append(item["link"])
            # break
            article_number += 1  # Move to the next page

            # Pause between requests to be polite and avoid rate limits
            await asyncio.sleep(2)  # Adjust sleep time as needed

    save_to_json(results=failed_items, filename="failed_news_items.json")

    # TODO: Do this after every url, not at the end
    # Save the collected news_items to a CSV file
    if all_news_items:
        save_news_items_to_csv(all_news_items, "parsed_news_items.csv")
        save_to_json(results=parsed_urls, filename="parsed_urls.csv")
    else:
        print("No news items were found during the crawl.")

    # Display usage statistics for the LLM strategy
    # llm_strategy.show_usage()


async def main():
    """
    Entry point of the script.
    """
    filename = "test.json"  # "leopard_news_01-01-2025_03-31-2025.json"  # INPUT 9
    filepath = os.path.join(ROOT_DIR, "json", "no_dups", filename)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"Number of URLs: {len(data)}")
        print(json.dumps(data[0], indent=2))

        await crawl_news_items(data)


if __name__ == "__main__":
    asyncio.run(main())
