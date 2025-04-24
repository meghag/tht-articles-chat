import csv
import os
import json
import collections
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


from models.news_item import NewsItem
import utils.print_utils as prnt

curr_dir = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(curr_dir)


def is_duplicate_news_item(news_item_name: str, seen_names: set) -> bool:
    return news_item_name in seen_names


def has_all_required_keys(news_item: dict, required_keys: list) -> bool:
    return all(key in news_item for key in required_keys)


def all_required_keys_have_values(news_item: dict, required_keys: list) -> bool:
    for key in required_keys:
        if not news_item[key]:
            return False

    return True


def save_news_items_to_csv(news_items: list, filename: str, dirname: str):
    if not news_items:
        print("No news items to save.")
        return

    # Use field names from the NewsItem model
    fieldnames = NewsItem.model_fields.keys()

    filepath = os.path.join(dirname, filename)

    # create the dir if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(news_items)
    print(f"Saved {len(news_items)} news items to '{filename}'.")


def save_single_news_item_to_csv(dirname, news_item: dict, filename: str):
    filepath = os.path.join(dirname, filename)

    # create the dir if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, mode="a+", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        # writer.writerow(news_item.values())
        writer.writerow(
            [
                news_item["date"],
                news_item["synopsis"],
                news_item["content"],
                news_item["date_google_news"],
                news_item["title"],
                news_item["source"],
                news_item["url"],
            ]
        )

    print(f"Saved news item to '{filename}'.")


def save_to_json(dirname: str, filename: str, results: list) -> None:
    # Save results to a JSON file
    filepath = os.path.join(dirname, filename)

    # create the dir if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    prnt.prLightPurple(f"\nSaved {len(results)} articles to {dirname}/{filename}\n")


def remove_duplicates(dirname: str, filename: str):
    prnt.prPurple("\nRemoving duplicates.")
    data = None

    with open(os.path.join(dirname, filename), "r", encoding="utf-8") as f:
        data = json.load(f)
        prnt.prLightPurple(f"Initial number of URLs: {len(data)}")
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
    save_to_json(
        dirname=dirname,
        filename=f"{filename.split('.')[0]}_no_dups.json",
        results=no_dups_data,
    )

    all_sources = [item["source"] for item in no_dups_data]
    prnt.prLightPurple(
        f"\nTop 20 sources:\n{json.dumps(collections.Counter(all_sources).most_common()[:20], indent=2)}"
    )


def concatenate_values(flat_list: list[dict]) -> str:
    content_list = [
        list(i.values())[0] for i in flat_list if (i and list(i.values())[0])
    ]
    return " ".join(content_list)


def get_content_from_nested_list(nested_content: list) -> str:
    # prnt.prPurple(f"\n{json.dumps(nested_content, indent=2)}\n")

    flat_list = []
    for d in nested_content:  # d is a dict
        flat_list.extend(list(d.values())[0])

    # prnt.prLightPurple(f"Flat list:\n{json.dumps(flat_list, indent=2)}")

    # return " ".join([p["para_content"] for p in flat_list if p])
    return concatenate_values(flat_list)


if __name__ == "__main__":
    # filename = "leopard_news_01-01-2025_03-31-2025.json"
    parsed_urls = ["url1", "url2", "url3"]
    filename = "parsed_urls.json"
    save_to_json(dirname=ROOT_DIR, filename=filename, results=parsed_urls)
    # remove_duplicate_urls(filename)
