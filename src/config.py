# config.py
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv

_ = load_dotenv()

curr_dir = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(curr_dir, "..", "results")
RAG_DIR = os.path.join(curr_dir, "..", "rag")

google_news_inputs = {
    "keyphrase": "leopard india",
    "dirname": "leopard_news",
    "start_month_year": "Nov 2024",  # 'MMM YYYYY'
    "end_month_year": "Nov 2024",  # 'MMM YYYYY'
    "vectordb_collection_name": "leopard_news",
    "required_keys": [  # keys that must be present after a news item is parsed
        "title",
        "date_scraped",
        "source",
        "content",
        # "synopsis",
        "url",
    ],
}

google_scholar_inputs = {
    "keyphrase": "leopards in india",
    "dirname": "leopard_scholar",
    # "years": 5,
    "mandatory_keywords": [
        "leopard",
        "india",
    ],  # specify the keywords that MUST be present in the title
    # "current_year": 2025,
    "start_year": 2020,
    "end_year": 2022,
    "vectordb_collection_name": "leopard_research_articles",
}

LLM_PROVIDER = "openai"  # change this value to use a different LLM provider
LLM_MODEL = "gpt-4o-mini"  # change this value to use a different LLM model

EMBEDDINGS_PROVIDER = "openai"
EMBEDDINGS_MODEL = "text-embedding-3-small"

PROVIDERS = {
    "openai": {
        # "url": "https://api.openai.com/v1/chat/completions",
        # "response_url": "https://api.openai.com/v1/responses",
        # "key": "OPENAI_API_KEY",
        "llm_models": ["gpt-4o-mini", "gpt-4o"],
        # "default_temperature": 0.7,
        "langchain_llm": ChatOpenAI(
            temperature=0, model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")
        ),
        "langchain_embeddings": OpenAIEmbeddings(
            model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
        ),
    }
}

