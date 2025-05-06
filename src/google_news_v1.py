import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import utils.print_utils as prnt
import src.config as cfg
from src.my_classes import NewsSearch
from src.rag_query import test_questions_on_the_go

# from dotenv import load_dotenv, find_dotenv

# _ = load_dotenv(find_dotenv())

if __name__ == "__main__":
    news_search = NewsSearch(cfg.google_news_inputs)
    print(news_search)

    # 1. Fetch news in 2-week intervals for the specified date range
    news_articles = news_search.fetch_news_for_date_range()
    prnt.prYellow(f"\nTotal articles fetched: {len(news_articles)}")

    # 2. Remove duplicate news items, if any
    news_search.remove_duplicates()

    # 3. Scrape the news items' content
    asyncio.run(news_search.crawl_news_items())

    # 4. Embed the newly-parsed news items in the vector DB
    news_search.embed_in_vectordb()

    # 5. Extract fields of interest and save them in a CSV
    news_search.extract_fields_of_interest(filename="new_parsed_news_items.csv")

    # 6. Test questions on the go
    test_questions_on_the_go(news_search.collection_name)
