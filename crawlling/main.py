import sys
import os
import json
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright, TimeoutError

app = FastAPI()

# 기본 URL
BASE_URL = "https://news.naver.com/breakingnews/section/101/258"

async def crawl_news() -> list[dict[str, str | None]] | None:
    articles = []
    target_article_count = 200  # 목표 기사 수

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # 초기 페이지 로드
        await page.goto(BASE_URL)
        await page.wait_for_selector("div.sa_item_inner", timeout=20000)
        print("초기 페이지 로드 완료")
        
        # 초기 기사 수집
        current_articles = await collect_articles_from_page(page)
        articles.extend(current_articles)
        print(f"초기 기사 수: {len(articles)}")
        
        # 목표 기사 수에 도달할 때까지 '기사 더보기' 버튼 클릭
        more_button_selector = "#newsct > div.section_latest > div > div.section_more > a"
        click_count = 0
        max_clicks = 30  # 최대 클릭 횟수 제한
        
        while len(articles) < target_article_count and click_count < max_clicks:
            try:
                # 페이지 하단으로 스크롤
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                
                # '기사 더보기' 버튼이 있는지 확인
                is_button_visible = await page.is_visible(more_button_selector)
                if not is_button_visible:
                    print("더 이상 '기사 더보기' 버튼이 없습니다.")
                    break
                
                # 버튼 클릭
                print(f"'기사 더보기' 버튼 클릭 시도 {click_count + 1}")
                await page.click(more_button_selector)
                await page.wait_for_timeout(3000)  # 데이터 로드 대기
                
                # 새 기사 수집
                new_articles = await collect_articles_from_page(page)
                
                # 중복 제거
                before_count = len(articles)
                for article in new_articles:
                    if not any(existing["link"] == article["link"] for existing in articles):
                        articles.append(article)
                
                new_added = len(articles) - before_count
                print(f"클릭 {click_count + 1} 후 {new_added}개 새 기사 추가됨. 현재 총 {len(articles)}개")
                
                # 새 기사가 추가되지 않았다면 종료
                if new_added == 0:
                    consecutive_no_new += 1
                    if consecutive_no_new >= 3:  # 3번 연속 새 기사가 없으면 종료
                        print("3번 연속 새 기사가 추가되지 않아 종료합니다.")
                        break
                else:
                    consecutive_no_new = 0
                
                click_count += 1
                
            except TimeoutError:
                print(f"버튼 클릭 시 타임아웃 발생 (시도 {click_count + 1})")
                break
            except Exception as e:
                print(f"버튼 클릭 중 오류 발생: {str(e)}")
                break
                
        await browser.close()
        print(f"최종 크롤링 완료: 총 {len(articles)}개 기사")
        return articles

async def collect_articles_from_page(page) -> list[dict[str, str | None]]:
    """현재 페이지에서 모든 기사를 수집하는 함수"""
    articles = []
    
    # 기사 수집
    news_items = await page.query_selector_all("div.sa_item_inner")
    for news in news_items:
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
        except Exception as e:
            print(f"기사 데이터 추출 중 오류: {str(e)}")
            continue
    
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