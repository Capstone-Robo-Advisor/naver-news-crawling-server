import asyncio
from playwright.async_api import async_playwright

# BASE_URL = "https://news.naver.com/breakingnews/section/101/258"

async def crawl_news() -> list[dict[str, str | None]] | None:
    articles = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # `await` 추가
        page = await browser.new_page()
        await page.goto(BASE_URL)

        # 스크롤을 통해 모든 기사 로드
        last_height = 0
        while True:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)  # 2초 대기
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 기사 수집
        for news in await page.query_selector_all(".sa_item_inner"):
            try:
                title = await news.query_selector(".sa_text_strong").inner_text()
                link = await news.query_selector(".sa_text_title").get_attribute('href')
                lede = await news.query_selector(".sa_text_lede").inner_text()
                source = await news.query_selector(".sa_text_press").inner_text()
                time = await news.query_selector(".sa_text_datetime b").inner_text()
                articles.append({
                    "title": title,
                    "link": link,
                    "lede": lede,
                    "source": source,
                    "time": time
                })
            except AttributeError:
                continue
        await browser.close()
        return articles

# 결과 출력
async def main():
    news_data = await crawl_news()
    for idx, article in enumerate(news_data, 1):
        print(f"[{idx}] {article['title']} ({article['time']})")
        print(f"    링크: {article['link']}")
        print(f"    요약: {article['lede']}")
        print(f"    출처: {article['source']}")
        print("="*60)

# 실행
asyncio.run(main())