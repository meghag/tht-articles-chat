from pydantic import BaseModel


class NewsItem(BaseModel):
    """
    Represents the data structure of a News Item.
    """

    title: str
    date: str
    publication: str
    article_content: str
    summary: str
    url: str
