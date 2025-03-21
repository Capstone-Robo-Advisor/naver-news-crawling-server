from pydantic import BaseModel

class Article(BaseModel):
    title: str
    link: str
    source: str
    pub_date: str