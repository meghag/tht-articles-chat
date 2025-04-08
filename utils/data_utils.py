import csv
import os
import json

from models.news_item import NewsItem

curr_dir = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(curr_dir)


def is_duplicate_news_item(news_item_name: str, seen_names: set) -> bool:
    return news_item_name in seen_names


def is_complete_news_item(news_item: dict, required_keys: list) -> bool:
    return all(key in news_item for key in required_keys)


def save_news_items_to_csv(news_items: list, filename: str):
    if not news_items:
        print("No news items to save.")
        return

    # Use field names from the NewsItem model
    fieldnames = NewsItem.model_fields.keys()

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(news_items)
    print(f"Saved {len(news_items)} news items to '{filename}'.")


def save_to_json(filename: str, results: list):
    # Save results to a JSON file
    with open(
        os.path.join(ROOT_DIR, "json", filename),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(results, f, indent=4)

    print(f"Saved {len(results)} articles to {filename}")
