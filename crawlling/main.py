import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from crawler import crawl_news
from storage import save_to_json
from models import CrawlResult
app = FastAPI()

@app.get("/news")
async def crawl_news_endpoint() -> CrawlResult:
    '''
    네이버 뉴스 크롤링 API 엔드포인트
    '''
    try:
        articles = await crawl_news()

        # 데이터가 있으면 JSON 파일로 저장
        if articles:
            filename = save_to_json(articles)
            return {
                "message": f"크롤링 성공 및 데이터 저장 완료 (총 {len(articles)}개 기사 수집, 파일: {filename})",
                "total_articles": len(articles),
                "data": articles
            }
        else:
            return {"message" : "크롤링 성공 (그러나 데이터 없음)", "data" : []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))