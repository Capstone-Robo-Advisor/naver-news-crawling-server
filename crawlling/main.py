# news_crawler.py
from playwright.sync_api import sync_playwright
import os
import pymysql
import logging
from datetime import datetime
from dotenv import load_dotenv

# 로깅 설정
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# RDS 연결 설정
RDS_HOST = os.environ.get("RDS_HOST")
RDS_PORT = int(os.environ.get("RDS_PORT", 3306))
RDS_USER = os.environ.get("RDS_USER")
RDS_PASSWORD = os.environ.get("RDS_PASSWORD")
RDS_DB = os.environ.get("RDS_DB")


def connect_to_db():
    """RDS MySQL 데이터베이스 연결"""
    try:
        # 연결 정보 로깅 (비밀번호는 로깅하지 않음)
        logging.info(f"DB 연결 시도: {RDS_HOST}:{RDS_PORT}, 사용자: {RDS_USER}, DB: {RDS_DB}")

        conn = pymysql.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            user=RDS_USER,
            password=RDS_PASSWORD,
            db=RDS_DB,
            charset='utf8mb4'
        )
        logger.info("RDS 데이터베이스 연결 성공")
        return conn
    except Exception as e:
        logger.error(f"RDS 연결 오류: {str(e)}")
        raise


def collect_articles_from_page(page):
    """현재 페이지에서 모든 기사를 수집하는 함수"""
    articles = []

    # 기사 수집
    news_items = page.query_selector_all("div.sa_item_inner")

    for news in news_items:
        try:
            # 썸네일
            thumbnail_elem = news.query_selector(".sa_thumb_inner img")
            thumbnail = thumbnail_elem.get_attribute('src') if thumbnail_elem else None

            # 링크
            link_elem = news.query_selector(".sa_thumb_link")
            link = link_elem.get_attribute('href') if link_elem else None

            # 기사 제목 크롤링
            title_elem = news.query_selector(".sa_text_strong")
            title = title_elem.inner_text() if title_elem else None

            # 요약 크롤링
            lede_elem = news.query_selector(".sa_text_lede")
            lede = lede_elem.inner_text() if lede_elem else None

            # 출처
            source_elem = news.query_selector(".sa_text_press")
            source = source_elem.inner_text() if source_elem else None

            # 몇 시간 전인지
            time_elem = news.query_selector(".sa_text_datetime b")
            time_text = time_elem.inner_text() if time_elem else None

            articles.append({
                "thumbnail": thumbnail,
                "link": link,
                "title": title,
                "lede": lede,
                "source": source,
                "time_text": time_text,
                "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            logger.error(f"기사 데이터 추출 중 오류: {str(e)}")
            continue

    return articles


def save_articles_to_db(articles):
    """크롤링한 기사를 RDS에 저장"""
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor() as cursor:
            for article in articles:
                # 중복 체크 (링크 기준)
                if not article['link']:
                    logger.warning("링크가 없는 기사 건너뜀")
                    continue

                cursor.execute(
                    "SELECT id FROM news_articles WHERE link = %s",
                    (article['link'],)
                )
                exists = cursor.fetchone()

                if not exists:
                    # 새 기사 삽입
                    cursor.execute(
                        """
                        INSERT INTO news_articles 
                        (title, content, source, link, image_url, published_time, crawled_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            article['title'],
                            article['lede'],
                            article['source'],
                            article['link'],
                            article['thumbnail'],
                            article['time_text'],
                            article['crawled_at']
                        )
                    )
                    logger.info(f"새 기사 저장: {article['title']}")

        conn.commit()
        logger.info(f"총 {len(articles)}개 기사 중 새로운 기사 처리 완료")

    except Exception as e:
        logger.error(f"DB 저장 중 오류: {str(e)}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


def crawl_naver_news():
    """네이버 뉴스 크롤링 메인 함수"""
    BASE_URL = "https://news.naver.com/breakingnews/section/101/258"
    articles = []
    target_article_count = 100  # 목표 기사 수

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", '--disable-dev-shm-usage'],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        )

        page = context.new_page()

        # 초기 페이지 로드
        page.goto(BASE_URL)
        page.wait_for_selector("div.sa_item_inner", timeout=20000)
        logger.info("초기 페이지 로드 완료")

        # 초기 기사 수집
        current_articles = collect_articles_from_page(page)
        articles.extend(current_articles)
        logger.info(f"초기 기사 수: {len(articles)}")

        # 목표 기사 수에 도달할 때까지 '기사 더보기' 버튼 클릭
        more_button_selector = "#newsct > div.section_latest > div > div.section_more > a"
        click_count = 0
        max_clicks = 15  # 최대 클릭 횟수 제한
        consecutive_no_new = 0  # 연속적으로 새 기사가 없는 횟수

        while len(articles) < target_article_count and click_count < max_clicks:
            try:
                # 페이지 하단으로 스크롤
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)

                # '기사 더보기' 버튼이 있는지 확인
                is_button_visible = page.is_visible(more_button_selector)
                if not is_button_visible:
                    logger.info("더 이상 '기사 더보기' 버튼이 없습니다.")
                    break

                # 버튼 클릭
                logger.info(f"'기사 더보기' 버튼 클릭 시도 {click_count + 1}")
                page.click(more_button_selector)
                page.wait_for_timeout(2000)  # 데이터 로드 대기

                # 새 기사 수집
                new_articles = collect_articles_from_page(page)

                # 중복 제거
                before_count = len(articles)
                for article in new_articles:
                    if article["link"] and not any(existing["link"] == article["link"] for existing in articles):
                        articles.append(article)

                new_added = len(articles) - before_count
                logger.info(f"클릭 {click_count + 1} 후 {new_added}개 새 기사 추가됨. 현재 총 {len(articles)}개")

                # 새 기사가 추가되지 않았다면 종료
                if new_added == 0:
                    consecutive_no_new += 1
                    if consecutive_no_new >= 3:  # 3번 연속 새 기사가 없으면 종료
                        logger.info("3번 연속 새 기사가 추가되지 않아 종료합니다.")
                        break
                else:
                    consecutive_no_new = 0

                click_count += 1

            except Exception as e:
                logger.error(f"버튼 클릭 중 오류 발생: {str(e)}")
                break

        browser.close()
        logger.info(f"최종 크롤링 완료: 총 {len(articles)}개 기사")

        # DB에 저장
        save_articles_to_db(articles)

        return len(articles)


# 직접 실행 시 테스트
if __name__ == "__main__":
    try:
        article_count = crawl_naver_news()
        print(f"크롤링 및 저장 완료: 총 {article_count}개 기사")
    except Exception as e:
        print(f"오류 발생: {str(e)}")