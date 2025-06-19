import sys
import os
import json
import random
import time
import requests
from serpapi import GoogleSearch
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup
from scidownl import scihub_download

# from scholarly import scholarly, ProxyGenerator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# import src.config as cfg
import utils.print_utils as pr
import utils.data_utils as dut
import utils.print_utils as prnt
import rag.maintain_vectordb as vdb
import re
import pandas as pd
import rag.fields_of_interest as foi
from src.extract_fields_of_interest import find_and_save_rag_answer

_ = load_dotenv(find_dotenv())

ROOT_DIR = "/content/drive/MyDrive/Work-related/THT/app"
curr_dir = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(curr_dir, "..", "results")


# # List of proxy servers (Replace with real working proxies)
# proxies = [
#     "http://username:password@proxy1.com:port",
#     "http://username:password@proxy2.com:port",
#     "http://username:password@proxy3.com:port"
# ]

# def get_random_proxy():
#     return {"http": random.choice(proxies), "https": random.choice(proxies)}

serp_api_key = os.getenv("SERPAPI_KEY")


class ScholarSearch:
    def __init__(self, inputs: dict) -> None:
        self.keyphrase = inputs["keyphrase"]
        # self.years = inputs["years"]
        self.start_year = inputs["start_year"]
        self.end_year = inputs["end_year"]
        self.results_dirname = os.path.join(
            RESULTS_DIR,
            inputs["dirname"],
            str(self.start_year) + "_" + str(self.end_year),
        )
        self.results_filename = "_".join(self.keyphrase.split()) + ".json"
        self.results_filepath = os.path.join(
            self.results_dirname, self.results_filename
        )
        self.mandatory_keywords = inputs["mandatory_keywords"]
        self.collection_name = inputs["vectordb_collection_name"]

        dut.create_dir_if_doesnt_exist(self.results_dirname)

        # create a file which logs the inputs
        if not os.path.exists(os.path.join(self.results_dirname, "config.json")):
            dut.save_to_json(
                results=inputs, dirname=self.results_dirname, filename="config.json"
            )
            dut.save_to_json(
                results=[], dirname=self.results_dirname, filename="new_downloads.json"
            )
            # dut.save_to_json(
            #     results=[], dirname=self.results_dirname, filename="failed_urls.json"
            # )

            # dut.create_csv_with_headers(
            #     dirname=self.results_dirname, filename="parsed_news_items.csv"
            # )
            dut.create_csv_with_headers(
                dirname=self.results_dirname,
                filename="embedded_sources.csv",
                headers=["Sources"],
            )

    def search_scholar_with_serpapi(self, pages_per_year: int):
        prnt.prPurple(
            f"\nSearching for articles from {self.start_year} to {self.end_year}\n"
        )
        all_results = []

        for year in range(self.start_year, self.end_year + 1):
            prnt.prPurple(f"Searching for articles in {year}...")
            results_for_this_year = []

            for page in range(pages_per_year):
                start = page * 10
                params = {
                    "engine": "google_scholar",
                    "q": self.keyphrase,
                    "hl": "en",
                    "as_ylo": year,
                    "as_yhi": year,
                    "start": start,
                    "api_key": serp_api_key,
                }

                # response = requests.get("https://serpapi.com/search", params=params)
                # data = response.json()
                try:
                    search = GoogleSearch(params)
                    data = search.get_dict()
                except Exception as e:
                    prnt.prRed(f"Exception while searching: {e}")
                    break

                results = data.get("organic_results", [])
                if not results:
                    break

                for res in results:
                    article = {
                        "title": (res.get("title", ""))
                        .strip()
                        .rstrip("."),  # remove the trailing period, if any
                        "url": res.get("link"),
                        "snippet": res.get("snippet"),
                        # "authors": res.get("publication_info", {}).get("authors"),
                        "summary": res.get("publication_info", {}).get("summary", ""),
                    }
                    (
                        article["authors_serpapi"],
                        article["publisher"],
                        article["year"],
                    ) = self.get_info_from_summary(article["summary"])
                    if not article["year"]:
                        # still some issue in extracting year
                        article["year"] = year
                    results_for_this_year.append(article)

            dut.save_to_json(
                results=results_for_this_year,
                dirname=os.path.join(self.results_dirname, "temp_files"),
                filename=f"{year}.json",
            )
            all_results.extend(results_for_this_year)

        # Save results to a JSON file
        print("Now saving results...")
        dut.save_to_json(results=all_results, filepath=self.results_filepath)

        # return all_results

    def get_info_from_summary(self, summary: str):
        authors, publisher, year = "", "", ""
        parts = summary.split(" - ")
        if len(parts) >= 3:
            authors = parts[0].strip()
            publisher = parts[-1].strip()
            # print(publisher)
            year_part = parts[-2].strip()
            match = re.search(r"\b(\d{4})\b", year_part)
            if match:
                year = match.group(1)
                # print(year)
        return authors, publisher, year

    def cleanup_scholar_results(self) -> list[dict]:
        """Preprocess the JSON to filter out results that do not fit the time period or the keyphrase"""
        pr.prPurple("\nCleaning up results based on year, keywords, and uniqueness\n")

        to_remove, unique_articles = [], []

        # first load all the articles found
        results = dut.load_json(
            os.path.join(self.results_dirname, self.results_filename)
        )
        pr.prLightPurple(f"Num articles before: {len(results)}")

        # then filter them based on year, keywords, and uniqueness
        for res in results:
            # first check if the publication year lies within the desired range
            year = int(res["year"]) if res["year"] else -1
            # print(year)
            if not ((year >= self.start_year) and (year <= self.end_year)):
                # print(f"Removing: ({year}) {res['title']}")
                to_remove.append(res)
                continue

            # then check if all the mandatory keywords are present in title or snippet
            for k in self.mandatory_keywords:
                if (k.lower() not in res["title"].lower()) and (
                    k.lower() not in res["snippet"].lower()
                ):
                    # print(f"Removing: {res['title']}")
                    to_remove.append(res)
                    break

            # check for duplicates by title and year
            if (res["title"], res["year"]) not in unique_articles:
                unique_articles.append((res["title"], res["year"]))
            else:
                to_remove.append(res)

        pr.prLightPurple(f"\nTo remove: {len(to_remove)}")

        # Save to_remove to a JSON file
        dut.save_to_json(
            results=to_remove,
            dirname=self.results_dirname,
            filename="removed_" + self.results_filename,
        )

        cleaned_results = [res for res in results if res not in to_remove]
        # new_results = list(set(results) - set(to_remove))
        pr.prLightPurple(f"Num articles after: {len(cleaned_results)}")

        # Save new_results to a JSON file
        dut.save_to_json(
            results=cleaned_results,
            dirname=self.results_dirname,
            filename="cleaned_" + self.results_filename,
        )

        # return cleaned_results

    def enrich_with_abstracts(self):
        pr.prPurple("\nGetting abstracts, if available, from Semantic Scholar\n")
        # enriched, unmatched = [], []
        processed = []
        num_found = 0

        # first load the cleaned up results
        articles = dut.load_json(
            os.path.join(self.results_dirname, "cleaned_" + self.results_filename)
        )
        pr.prLightPurple(f"\nNum of articles: {len(articles)}")

        for idx, article in enumerate(articles):
            title = article.get("title")
            if not title:
                processed.append(article)
                # unmatched.append(article)
                continue

            print(f"\n{idx + 1}: {title}")
            try:
                resp = requests.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": title,
                        "limit": 1,
                        "fields": "title,abstract,authors,year,venue,url",
                    },
                )
                data = resp.json().get("data", [])

                if (
                    data
                    and (
                        data[0].get("title", "").strip().rstrip(".").lower()
                        == title.lower()
                    )
                    and data[0].get("abstract")
                ):
                    best_match = data[0]
                    # pr.prLightPurple(
                    #     f"\nBest match:\n{json.dumps(best_match, indent=2)}"
                    # )
                    article["abstract"] = best_match.get("abstract")
                    article["publisher"] = best_match.get("venue")
                    article["semantic_scholar_url"] = best_match.get("url")
                    if not article["year"]:
                        article["year"] = best_match.get("year")
                    article["authors_semantic_scholar"] = best_match.get("authors")
                    # processed.append(article)
                    num_found += 1
                else:
                    print("Didn't find a match")
                # processed.append(article)
            except Exception as e:
                pr.prRed(f"Error: {e}")

            processed.append(article)

            time.sleep(1)  # Respect Semantic Scholar's API limits

        prnt.prYellow(
            f"Found abstracts for {num_found} out of {len(articles)} articles."
        )
        # Save results to a JSON file
        pr.prLightPurple("\nNow saving results...")
        dut.save_to_json(
            results=processed,
            dirname=self.results_dirname,
            filename="processed_" + self.results_filename,
        )

        # dut.save_to_json(
        #     results=unmatched,
        #     dirname=self.results_dirname,
        #     filename="results_wo_abstracts.json",
        # )

        # return enriched, unmatched

    def search_and_download_from_scihub(self):
        pr.prPurple("\nTrying to download from SciHub\n")

        articles = dut.load_json(
            os.path.join(self.results_dirname, "processed_" + self.results_filename)
        )
        pr.prLightPurple(f"\nFound a total of {len(articles)} articles.\n")

        # reset new downloads to empty
        dut.save_to_json(
            results=[], dirname=self.results_dirname, filename="new_downloads.json"
        )

        pdf_dir = os.path.join(self.results_dirname, "pdf")
        dut.create_dir_if_doesnt_exist(pdf_dir)
        pr.prLightPurple(
            f"\n{len(os.listdir(pdf_dir))} articles are already downloaded.\n"
        )

        articles_with_filepath = []
        for i, art in enumerate(articles):
            try:
                title = art["title"]
                if self.is_already_downloaded(title):
                    articles_with_filepath.append(art)
                    continue

                print(f"\n------\nTrying: {i}: {title}")
                scihub_download(
                    keyword=title,
                    paper_type="title",
                    out=os.path.join(ROOT_DIR, "pdf", title + ".pdf"),
                )

                # if the title got downloaded, save it in new_downloads.json
                if self.is_already_downloaded(title):
                    dut.append_to_json(
                        data=title + ".pdf",
                        dirname=self.results_dirname,
                        filename="new_downloads.json",
                    )
                    # add another field to the article details
                    art["filepath"] = os.path.join(pdf_dir, title + ".pdf")

                # else:
                # TODO: Try doi way too
            except Exception as e:
                print(f"Exception for idx {i}: {e}")

            articles_with_filepath.append(art)

        # save the updated articles
        dut.save_to_json(
            articles_with_filepath,
            dirname=self.results_dirname,
            filename="filepath_" + self.results_filename,
        )

        # scihub downloader changes colons to underscores in downloaded filenames as colons are not allowed in filenames on Windows. Revert them to colons.
        self.revert_to_original_filenames()

    def revert_to_original_filenames(self):
        # scihub downloader changes colons to underscores in downloaded filenames as colons are not allowed in filenames on Windows. Revert them to colons.
        pdf_dir = os.path.join(self.results_dirname, "pdf")
        for filename in os.listdir(pdf_dir):
            if filename.endswith(".pdf") and "_" in filename:
                new_filename = filename.replace("_", ":")
                src = os.path.join(pdf_dir, filename)
                dst = os.path.join(pdf_dir, new_filename)

                try:
                    os.rename(src, dst)
                    print(f"Renamed: {filename} → {new_filename}")
                except OSError as e:
                    prnt.prRed(f"Failed to rename {filename}: {e}")

    def is_already_downloaded(self, title: str) -> bool:
        pdf_dir = os.path.join(self.results_dirname, "pdf")
        already_downloaded = os.listdir(pdf_dir)
        if (title + ".pdf" in already_downloaded) or (
            title.replace(":", "_") in already_downloaded
        ):
            return True

        return False

    def embed_in_vectordb(self):
        print("Embedding in Vector DB")
        # pdf_dir = os.path.join(self.results_dirname, "pdf")
        # data = os.listdir(pdf_dir)

        articles = dut.load_json(
            os.path.join(self.results_dirname, "filepath_" + self.results_filename)
        )
        prnt.prYellow(f"Num articles loaded: {len(articles)}")

        for art in articles:
            try:
                addnl_metadata = {
                    "source_type": "scholar",
                    "title": art["title"],
                    "year": art.get("year"),
                    "authors": art.get("authors_serpapi"),
                    "publisher": art.get("publisher"),
                }
                if "filepath" in art:
                    # This article has been downloaded. Embed it.
                    if "abstract" in art:
                        addnl_metadata["abstract"] = art["abstract"]

                    vdb.add_update_docs(
                        data_to_add=[art["filepath"]],
                        collection_name=self.collection_name,  # "leopard_research_articles",
                        addnl_metadata=addnl_metadata,
                        dir_name=os.path.join(self.results_dirname, "pdf"),
                        update=False,
                    )
                elif "abstract" in art:
                    # This article wasn't downloaded but we have its abstract
                    addnl_metadata["abstract"] = art["abstract"]
                    vdb.add_update_docs(
                        data_to_add=[f"Abstract: {art['title']}"],
                        collection_name=self.collection_name,  # "leopard_research_articles",
                        addnl_metadata=addnl_metadata,
                        # dir_name=os.path.join(self.results_dirname, "pdf"),
                        update=False,
                    )
            except Exception as e:
                prnt.prRed(e)
                continue

    def extract_fields_of_interest(
        self,  # embed: bool = False
    ):
        """
        This assumes that the PDFs or abstracts are already embedded and directly tries to extract the fields of interest.
        """
        print("Extracting fields of interest")
        # if embed:
        #     self.embed_in_vectordb(filename)

        articles = dut.load_json(
            os.path.join(self.results_dirname, "filepath_" + self.results_filename)
        )
        embedded_sources_df = pd.read_csv(
            os.path.join(
                self.results_dirname,
                "embedded_sources.csv",
                # curr_dir, "..", "rag", self.collection_name + "_embedded_sources.csv"
            )
        )
        embedded_sources = set(embedded_sources_df["Sources"].to_list())

        # df = pd.read_csv(os.path.join(self.results_dirname, filename))
        print(f"Num articles: {len(articles)}\n")

        fields = foi.leopard_research_article_fields
        print(fields.keys())

        updated_articles = []
        for art in articles:
            if "location" not in art:
                # fields not extracted yet
                if (
                    art.get("filepath") and (art["title"] + ".pdf" in embedded_sources)
                ) or (
                    art.get("abstract")
                    and ("Abstract: " + art["title"] in embedded_sources)
                ):
                    # this PDF/abstract has been embedded
                    updated_art = find_and_save_rag_answer(
                        fields,
                        art,
                        collection_name=self.collection_name,
                        metadata_filters={"title": {"$eq": art["title"]}},
                    )
                    if "location" in updated_art:
                        updated_articles.append(updated_art)

        if len(updated_articles) > 0:
            # TODO: Append instead of overwrite
            # dut.save_to_json(
            dut.append_to_json(
                data=updated_articles,
                dirname=self.results_dirname,
                filename="fields_" + self.results_filename,
            )

            dut.json_to_csv(
                json_file_path=os.path.join(
                    self.results_dirname, "fields_" + self.results_filename
                ),
                csv_file_path=os.path.join(self.results_dirname, "with_fields.csv"),
            )
        else:
            print("Couldn't extract fields of interest for any article.")


"""
def search_scholar_with_scholarly(self) -> list[dict]:
        results = []
        search_query = scholarly.search_pubs(
            self.keyphrase, year_low=self.start_year, year_high=self.end_year
        )
        print(f"{'-' * 30}\n{search_query}\n{'-' * 30}")

        # while True:
        for i in range(100):  # Fetch top 5 results
            # Introduce a random delay between API calls to avoid detection
            time.sleep(random.uniform(3, 7))

            try:
                article = next(search_query)
                results.append(
                    {
                        "title": article.get("bib", {}).get("title"),
                        "author": article.get("bib", {}).get("author"),
                        "year": article.get("bib", {}).get("pub_year"),
                        "url": article.get("pub_url"),
                    }
                )
                print(f"Processed article {i}")

            except StopIteration:
                break

            except Exception as e:
                print(f"Error processing publication {i}: {e}")
                continue

        # Save results to a JSON file
        print("Now saving results...")
        dut.save_to_json(results=results, filepath=self.results_filepath)

        return results
"""
