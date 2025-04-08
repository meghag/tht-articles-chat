import csv
import os
import json
import collections
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


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

    filepath = os.path.join(ROOT_DIR, "csv", filename)

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
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


def remove_duplicate_urls(filename: str):
    data = None

    with open(
        os.path.join(ROOT_DIR, "json", filename),
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)
        print(f"Initial number of URLs: {len(data)}")
        print(json.dumps(data[0], indent=2))

    no_dups_data = []
    no_dups_urls = []
    for item in data:
        if item["link"] not in no_dups_urls:
            item.pop("position", None)
            item.pop("thumbnail", None)
            no_dups_data.append(item)
            no_dups_urls.append(item["link"])

    print(f"Final number of URLs: {len(no_dups_data)}")
    save_to_json(filename=f"no_dups/{filename}", results=no_dups_data)

    all_sources = [item["source"] for item in no_dups_data]
    print(collections.Counter(all_sources).most_common()[:20])


if __name__ == "__main__":
    # filename = "leopard_news_01-01-2025_03-31-2025.json"
    parsed_urls = ["url1", "url2", "url3"]
    filename = "parsed_urls.json"
    save_to_json(filename=filename, results=parsed_urls)
    # remove_duplicate_urls(filename)
