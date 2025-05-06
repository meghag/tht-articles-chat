import csv
import os
import json
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


def create_csv_with_headers(dirname: str, filename: str, headers: list = None):
    filepath = os.path.join(dirname, filename)

    if not headers:
        headers = [
            "date_scraped",
            "synopsis",
            "content",
            "date_serpapi",
            "title",
            "source",
            "url",
        ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
    print(f"Created CSV file '{filename}' with headers: {headers}")


def save_news_items_to_csv(news_items: list, filename: str, dirname: str):
    if not news_items:
        print("No news items to save.")
        return

    # Use field names from the NewsItem model
    fieldnames = NewsItem.model_fields.keys()

    filepath = os.path.join(dirname, filename)

    # create the dir if it doesn't exist
    create_dir_if_doesnt_exist(os.path.dirname(filepath))

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(news_items)
    print(f"Saved {len(news_items)} news items to '{filename}'.")


def append_news_item_to_csv(news_item: dict, dirname: str, filename: str):
    filepath = os.path.join(dirname, filename)

    # create the dir if it doesn't exist
    create_dir_if_doesnt_exist(os.path.dirname(filepath))

    columns = [
        "date_scraped",
        "synopsis",
        "content",
        "date_serpapi",
        "title",
        "source",
        "url",
    ]

    with open(filepath, mode="a+", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        # writer.writerow(news_item.values())
        row = [news_item[col] for col in columns]
        writer.writerow(row)

    print(f"Saved news item to '{filename}'.")


def save_to_json(
    results: list | dict,
    dirname: str = None,
    filename: str = None,
    filepath: str = None,
) -> None:
    # Save results to a JSON file
    if (not filepath) and (dirname and filename):
        filepath = os.path.join(dirname, filename)

    # create the dir if it doesn't exist
    create_dir_if_doesnt_exist(os.path.dirname(filepath))

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    prnt.prLightPurple(f"\nSaved {len(results)} articles to {filepath}\n")


def append_to_json(
    data,
    dirname: str = None,
    filename: str = None,
    filepath: str = None,
) -> None:
    # Load existing data if the file exists
    if (not filepath) and (dirname and filename):
        filepath = os.path.join(dirname, filename)

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    # Ensure data is a list of dicts
    if isinstance(data, list):
        existing_data.extend(data)
    else:
        existing_data.append(data)
        # raise ValueError("Data must be a dict or a list of dicts")

    # Keep only unique items
    existing_data = list(set(existing_data))

    # Write back to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

    print(f"Appended {len(data)} items to {filepath}")


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


def create_dir_if_doesnt_exist(dirpath: str):
    if not os.path.exists(dirpath):
        print(f"Directory '{dirpath}' doesn't exist. Creating it...", end=" ")
        os.makedirs(dirpath)
        print("Created.")
    else:
        print(f"Directory '{dirpath}' already exists.")


def load_json(filepath: str) -> list:
    data = []

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"{len(data)} loaded.")

    return data


def json_to_csv(json_file_path, csv_file_path):
    """
    Converts a JSON file to a CSV file.

    Args:
        json_file_path (str): The path to the JSON file.
        csv_file_path (str): The path to the output CSV file.
    """
    try:
        with open(json_file_path, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: JSON file not found at '{json_file_path}'")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{json_file_path}'")
        return

    if not isinstance(data, list):
        data = [data]

    if not data:
        print("Error: JSON data is empty")
        return

    try:
        with open(csv_file_path, "w", newline="") as file:
            csv_writer = csv.writer(file)

            header = data[0].keys()
            csv_writer.writerow(header)

            for item in data:
                csv_writer.writerow(item.values())
    except Exception as e:
        print(f"An error occurred during CSV writing: {e}")


if __name__ == "__main__":
    json_file_path = "/Users/megha-personal/Documents/THT/app/trial_results/leopards_scholarly_processed_results_trial.json"
    csv_file_path = "/Users/megha-personal/Documents/THT/app/trial_results/leopards_scholarly_processed_results_trial.csv"
    json_to_csv(json_file_path, csv_file_path)
