import json
import os
from typing import List, Set, Tuple

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
    LLMConfig,
)

from models.news_item import NewsItem
from utils.data_utils import is_complete_news_item  # , is_duplicate_venue


def get_browser_config() -> BrowserConfig:
    """
    Returns the browser configuration for the crawler.

    Returns:
        BrowserConfig: The configuration settings for the browser.
    """
    # https://docs.crawl4ai.com/core/browser-crawler-config/
    return BrowserConfig(
        browser_type="chromium",  # Type of browser to simulate
        headless=True,  # Whether to run in headless mode (no GUI)
        verbose=True,  # Enable verbose logging
    )


def get_llm_strategy() -> LLMExtractionStrategy:
    """
    Returns the configuration for the language model extraction strategy.

    Returns:
        LLMExtractionStrategy: The settings for how to extract data using LLM.
    """
    # https://docs.crawl4ai.com/api/strategies/#llmextractionstrategy
    return LLMExtractionStrategy(
        # provider="groq/deepseek-r1-distill-llama-70b",  # Name of the LLM provider
        llm_config=LLMConfig(
            provider="groq/gemma2-9b-it",
            api_token=os.getenv("GROQ_API_KEY"),
        ),  # API token for authentication
        schema=NewsItem.model_json_schema(),  # JSON schema of the data model
        extraction_type="schema",  # Type of extraction to perform
        instruction=(
            "Extract the main news item object with 'title', 'date', 'publication', the content of the whole news item as 'article_content', "
            "'url', and a summary of the news item within 300 words from the "
            "following content."
        ),  # Instructions for the LLM
        input_format="markdown",  # Format of the input content
        verbose=True,  # Enable verbose logging
    )


async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    # page_number: int,
    base_url: str,
    # css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    # seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    """
    Fetches and processes a single page of news_item data.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        page_number (int): The page number to fetch.
        base_url (str): The base URL of the website.
        css_selector (str): The CSS selector to target the content.
        llm_strategy (LLMExtractionStrategy): The LLM extraction strategy.
        session_id (str): The session identifier.
        required_keys (List[str]): List of required keys in the news_item data.
        seen_names (Set[str]): Set of news_item names that have already been seen.

    Returns:
        Tuple[List[dict], bool]:
            - List[dict]: A list of processed news_items from the page.
            - bool: A flag indicating if the "No Results Found" message was encountered.
    """
    # url = f"{base_url}?page={page_number}"
    url = base_url
    # print(f"Loading page {page_number}...")

    # Fetch page content with the extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            extraction_strategy=llm_strategy,  # Strategy for data extraction
            # css_selector=css_selector,  # Target specific content on the page
            session_id=session_id,  # Unique session ID for the crawl
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {url}: {result.error_message}")
        return [], False

    # Parse extracted content
    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        print(f"No news_items found on page {url}.")
        return [], False

    # After parsing extracted content
    print("Extracted data:", extracted_data)

    # return extracted_data, False

    # Process news items
    complete_news_items = []
    for news_item in extracted_data:
        # Debugging: Print each news_item to understand its structure
        print("Processing news_item:", news_item)

        # Ignore the 'error' key if it's False
        if news_item.get("error") is False:
            news_item.pop("error", None)  # Remove the 'error' key if it's False

        if not is_complete_news_item(news_item, required_keys):
            continue  # Skip incomplete news_items

        # if is_duplicate_news_item(news_item["name"], seen_names):
        #     print(f"Duplicate news_item '{news_item['name']}' found. Skipping.")
        #     continue  # Skip duplicate news_items

        # Add news_item to the list
        # seen_names.add(news_item["name"])
        complete_news_items.append(news_item)

    if not complete_news_items:
        print(f"No complete news_items found on page {url}.")
        return [], False

    print(f"Extracted {len(complete_news_items)} news_items from page {url}.")
    return complete_news_items, False  # Continue crawling
