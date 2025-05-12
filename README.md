# Documentation

### Pipeline for Google News

1. In `config.py > google_news_inputs`, specify the keywords for your search as well as the start and end dates (as a combination of month and year, for example, `May 2020`). `dirname` is the name of the subdirectory of `results` where the search results and further processed results will be stored.

2. Run `src > google_news_v1.py`. This will perform the following actions step by step:
    - Fetch news in 2-week intervals for the specified date range from Google News, store them in a subfolder in {dirname} which will be named by the search dates. Search results for 2-week periods in the search period will be stored in 'temp_files' subdirectory inside this subfolder.
    - Remove duplicate news items, if any, and store them in a separate JSON in the same subfolder.
    - Scrape the news items' content using `Crawl4AI` to extract its content, date and synopsis. Note that it can only handle sources that are included in the `SCHEMA_MAP` in `config.py`. The results from this parsing are stored in `parsed_news_items.csv` in the same subfolder. The URLs that fail to be scraped and parsed are saved in `failed_urls.json` and the successfully-parsed ones in `parsed_urls.json`.
    - Embed the newly-parsed news items in the vector DB.
    - Extract fields of interest (like location, context, PA names, etc.) using Retrieval-Augmented Generation (RAG) and save them in a CSV.
    - Test questions on the go using another RAG pipeline on the same vector DB.



### Pipeline for Google Scholar

1. In `config.py > google_scholar_inputs`, specify the keywords for your search as well as the start and end year. `dirname` is the name of the subdirectory of `results` where the search results and further processed results will be stored.

2. Run `src > google_scholar_v1.py`. This will perform the following actions step by step:
    - Search for a keyphrase and extract results, one year at a time, from Google Scholar in a JSON in {dirname} which will be named by the search years. Search results for each year in the search period will be stored in 'temp_files' subdirectory inside this subfolder.
    - Clean up the search results based on year and title, remove duplicates if any, and store them in a separate JSON in the same subfolder.
    - Search for each title on Semantic Scholar and try getting the abstract. These processed results will be stored a s separate JSON.
    - Search for each title on Science Hub and try downloading it if it hasn't been downloaded already.
    - Embed the newly-downloaded articles in the vector DB.
    - Extract fields of interest (like location, context, PA names, etc.) using Retrieval-Augmented Generation (RAG) and save them in a CSV.
    - Test questions on the go using another RAG pipeline on the same vector DB.