SCHEMA_MAP = {
    "Times of India": {
        "name": "Article",
        "baseSelector": "div.okf2Z",
        "fields": [
            # {"name": "author", "selector": "div.xf8Pm a", "type": "text"},
            {"name": "date_scraped", "selector": "div.xf8Pm span", "type": "text"},
            {"name": "synopsis", "selector": "div.art_synopsis", "type": "text"},
            {"name": "content", "selector": "div.js_tbl_article", "type": "text"},
        ],
    },
    "The Indian Express": {
        "name": "Article",
        "baseSelector": "div.native_story",
        "fields": [
            # {"name": "author", "selector": "div.editor a", "type": "text"},
            {"name": "date_scraped", "selector": "div.editor span", "type": "text"},
            {"name": "synopsis", "selector": "h2.synopsis", "type": "text"},
            {"name": "content", "selector": "div.story_details", "type": "text"},
        ],
    },
    "Deccan Herald": {
        "name": "Article",
        "baseSelector": "div.story-section",
        "fields": [
            {"name": "date_scraped", "selector": "div.ITNYL", "type": "text"},
            {"name": "synopsis", "selector": "div.sub-headline", "type": "text"},
            {
                "name": "content",
                "selector": "div#text-element-with-ad",
                "type": "nested_list",
                "fields": [
                    {
                        "name": "content1",
                        "selector": "div > div > div.story-element-text > p",
                        "type": "list",
                        "fields": [{"name": "para_content", "type": "text"}],
                    }
                ],
            },
        ],
    },
    "India Today Video": {  # if "/video/" in url
        "name": "Article",
        "baseSelector": "div.videodetails",
        "fields": [
            # {"name": "author", "selector": "div.editor a", "type": "text"},
            {"name": "date_scraped", "selector": "span.strydate", "type": "text"},
            {
                "name": "synopsis",
                "selector": "div.description div.text-formatted p",  # TODO: have used the same selector as content
                "type": "text",
            },
            {
                "name": "content",
                "selector": "div.description div.text-formatted",
                "type": "text",
            },
        ],
    },
    "India Today": {  # if "/video/" not in url
        "name": "Article",
        "baseSelector": "div.story__content__body",
        "fields": [
            # {"name": "author", "selector": "div.editor a", "type": "text"},
            {"name": "date_scraped", "selector": "span.strydate", "type": "text"},
            {
                "name": "synopsis",
                "selector": "div.story-kicker h2",
                "type": "text",
            },
            {
                "name": "content",
                "selector": "div.story-with-main-sec div.description > p",
                "type": "list",
                "fields": [{"name": "para_content", "type": "text"}],
            },
        ],
    },
    "Hindustan Times": {
        "name": "Article",
        "baseSelector": "div.fullStory",
        "fields": [
            # {"name": "author", "selector": "small.byLineAuthor a", "type": "text"},
            {"name": "date_scraped", "selector": "div.dateTime", "type": "text"},
            {"name": "synopsis", "selector": "h2.sortDec", "type": "text"},
            {"name": "content", "selector": "div.detail", "type": "text"},
        ],
    },
    "NDTV": {
        "name": "Article",
        "baseSelector": "div.sp-hd",
        "fields": [
            # {"name": "author", "selector": "nav.pst-by a.pst-by_lnk", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "nav.pst-by span.pst-by_lnk",
                "type": "text",
            },
            {"name": "synopsis", "selector": "h2.sp-descp", "type": "text"},
            {"name": "content", "selector": "div.Art-exp_wr", "type": "text"},
        ],
    },
    "News18": {
        "name": "Article",
        "baseSelector": "article.articlecontent",
        "fields": [
            # {"name": "author", "selector": "div.rptby ul.rptblist a.cp_author_byline", "type": "text"},
            {"name": "date_scraped", "selector": "div.ltu time", "type": "text"},
            {"name": "synopsis", "selector": "h2.asubttl-schema", "type": "text"},
            {
                "name": "content",
                "selector": "article.articlecontent > p",
                "type": "list",
                "fields": [{"name": "para_content", "type": "text"}],
            },
        ],
    },
    "The Tribune": {
        "name": "Article",
        "baseSelector": "div.article-main",
        "fields": [
            # {"name": "author", "selector": "div.writter_name", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "div.timesTamp > span:not(.location)",
                "type": "text",
            },
            {"name": "synopsis", "selector": "div.excerpt", "type": "text"},
            {
                "name": "content",
                "selector": "div#story-detail > p",
                "type": "list",
                "fields": [{"name": "para_content", "type": "text"}],
            },
        ],
    },
    "The Hindu": {
        "name": "Article",
        "baseSelector": "div.storyline",
        "fields": [
            # {"name": "author", "selector": "div.writter_name", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "div.update-publish-time span",
                "type": "text",
            },
            {"name": "synopsis", "selector": "h2.sub-title", "type": "text"},
            {
                "name": "content",
                "selector": "div.articlebodycontent > p",
                "type": "list",
                "fields": [{"name": "para_content", "type": "text"}],
            },
        ],
    },
    # "MSN": {  # TODO: No news items are getting extracted at all
    #     "name": "Article",
    #     "baseSelector": "body entry-point-views div.article_content",  # consumption-page-gridarea_content",
    #     "fields": [
    #         # {"name": "author", "selector": "div.writter_name", "type": "text"},
    #         {"name": "heading", "selector": "h1.viewsHeaderText", "type": "text"},
    #         {
    #             "name": "date_scraped",
    #             "selector": "div.consumption-page-content-header div.viewsInfo span.viewsAttribution",
    #             "type": "text",
    #         },
    #         # {"name": "synopsis", "selector": "h2.sub-title", "type": "text"},
    #         {
    #             "name": "content",
    #             "selector": "article.article-reader-container body.article-body > p",
    #             "type": "list",
    #             "fields": [{"name": "para_content", "type": "text"}],
    #         },  # TODO: this is selecting only the first para in the story, need to capture all p tags
    #     ],
    # },
    "Mongabay-India": {
        "name": "Article",
        "baseSelector": "body main div.single",
        "fields": [
            # {"name": "author", "selector": "div.article-headline div.about-author div.extra-info span.bylines a", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "div.article-headline div.about-author div.extra-info span.date",
                "type": "text",
            },
            {
                "name": "synopsis",
                "selector": "div.inner div.bulletpoints",
                "type": "text",
            },
            {
                "name": "content",
                "selector": "div.inner > article > p",
                "type": "list",
                "fields": [{"name": "para_content", "type": "text"}],
            },
        ],
    },
    "Free Press Journal": {
        "name": "Article",
        "baseSelector": "div.inner-wrap",
        "fields": [
            # {"name": "author", "selector": "div.article-headline div.about-author div.extra-info span.bylines a", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "div.article-lhs div.updated-time",
                "type": "text",
            },  # TODO: date doesn't have a tag, hence some extra text is getting extracted
            {
                "name": "synopsis",
                "selector": "div.article-container-wrap h2.slug",
                "type": "text",
            },
            {
                "name": "content",
                "selector": "article > p",
                "type": "list",
                "fields": [{"name": "para_content", "type": "text"}],
            },
        ],
    },
    "ThePrint": {
        "name": "Article",
        "baseSelector": "article.status-publish",
        "fields": [
            # {"name": "author", "selector": "div.tdb-author-name-wrap a.tdb-author-name", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "div.wpb_wrapper div.tdb_single_date div.tdb-block-inner time.entry-date",
                "type": "text",
            },
            # {
            #     "name": "synopsis",
            #     "selector": "xyz",
            #     "type": "text",
            # },
            {
                "name": "content",
                "selector": "div.tdb-block-inner p:not([class])",
                "type": "list",
                "fields": [{"name": "para_content", "type": "text"}],
            },  # TODO: not properly organized tags
        ],
    },
    "Down To Earth": {
        "name": "Article",
        "baseSelector": "div.infinite-wrapper",
        "fields": [
            # {"name": "author", "selector": "div.arr-name-share span a", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "div.arr--publish-details time.arr__timeago",
                "type": "text",
            },
            {
                "name": "synopsis",
                "selector": "div.arr--sub-headline",
                "type": "text",
            },
            {
                "name": "content",
                "selector": "div.arr--story-page-card-wrapper div.arr--element-container div.arr--text-element",
                "type": "text",
            },
        ],
    },
    "Gulf News": {
        "name": "Article",
        "baseSelector": "div.story-grid",
        "fields": [
            # {"name": "author", "selector": "div.author-div a", "type": "text"},
            {
                "name": "date_scraped",
                "selector": "time",
                "type": "text",
            },
            {
                "name": "synopsis",
                "selector": "p.d-C--",
                "type": "text",
            },
            {
                "name": "content",
                "selector": "div.rlKNF div.story-element-text",
                "type": "nested_list",
                "fields": [
                    {
                        "name": "content1",
                        "selector": "div > div > p",
                        "type": "list",
                        "fields": [{"name": "para_content", "type": "text"}],
                    }
                ],
            },
        ],
    },
}
