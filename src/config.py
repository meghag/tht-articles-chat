# config.py

BASE_URL = "https://india.mongabay.com/2025/01/new-study-proposes-roadmap-to-conserve-the-clouded-leopard/"
CSS_SELECTOR_MAP = {"Times of India": []}
# "[class^='info-container']"
REQUIRED_KEYS = [
    "title",
    "date",
    "source",
    "content",
    "synopsis",
    "url",
]

SCHEMA_MAP = {
    "Times of India": {
        "name": "Article",
        "baseSelector": "div.okf2Z",  # Repeated elements
        "fields": [
            # {"name": "author", "selector": "div.xf8Pm a", "type": "text"},
            {"name": "date", "selector": "div.xf8Pm span", "type": "text"},
            {"name": "synopsis", "selector": "div.art_synopsis", "type": "text"},
            {
                "name": "content",
                "selector": "div.js_tbl_article",
                "type": "text",
            },
        ],
    }
}
