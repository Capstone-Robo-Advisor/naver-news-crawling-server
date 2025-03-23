import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright

app = FastAPI()

BASE_URL = "https://news.naver.com/breakingnews/section/101/258"

async def crawl_news() -> list[dict[str, str | None]] | None:
    articles = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # `await` 추가
        page = await browser.new_page()

        # User-Agent 추가
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        })

        await page.goto(BASE_URL)

        # AJAX 데이터 로드 대기
        await page.wait_for_selector("div.sa_item_inner", timeout=20000)

        # 스크롤을 통해 모든 기사 로드
        last_height = 0
        while True:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(5000)  # 5초 대기
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 기사 수집
        for news in await page.query_selector_all(".sa_item_inner"):
            try:
                # 썸네일
                thumbnail_elem = await news.query_selector(".sa_thumb_inner img")
                thumbnail = await thumbnail_elem.get_attribute('src') if thumbnail_elem else None

                # 링크
                link_elem = await news.query_selector(".sa_thumb_link")
                link = await link_elem.get_attribute('href') if link_elem else None

                # 기사 제목 크롤링
                title_elem = await news.query_selector(".sa_text_strong")
                title = await title_elem.inner_text() if title_elem else None

                # 요약 크롤링
                lede_elem = await news.query_selector(".sa_text_lede")
                lede = await lede_elem.inner_text() if lede_elem else None

                # 출처
                source_elem = await news.query_selector(".sa_text_press")
                source = await source_elem.inner_text() if source_elem else None

                # 몇 시간 전인지
                time_elem = await news.query_selector(".sa_text_datetime b")
                time = await time_elem.inner_text() if time_elem else None
                articles.append({
                    "thumbnail": thumbnail,
                    "link": link,
                    "title": title,
                    "lede": lede,
                    "source": source,
                    "time": time
                })
            except AttributeError:
                continue

        await browser.close()
        return articles

def save_to_json(data: list[dict[str, str | None]]):
    '''
    크롤링한 데이터를 JSON 파일로 저장
    '''
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"news_{timestamp}.json"

    # JSON 데이터 저장
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"📋 데이터가 JSON 파일로 저장되었습니다 : {filename}")

@app.get("/news")
async def crawl_news_endpoint():
    '''
    네이버 뉴스 크롤링 API 엔드포인트
    '''
    try:
        articles = await crawl_news()

        # 데이터가 있으면 JSON 파일로 저장
        if articles:
            save_to_json(articles)
            return {
                "message": f"크롤링 성공 및 데이터 저장 완료 (총 {len(articles)}개 기사 수집)",
                "total_articles": len(articles),
                "data": articles
            }
        else:
            return {"message" : "크롤링 성공 (그러나 데이터 없음)", "data" : []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))