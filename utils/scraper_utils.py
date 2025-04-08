import os
import sys
import json
from typing import List, Set, Tuple, Dict

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
    LLMConfig,
    JsonCssExtractionStrategy,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from models.news_item import NewsItem
from utils.data_utils import is_complete_news_item  # , is_duplicate_news_item
from src.config import SCHEMA_MAP


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
        verbose=False,  # Enable verbose logging
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


def get_json_css_strategy(publication: str) -> JsonCssExtractionStrategy:
    if publication in SCHEMA_MAP:
        return JsonCssExtractionStrategy(SCHEMA_MAP[publication], verbose=True)

    print(f"\nDidn't find any json_css_schema for {publication}\n")
    return None


async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    article_details: Dict,
    # llm_strategy: LLMExtractionStrategy,
    # json_css_strategy: JsonCssExtractionStrategy,
    session_id: str,
    required_keys: List[str],
) -> List[dict]:
    """
    Fetches and processes a single page of news_item data.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        url (str): The URL of the article.
        session_id (str): The session identifier.
        required_keys (List[str]): List of required keys in the news_item data.

    Returns:
        - List[dict]: A list of processed news_items from the page.
    """
    url = article_details["link"]
    extraction_strategy = get_json_css_strategy(article_details["source"])
    if not extraction_strategy:
        return []

    # Fetch page content with the extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            extraction_strategy=get_json_css_strategy(
                article_details["source"]
            ),  # Strategy for data extraction
            session_id=session_id,  # Unique session ID for the crawl
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {url}: {result.error_message}")
        return []

    # Parse extracted content
    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        print(f"No news_items found on page {url}.")
        return []

    # Debugging: Print each news_item to understand its structure after parsing extracted content
    print("\nExtracted data:", extracted_data)

    # Process news items
    news_items = []
    for i, news_item in enumerate(extracted_data):
        print(f"\nProcessing news_item {i} in extracted data")
        news_item["title"] = article_details["title"]
        news_item["source"] = article_details["source"]
        news_item["url"] = url

        if not is_complete_news_item(news_item, required_keys):
            continue  # Skip incomplete news_items

        # if is_duplicate_news_item(news_item["name"], seen_names):
        #     print(f"Duplicate news_item '{news_item['name']}' found. Skipping.")
        #     continue  # Skip duplicate news_items

        # Add news_item to the list
        news_items.append(news_item)

    # print(f"Extracted {len(news_items)} news_items from page {url}.")
    return news_items
