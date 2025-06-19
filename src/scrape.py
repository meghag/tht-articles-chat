import sys
import os
import json
import random
import time
import requests
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup

# import utils.print_utils as prnt
import math
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import certifi


_ = load_dotenv(find_dotenv())

curr_dir = os.path.dirname(__file__)
print(curr_dir)
# ROOT_DIR = os.path.dirname(curr_dir)
# print(f"ROOT DIR: {ROOT_DIR}")

DEBUG = 0
# prnt.prYellow(f"DEBUG = {DEBUG}")
# List of proxy servers (Replace with real working proxies)
proxies = [
    "http://username:password@proxy1.com:port",
    "http://username:password@proxy2.com:port",
    "http://username:password@proxy3.com:port",
]

HEADER_CHOICES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]


def is_valid_pdf_url(url):
    return url.lower().endswith(".pdf")


def get_all_pdf_links(webpage_url):
    headers = {"User-Agent": random.choice(HEADER_CHOICES)}
    try:
        response = requests.get(webpage_url, headers=headers, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {webpage_url}: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    pdf_links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        full_url = urljoin(webpage_url, href)
        if is_valid_pdf_url(full_url):
            pdf_links.append(full_url)

    return pdf_links


# def get_all_pdf_links(webpage_url):
#     headers = {"User-Agent": random.choice(HEADER_CHOICES)}
#     try:
#         response = requests.get(webpage_url, headers=headers, verify=False)
#         response.raise_for_status()
#     except requests.exceptions.RequestException as e:
#         print(f"Error accessing {webpage_url}: {e}")
#         return []

#     soup = BeautifulSoup(response.content, "html.parser")
#     pdf_links = []

#     base_url_parts = urlparse(webpage_url)

#     for link in soup.find_all("a", href=True):
#         href = link["href"]
#         full_url = urljoin(webpage_url, href)
#         full_url_parts = urlparse(full_url)

#         # Check: same domain + same page (not navigating to another route or page)
#         if is_valid_pdf_url(full_url) and (
#             full_url_parts.netloc == base_url_parts.netloc
#             and full_url_parts.path.startswith(base_url_parts.path)
#         ):
#             pdf_links.append(full_url)

#     return pdf_links


def download_pdfs(pdf_urls, download_dir):
    headers = {"User-Agent": random.choice(HEADER_CHOICES)}
    os.makedirs(download_dir, exist_ok=True)

    for url in tqdm(pdf_urls[:3], desc="Downloading PDFs"):
        try:
            filename = os.path.basename(urlparse(url).path)
            filepath = os.path.join(download_dir, filename)
            response = requests.get(url, stream=True, headers=headers, verify=False)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

        except requests.exceptions.RequestException as e:
            print(f"Failed to download {url}: {e}")


def get_random_proxy():
    return {"http": random.choice(proxies), "https": random.choice(proxies)}


"""## Helper functions

### Scraping a website for relevant hyperlinks
"""


def scrape_and_extract(url: str, keywords: list[str]):
    try:
        # Send an HTTP GET request to the website with a randomized User-Agent to make the requests look more natural
        headers = {"User-Agent": random.choice(HEADER_CHOICES)}
        response = requests.get(url, headers=headers)  # , proxies=get_random_proxy()
        # )  # {"User-Agent": "Mozilla/5.0"})
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
                link_text.lower() in keywords
            ):  # or keyword.lower() in link["href"].lower():
                matching_links.append(link["href"])

        # Return extracted sections
        # return matching_links if matching_links else ["No relevant links found."]

        # Extract relevant buttons
        # matching_buttons = []
        for link in soup.find_all("button"):
            # print(f"\n\n{link}")
            link_text = link.get_text(strip=True)
            print(f"\n\n{link_text}")
            if link_text.lower() in keywords:
                matching_links.append(link)

        # Return extracted sections
        return matching_links if matching_links else ["No relevant links found."]

    except requests.exceptions.RequestException as e:
        return [f"Error fetching data: {e}"]


if __name__ == "__main__":
    # url = "https://journals.lww.com/coas/fulltext/2006/04030/is_relocation_a_viable_management_option_for.6.aspx"
    # print(scrape_and_extract(url, keywords=["pdf", "download"]))

    webpage_url = "https://example.com/page-with-pdfs"  # 🔁 Replace this
    download_dir = "downloaded_pdfs"

    pdf_links = get_all_pdf_links(webpage_url)
    print(f"Found {len(pdf_links)} PDFs")
    download_pdfs(pdf_links, download_dir)
