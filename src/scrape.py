import sys
import os
import json
import random
import time
import requests
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup
import utils.print_utils as prnt
import math
from datetime import datetime, timedelta
import os
import requests

_ = load_dotenv(find_dotenv())

curr_dir = os.path.dirname(__file__)
print(curr_dir)
ROOT_DIR = os.path.dirname(curr_dir)
print(f"ROOT DIR: {ROOT_DIR}")

DEBUG = 0
prnt.prYellow(f"DEBUG = {DEBUG}")
# List of proxy servers (Replace with real working proxies)
proxies = [
    "http://username:password@proxy1.com:port",
    "http://username:password@proxy2.com:port",
    "http://username:password@proxy3.com:port",
]


def get_random_proxy():
    return {"http": random.choice(proxies), "https": random.choice(proxies)}


"""## Helper functions

### Scraping a website for relevant hyperlinks
"""


def scrape_and_extract(url, keyword):
    try:
        # Send an HTTP GET request to the website with a randomized User-Agent to make the requests look more natural
        headers = {
            "User-Agent": random.choice(
                [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                ]
            )
        }
        response = requests.get(
            url, headers=headers, proxies=get_random_proxy()
        )  # {"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()  # Raise an error for unsuccessful requests

        # Introduce a random delay to mimic human behavior
        time.sleep(random.uniform(5, 10))

        # Parse the webpage content using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        # print(soup)
        print("-" * 30)

        # Extract relevant hyperlinks
        matching_links = []
        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True)
            if (
                keyword.lower() in link_text.lower()
                or keyword.lower() in link["href"].lower()
            ):
                matching_links.append(link["href"])

        # Return extracted sections
        return matching_links if matching_links else ["No relevant links found."]

    except requests.exceptions.RequestException as e:
        return [f"Error fetching data: {e}"]
