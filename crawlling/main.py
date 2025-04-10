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
            # 현재 DB에 저장된 기사 수 확인
            cursor.execute("SELECT COUNT(*) FROM news_articles")
            current_count = cursor.fetchone()[0]

            if current_count >= 100:
                logger.info("DB에 이미 100개의 기사가 저장되어 있습니다. 기존 기사만 갱신합니다.")
                # 기존 기사 갱신 로직
                for article in articles:
                    if not article['link']:
                        logger.warning("링크가 없는 기사 건너뜀")
                        continue

                    cursor.execute(
                        "SELECT id FROM news_articles WHERE link = %s",
                        (article['link'],)
                    )
                    exists = cursor.fetchone()

                    if exists:
                        # 기존 기사 업데이트
                        cursor.execute(
                            """
                            UPDATE news_articles
                            SET title = %s, content = %s, source = %s, image_url = %s, published_time = %s, crawled_at = %s
                            WHERE link = %s
                            """,
                            (
                                article['title'],
                                article['lede'],
                                article['source'],
                                article['thumbnail'],
                                article['time_text'],
                                article['crawled_at'],
                                article['link']
                            )
                        )
                        logger.info(f"기존 기사 갱신: {article['title']}")

            else:
                # 새 기사 삽입 로직 (필요 시)
                for article in articles:
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
        logger.info(f"총 {len(articles)}개 기사 중 새로운 기사 및 갱신 처리 완료")

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
    target_article_count = 100

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                # "--single-process",
                # "--no-zygote",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--ignore-certificate-errors",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            bypass_csp=True,
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

        try:
            page = context.new_page()
            page.set_default_timeout(180000)

            # 초기 페이지 로드 시도
            for attempt in range(3):
                try:
                    logger.info(f"페이지 로드 시도 {attempt + 1}/3")
                    page.goto(BASE_URL, wait_until="networkidle", timeout=180000)
                    page.wait_for_selector("div.sa_item_inner", timeout=30000)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise Exception(f"페이지 로드 실패: {str(e)}")
                    page.wait_for_timeout(5000 * (attempt + 1))

            logger.info("초기 페이지 로드 완료")

            # 초기 기사 수집
            current_articles = collect_articles_from_page(page)
            articles.extend(current_articles)
            logger.info(f"초기 기사 수: {len(articles)}")

            # 기사 더보기 버튼 클릭 및 추가 기사 수집
            more_button_selector = "#newsct > div.section_latest > div > div.section_more > a"
            click_count = 0
            max_clicks = 15
            consecutive_no_new = 0

            while len(articles) < target_article_count and click_count < max_clicks:
                try:
                    # 스크롤 및 대기
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)  # 스크롤 대기 시간 증가

                    # 버튼 가시성 확인
                    is_button_visible = page.is_visible(more_button_selector)
                    if not is_button_visible:
                        logger.info("더 이상 '기사 더보기' 버튼이 없습니다.")
                        break

                    # 버튼 클릭 시도
                    logger.info(f"'기사 더보기' 버튼 클릭 시도 {click_count + 1}")

                    # JavaScript로 직접 클릭 (더 안정적인 클릭 방식)
                    page.evaluate(f"document.querySelector('{more_button_selector}').click()")
                    page.wait_for_timeout(3000)  # 데이터 로드 대기 시간 증가

                    # 새로운 기사가 로드될 때까지 대기
                    page.wait_for_selector("div.sa_item_inner", timeout=30000)

                    # 새 기사 수집
                    new_articles = collect_articles_from_page(page)

                    # 중복 제거 및 새 기사 추가
                    before_count = len(articles)
                    for article in new_articles:
                        if article["link"] and not any(existing["link"] == article["link"] for existing in articles):
                            articles.append(article)

                    new_added = len(articles) - before_count
                    logger.info(f"클릭 {click_count + 1} 후 {new_added}개 새 기사 추가됨. 현재 총 {len(articles)}개")

                    # 새 기사 추가 여부 확인
                    if new_added == 0:
                        consecutive_no_new += 1
                        if consecutive_no_new >= 3:
                            logger.info("3번 연속 새 기사가 추가되지 않아 종료합니다.")
                            break
                    else:
                        consecutive_no_new = 0

                    click_count += 1

                except Exception as e:
                    logger.error(f"버튼 클릭 중 오류 발생: {str(e)}")
                    # 한 번의 실패는 허용하고 다시 시도
                    page.wait_for_timeout(5000)
                    continue

            logger.info(f"최종 크롤링 완료: 총 {len(articles)}개 기사")

            # DB에 저장
            save_articles_to_db(articles)

            return len(articles)

        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {str(e)}")
            raise
        finally:
            try:
                context.close()
                browser.close()
            except Exception as e:
                logger.error(f"브라우저 종료 중 오류: {str(e)}")


# 직접 실행 시 테스트
if __name__ == "__main__":
    try:
        article_count = crawl_naver_news()
        print(f"크롤링 및 저장 완료: 총 {article_count}개 기사")
    except Exception as e:
        print(f"오류 발생: {str(e)}")