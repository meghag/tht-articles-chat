from pydantic import BaseModel


class NewsItem(BaseModel):
    """
    Represents the data structure of a News Item.
    """

    title: str
    date: str
    source: str
    content: str
    synopsis: str
    url: str
    # author: str
