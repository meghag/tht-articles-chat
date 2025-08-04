# Documentation

### How to install and run

1. Clone the repository from Github using `git clone` on your local.

2. This project uses Python 3.11. If you don't have it already, install it and use a Python environment manager like `pyenv` to use the correct version of Python inside this cloned directory.

3. Inside the root directory, i.e. `app`, create a Python virtual environment (using Python 3.11) and activate it.

4. Install the required packages using `pip install -r requirements.txt`. Make sure your virtual environment is activated before doing this.

5. Create a file called `.env` inside the `app` directory. Inside this, add your API keys as shown in `env_sample.txt`. NEVER commit and push your .env file to remote.

6. Use the command below in your terminal to run the app locally:
`streamlit run streamlit_app.py`

### Build a Collection to Chat With

There are two broad ways to build a chatbot using a set of documents that you can chat with.

1. Provide a topic and time range to search news and research articles on. Clicking on the `Build Q&A Chatbot` button in this case  will perform the following actions step by step:
    - A subdirectory, named by the topic and search dates, will be created inside the `results` directory. Further, this subdirectory will have `news` and `scholar` as its subdirectories.
    - For news articles:
        - Fetch news in 2-week intervals for the specified date range from Google News, store them in the corresponding `news` directory. Search results for 2-week periods in the search period will be stored in `temp_files` subdirectory inside the `news` subdirectory.
        - Remove duplicate news items, if any, and store them in a separate JSON in the same subfolder.
        - Scrape the news items' content using `Crawl4AI` to extract its content, date and synopsis. Note that it can only handle sources that are included in the `SCHEMA_MAP` in `config.py`. The results from this parsing are stored in `parsed_news_items.csv` in the same subfolder. The URLs that fail to be scraped and parsed are saved in `failed_urls.json` and the successfully-parsed ones in `parsed_urls.json`.
        - Embed the newly-parsed news items in the vector DB.
        - Extract fields of interest (like location, context, PA names, etc.) using Retrieval-Augmented Generation (RAG) and save them in a CSV.
    - For reserch articles:
        - Search for a topic and extract results, one year at a time, from Google Scholar in a JSON file. Search results for each year in the search period will be stored in `temp_files` subdirectory inside the corresponding `scholar` subfolder.
        - Clean up the search results based on year and title, remove duplicates if any, and store them in a separate JSON in the same subfolder.
        - Search for each title on Semantic Scholar and try getting the abstract. These processed results will be stored a s separate JSON.
        - Search for each title on Science Hub and try downloading it if it hasn't been downloaded already.
        - Embed the newly-downloaded articles in the vector DB.
        - Extract fields of interest (like location, context, PA names, etc.) using Retrieval-Augmented Generation (RAG) and save them in a CSV.


2. Provide a data source (path to a local folder, Google Drive link, or web URL) to extract documents from
    - Downloads all the documents available at the link locally, then embeds them into a new collection of the vector db, then deletes the local files.

In both cases, once the pipeline finishes successfully, you can start asking questions on the go using another RAG pipeline on the same vector DB.
