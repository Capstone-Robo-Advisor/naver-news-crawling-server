from typing import TypedDict, Optional, List

class NewsArticle(TypedDict):
    thumbnail: Optional[str]
    link: Optional[str]
    title: Optional[str]
    lede: Optional[str]
    source: Optional[str]
    time: Optional[str]

class CrawlResult(TypedDict):
    message: str
    total_articles: int
    data: List[NewsArticle]