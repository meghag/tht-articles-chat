import os
import sys
import json
from dotenv import load_dotenv, find_dotenv
from serpapi import GoogleSearch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


import utils.print_utils as prnt
import utils.data_utils as dut
from utils.scraper_utils import get_browser_config, get_json_css_strategy
import rag.maintain_vectordb as vdb
import rag.fields_of_interest as foi
from src.extract_fields_of_interest import find_and_save_rag_answer
import src.config as cfg

from datetime import datetime, timedelta
import collections
import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    # BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    # LLMExtractionStrategy,
    # LLMConfig,
    # JsonCssExtractionStrategy,
)

import pandas as pd
from dateutil import parser
import re


_ = load_dotenv(find_dotenv())

curr_dir = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(curr_dir, "..", "results")
# print(f"RESULTS DIR: {RESULTS_DIR}")

DEBUG = 0
prnt.prYellow(f"DEBUG = {DEBUG}")

serp_api_key = os.getenv("SERPAPI_KEY")


class NewsSearch:
    def __init__(self, inputs: dict) -> None:
        self.keyphrase = inputs["keyphrase"]
        self.start_month_year = inputs["start_month_year"]
        self.end_month_year = inputs["end_month_year"]
        # self.overall_period = f"{str(self.start_date).replace('/', '-')}_{str(self.end_date).replace('/', '-')}"
        self.overall_period = f"{(self.start_month_year).replace(' ', '')}_{(self.end_month_year).replace(' ', '')}"
        self.results_dirname = os.path.join(
            RESULTS_DIR, inputs["dirname"], self.overall_period
        )
        self.results_filename = "serp_results.json"
        # f"{self.overall_period}.json"
        self.results_filepath = os.path.join(
            self.results_dirname, self.results_filename
        )
        # TODO: make it a class attribute?
        self.required_keys = cfg.google_news_inputs["required_keys"]
        self.collection_name = inputs["vectordb_collection_name"]

        dut.create_dir_if_doesnt_exist(self.results_dirname)

        # create a file which logs the inputs
        if not os.path.exists(os.path.join(self.results_dirname, "config.json")):
            dut.save_to_json(
                results=inputs, dirname=self.results_dirname, filename="config.json"
            )
            dut.save_to_json(
                results=[], dirname=self.results_dirname, filename="parsed_urls.json"
            )
            dut.save_to_json(
                results=[], dirname=self.results_dirname, filename="failed_urls.json"
            )

            dut.create_csv_with_headers(
                dirname=self.results_dirname, filename="parsed_news_items.csv"
            )
            dut.create_csv_with_headers(
                dirname=self.results_dirname,
                filename="embedded_sources.csv",
                headers=["Sources"],
            )

    def fetch_news_using_serpapi(self, period_start, period_end) -> list:
        """
        Fetches one page at a time until all pages have been exhausted.
        """
        prnt.prPurple(f"Fetching news from {period_start} to {period_end}...")

        all_results = []

        params = {
            "q": self.keyphrase,
            "tbm": "nws",
            "location": "India",
            "hl": "en",
            "tbs": f"cdr:1,cd_min:{period_start},cd_max:{period_end}",
            # "num": 10,  # Fetching smaller batches
            "api_key": serp_api_key,
        }

        # TODO: To remove page number restriction, comment out lines 110 and 111, and uncomment lines 112 and 113. Take care of the indentation.
        pages = 1  # num of pages to fetch
        for offset in range(0, pages * 10, 10):  # Adjust pagination step if needed
            # offset = 0
            # while True:
            # for _ in range(2):
            params["start"] = offset
            results = {}

            # response = requests.get("https://serpapi.com/search", params=params)
            # data = response.json()
            try:
                prnt.prLightPurple(
                    f"\nStarting search for {period_start} to {period_end} with offset {offset}..."
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

    def get_start_end_dates(self, year, month, period: str):
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

    from datetime import datetime, timedelta

    def get_start_date(self, month_year_str):
        """Return the start date of the month in MM/DD/YYYY format."""
        date_obj = datetime.strptime(month_year_str, "%b %Y")
        date_str = date_obj.strftime("%m/%d/%Y")
        return datetime.strptime(date_str, "%m/%d/%Y")

    def get_end_date(self, month_year_str):
        """Return the last date of the month in MM/DD/YYYY format."""
        date_obj = datetime.strptime(month_year_str, "%b %Y")
        # Go to first of next month, then subtract 1 day
        next_month = date_obj.replace(day=28) + timedelta(days=4)
        last_day = next_month.replace(day=1) - timedelta(days=1)
        date_str = last_day.strftime("%m/%d/%Y")
        return datetime.strptime(date_str, "%m/%d/%Y")

    def fetch_news_for_date_range(self):
        """
        Assumes the date_range is at least one month long, and that start date is always the beginning of some month and end date is always the end of some month.
        """
        # First check if the results already exist
        if os.path.exists(self.results_filepath):
            with open(self.results_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if len(data) > 0:
                    print("Results already exist for this topic and date range.")
                    return data

        start_date = self.get_start_date(self.start_month_year)
        end_date = self.get_end_date(self.end_month_year)
        prnt.prYellow(f"\nStart date: {start_date}, end_date: {end_date}\n")

        current_date = start_date

        all_articles = []
        while current_date <= end_date:
            month, year = current_date.month, current_date.year

            # Define two periods per month
            for half in ["first-half", "second-half"]:
                period_start, period_end = self.get_start_end_dates(
                    year, month, period=half
                )
                period = f"{str(period_start).replace('/', '-')}_{str(period_end).replace('/', '-')}"
                articles = self.fetch_news_using_serpapi(period_start, period_end)
                all_articles.extend(articles)
                dut.save_to_json(
                    results=articles,
                    dirname=os.path.join(self.results_dirname, "temp_files"),
                    filename=f"{period}.json",
                )

            # Move to next month
            current_date = datetime(year, month, 28) + timedelta(
                days=4
            )  # Ensures we reach the next month
            current_date = current_date.replace(day=1)

        dut.save_to_json(
            results=all_articles,
            filepath=self.results_filepath,
        )
        return all_articles

    def remove_duplicates(self):
        prnt.prPurple("\nRemoving duplicates.")
        data = None

        with open(self.results_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            prnt.prLightPurple(f"Initial number of URLs: {len(data)}")
            if data:
                print(f"\nSample URL:\n{json.dumps(data[0], indent=2)}")

        no_dups_data = []
        no_dups_urls = []
        for item in data:
            if item["link"] not in no_dups_urls:
                item.pop("position", None)
                item.pop("thumbnail", None)
                no_dups_data.append(item)
                no_dups_urls.append(item["link"])

        prnt.prLightPurple(f"\nFinal number of URLs: {len(no_dups_data)}")
        dut.save_to_json(
            results=no_dups_data,
            dirname=self.results_dirname,
            filename=f"{self.results_filename.split('.')[0]}_no_dups.json",
        )

        # TODO: If any of the top 20 sources aren't in SCHEMA_MAP, save them in a list to be included later.
        all_sources = [item["source"] for item in no_dups_data]
        top_20_sources = collections.Counter(all_sources).most_common()[:20]
        prnt.prLightPurple("\nTop 20 sources:\n")
        for s in top_20_sources:
            prnt.prLightPurple(f"{s[0]}: {s[1]}")

    def has_all_required_keys(self, news_item: dict, required_keys: list) -> bool:
        return all(key in news_item for key in required_keys)

    def all_required_keys_have_values(
        self, news_item: dict, required_keys: list
    ) -> bool:
        for key in required_keys:
            if not news_item[key]:
                return False

        return True

    async def crawl_news_items(self, source_to_parse: str = "all"):
        """
        Main function to crawl news data from the news website.
        """
        # Initialize configurations
        browser_config = get_browser_config()
        session_id = "news_items_crawl_session"

        # Load data
        data = None
        no_dups_filename = f"{self.results_filename.split('.')[0]}_no_dups.json"
        no_dups_filepath = os.path.join(self.results_dirname, no_dups_filename)
        with open(no_dups_filepath, "r", encoding="utf-8") as f1:
            data = json.load(f1)
            print(f"Number of URLs to parse: {len(data)}")
            # print(json.dumps(data[0], indent=2))

        parsed_urls = []
        with open(
            os.path.join(self.results_dirname, "parsed_urls.json"),
            "r",
            encoding="utf-8",
        ) as f2:
            parsed_urls = json.load(f2)
            print(f"\nNumber of parsed URLs: {len(parsed_urls)}")
            # print(parsed_urls)

        failed_urls = []
        with open(
            os.path.join(self.results_dirname, "failed_urls.json"),
            "r",
            encoding="utf-8",
        ) as f3:
            failed_urls = json.load(f3)
            print(f"\nNumber of failed URLs: {len(failed_urls)}")

        # Initialize state variables
        article_number = 1
        num_parsed_items = 0
        all_news_items = []

        if source_to_parse != "all":
            data = [d for d in data if d["source"] == source_to_parse]

        # Start the web crawler context
        # https://docs.crawl4ai.com/api/async-webcrawler/#asyncwebcrawler

        async with AsyncWebCrawler(config=browser_config) as crawler:
            for item in data:
                # TODO: remove for actual run
                if num_parsed_items == 3:
                    break

                print(f"\n----{article_number}------")  # \n{item}\n")
                url = item["link"]
                if url in parsed_urls:
                    prnt.prLightPurple("Item already parsed. Skipping it.")
                    article_number += 1  # Move to the next article
                    continue

                # Fetch and process data from the current page
                news_items = await self.fetch_and_process_page(
                    crawler, item, session_id
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
                    dut.append_to_json(
                        data=url,
                        dirname=self.results_dirname,
                        filename="parsed_urls.json",
                    )

                    for news_item in news_items:
                        dut.append_news_item_to_csv(
                            news_item,
                            self.results_dirname,
                            "parsed_news_items.csv",
                        )

                    num_parsed_items += 1
                # break
                article_number += 1  # Move to the next article

                # Pause between requests to be polite and avoid rate limits
                await asyncio.sleep(2)  # Adjust sleep time as needed

        dut.save_to_json(
            results=list(set(failed_urls)),
            dirname=self.results_dirname,
            filename="failed_urls.json",
        )
        # dut.save_to_json(
        #     results=list(set(parsed_urls)),
        #     dirname=self.results_dirname,
        #     filename="parsed_urls.json",
        # )
        if all_news_items:
            dut.save_news_items_to_csv(
                news_items=all_news_items,
                filename="new_parsed_news_items.csv",
                dirname=self.results_dirname,
            )

    async def fetch_and_process_page(
        self,
        crawler: AsyncWebCrawler,
        article_details: dict,
        # llm_strategy: LLMExtractionStrategy,
        # json_css_strategy: JsonCssExtractionStrategy,
        session_id: str,
    ) -> list[dict]:
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
            news_item["date_serpapi"] = article_details["date"]
            if "ago" in news_item["date_serpapi"]:
                formatted_date = self.extract_and_format_date(news_item["date_scraped"])
                if formatted_date:
                    news_item["date_serpapi"] = formatted_date

            if not self.has_all_required_keys(news_item, self.required_keys):
                continue  # Skip incomplete news_items

            prnt.prLightPurple("Successfully extracted data.")
            if "synopsis" not in news_item:
                prnt.prLightPurple("No synopsis, adding an empty string.")
                news_item["synopsis"] = ""

            if news_item["content"] and isinstance(news_item["content"], list):
                if "para_content" in news_item["content"][0]:
                    # concatenate the elements of the list
                    news_item["content"] = dut.concatenate_values(news_item["content"])
                    # print(news_item["content"])
                elif "content1" in news_item["content"][0]:
                    news_item["content"] = dut.get_content_from_nested_list(
                        news_item["content"]
                    )
                    # prnt.prLightPurple(json.dumps(news_item["content"], indent=2))
                else:
                    prnt.prRed("Malformed content. Skipping.")
                    continue

            if self.all_required_keys_have_values(news_item, self.required_keys):
                # Add news_item to the list
                news_items.append(news_item)
                break
            else:
                prnt.prRed("Some required key is null. Skipping this article.")

        return news_items

    def extract_and_format_date(self, text: str) -> str:
        try:
            # Try to parse any date found in the text
            date = parser.parse(text, fuzzy=True)
            return date.strftime("%b %d, %Y")
        except ValueError:
            print(
                f"Value Error while extracting date from {text}. Trying the regex approach now."
            )

        try:
            regex1 = r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}"
            regex2 = r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*,?\s+\d{4}"
            match = re.search(regex1, text) or re.search(regex2, text)
            if match:
                date = parser.parse(match.group(0))
                return date.strftime("%b %d, %Y")
        except Exception as e:
            print(f"Exception while extracting date from {text}: {e}")

        return None

    def embed_in_vectordb(self, filename: str = "new_parsed_news_items.csv"):
        vdb.add_update_docs(
            data_to_add=[filename],
            collection_name=self.collection_name,  # "leopard_news",
            addnl_metadata={
                "source_type": "google_news",
            },
            dir_name=self.results_dirname,
            update=False,
        )

    def extract_fields_of_interest(
        self,
        filename: str,
        embed: bool = False,
    ):
        """
        If 'embed' is True, this method will try embedding the rows of the file in the vector db, and then extract fields of interest.
        If it's False, this will assume that the rows of the file are already embedded and directly try to extract the fields of interest.
        """
        if embed:
            self.embed_in_vectordb(filename)

        df = pd.read_csv(os.path.join(self.results_dirname, filename))
        print(f"Num news items: {len(df)}\n")

        fields = foi.leopard_news_item_fields
        print(fields.keys())

        processed_news_items = []
        for index, row in df.iterrows():
            news_item = row.to_dict()

            if "location" not in row:
                updated_news_item = find_and_save_rag_answer(
                    fields,
                    news_item,
                    collection_name=self.collection_name,
                    metadata_filters={"source": {"$eq": news_item["url"]}},
                )
                if "location" in updated_news_item:
                    processed_news_items.append(updated_news_item)

        # TODO: Append instead of overwrite
        dut.save_to_json(
            results=processed_news_items,
            dirname=self.results_dirname,
            filename="processed_news_items.json",
        )

        dut.json_to_csv(
            json_file_path=os.path.join(
                self.results_dirname, "processed_news_items.json"
            ),
            csv_file_path=os.path.join(
                self.results_dirname, "processed_news_items.csv"
            ),
        )


"""
# def search_google_news_with_serpapi(self, offset: int = 0):
    #     params = {
    #         # "engine": "google_news",
    #         "q": self.keyphrase,
    #         "tbm": "nws",  # to search only Google News
    #         "location": "India",
    #         "hl": "en",  # define the language of the results
    #         "tbs": f"cdr:1,cd_min:{self.start_date},cd_max:{self.end_date},sbd:1",  # custom date range, language, and sorted by date # lr=lang_en
    #         "start": offset,  # the number of results to skip in the beginning
    #         "num": 100,  # max number of results to return, may not work correctly
    #         "api_key": os.getenv("SERPAPI_KEY"),
    #     }

    #     search = GoogleSearch(params)
    #     results = search.get_dict()
    #     news_results = []
    #     if results["search_information"].get("total_results"):
    #         print(f"Found {results['search_information']['total_results']} results.")
    #         news_results = results["news_results"]
    #     else:
    #         prnt.prRed("Some error occured. Didn't get results.")
    #         return news_results

    #     # Save results to a JSON file
    #     dut.save_to_json(results=news_results, filepath=self.results_filepath)

    #     return news_results
"""
