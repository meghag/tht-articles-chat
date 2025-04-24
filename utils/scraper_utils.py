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
from utils.data_utils import (
    has_all_required_keys,
    get_content_from_nested_list,
    all_required_keys_have_values,
    concatenate_values,
)  # , is_duplicate_news_item
from src.config import SCHEMA_MAP
import utils.print_utils as prnt


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
            # provider="groq/gemma2-9b-it",
            provider="openai/gpt-4o-mini",
            api_token=os.getenv("OPENAI_API_KEY"),
        ),  # API token for authentication
        schema=NewsItem.model_json_schema(),  # JSON schema of the data model
        extraction_type="schema",  # Type of extraction to perform
        instruction=(
            "From the given html for a news page, extract the 'date', 'source', 'content' (verbatim text content of the main article), 'synoposis' (if any), and the 'url'."
        ),  # Instructions for the LLM
        input_format="html",  # Format of the input content
        verbose=True,  # Enable verbose logging
    )


def get_json_css_strategy(publication: str) -> JsonCssExtractionStrategy:
    if publication in SCHEMA_MAP:
        return JsonCssExtractionStrategy(SCHEMA_MAP[publication], verbose=True)

    prnt.prRed(f"\nDidn't find any json_css_schema for {publication}\n")
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
    source = article_details["source"]

    # Omitting India Today videos for now
    if (source == "India Today") and ("/video/" in url):
        source = "India Today Video"

    # extraction_type = "css"
    extraction_strategy = get_json_css_strategy(source)
    if not extraction_strategy:
        # Use AI extraction strategy instead
        # extraction_strategy = get_llm_strategy()
        # extraction_type = "llm"
        return []

    # Fetch page content with the extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            extraction_strategy=extraction_strategy,  # Strategy for data extraction
            session_id=session_id,  # Unique session ID for the crawl
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {url}: {result.error_message}")
        return []

    # Parse extracted content
    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        # prnt.prLightPurple(result)
        prnt.prRed(f"No news_items found on page {url}.")
        return []

    # Debugging: Print each news_item to understand its structure after parsing extracted content
    print(f"\nExtracted data:\n{json.dumps(extracted_data, indent=2)}")

    # Process news items
    news_items = []
    for _, news_item in enumerate(extracted_data):
        # print(f"\nProcessing news_item {i} in extracted data")

        news_item["title"] = article_details["title"]
        news_item["source"] = article_details["source"]
        news_item["url"] = url
        news_item["date_google_news"] = article_details["date"]

        if not has_all_required_keys(news_item, required_keys):
            continue  # Skip incomplete news_items

        prnt.prLightPurple("Successfully extracted data.")
        if "synopsis" not in news_item:
            prnt.prLightPurple("No synopsis, adding an empty string.")
            news_item["synopsis"] = ""

        if news_item["content"] and isinstance(news_item["content"], list):
            if "para_content" in news_item["content"][0]:
                # concatenate the elements of the list
                news_item["content"] = concatenate_values(news_item["content"])
                # print(news_item["content"])
            elif "content1" in news_item["content"][0]:
                news_item["content"] = get_content_from_nested_list(
                    news_item["content"]
                )
                # prnt.prLightPurple(json.dumps(news_item["content"], indent=2))
            else:
                prnt.prRed("Malformed content. Skipping.")
                continue

        if all_required_keys_have_values(news_item, required_keys):
            # Add news_item to the list
            news_items.append(news_item)
            break
        else:
            prnt.prRed("Some required key is null. Skipping this article.")

    return news_items
