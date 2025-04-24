# Documentation

### Pipeline for Google News

1. In `config.py > google_news_inputs`, specify the keywords for your search as well as the start and end dates (typically starting of a month and end of the same or different month). `dirname` is the name of the subdirectory of `results` where the search results and further processed results will be stored.

2. First run `src > google_news.py`. This will fetch the relevant results from Google News, store them in a subfolder in {dirname} which will be named by the search dates. It will also remove any duplicate results and store them in a separate JSON in the same subfolder. Search results for 2-week periods in the search period will be stored in 'temp_files' subdirectory inside this subfolder.

3. Then run `src > crawl.py`. This script will load the correct JSON based on the `google_news_inputs` parameters in `config.py`, and then scrape each article's URL to extract its content, date and synopsis. Note that it can only handle sources that are included in the `SCHEMA_MAP` in `config.py`. The results from this parsing are stored in `parsed_news_items.csv` in the same subfolder. The URLs that fail to be scraped and parsed are saved in `failed_urls.json` and the successfully-parsed ones in `parsed_urls.json`.

