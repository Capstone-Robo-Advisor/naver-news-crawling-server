#!/usr/bin/env python3
import os
import logging
from datetime import datetime
from crawlling.main import crawl_naver_news

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("네이버 뉴스 크롤링 시작")
        start_time = datetime.now()

        # 크롤링 실행 (기존 main.py의 함수 호출)
        article_count = crawl_naver_news()

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(f"크롤링 완료: {article_count}개 기사, 소요시간: {duration_seconds}초")
        return True
    except Exception as e:
        logger.error(f"크롤링 실패: {str(e)}")
        return False


if __name__ == "__main__":
    main()