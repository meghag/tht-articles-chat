import asyncio

from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

from config import BASE_URL, CSS_SELECTOR, REQUIRED_KEYS

from utils.data_utils import (
    save_news_items_to_csv,
)
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    get_llm_strategy,
)

load_dotenv()


async def crawl_news_items():
    """
    Main function to crawl venue data from the website.
    """
    # Initialize configurations
    browser_config = get_browser_config()
    llm_strategy = get_llm_strategy()
    session_id = "news_items_crawl_session"

    # Initialize state variables
    page_number = 1
    all_news_items = []
    seen_names = set()

    # Start the web crawler context
    # https://docs.crawl4ai.com/api/async-webcrawler/#asyncwebcrawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        while True:
            # Fetch and process data from the current page
            news_items, no_results_found = await fetch_and_process_page(
                crawler,
                # page_number,
                BASE_URL,
                # CSS_SELECTOR,
                llm_strategy,
                session_id,
                REQUIRED_KEYS,
                # seen_names,
            )

            if no_results_found:
                print("No more news_items found. Ending crawl.")
                break  # Stop crawling when "No Results Found" message appears

            if not news_items:
                print(f"No news_items extracted from page {BASE_URL}.")
                break  # Stop if no news_items are extracted

            # Add the news_items from this page to the total list
            all_news_items.extend(news_items)
            break
            # page_number += 1  # Move to the next page

            # Pause between requests to be polite and avoid rate limits
            # await asyncio.sleep(2)  # Adjust sleep time as needed

    # Save the collected news_items to a CSV file
    if all_news_items:
        save_news_items_to_csv(all_news_items, "complete_news_items.csv")
        print(f"Saved {len(all_news_items)} news_items to 'complete_news_items.csv'.")
    else:
        print("No news items were found during the crawl.")

    # Display usage statistics for the LLM strategy
    llm_strategy.show_usage()


async def main():
    """
    Entry point of the script.
    """
    await crawl_news_items()


if __name__ == "__main__":
    asyncio.run(main())
