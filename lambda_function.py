import json
import logging
import os
from datetime import datetime
# 크롤링 모듈 임포트 경로 수정
from crawlling.main import crawl_naver_news  # crawlling 폴더 안의 main.py 모듈 참조

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """AWS Lambda 핸들러 함수"""
    try:
        logger.info("네이버 뉴스 크롤링 시작")

        # 실행 시작 시간 기록
        start_time = datetime.now()

        # 뉴스 크롤링 및 DB 저장
        article_count = crawl_naver_news()

        # 실행 종료 시간 및 소요 시간 계산
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': '크롤링 성공',
                'article_count': article_count,
                'execution_time_seconds': duration_seconds,
                'timestamp': end_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        }
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'크롤링 실패: {str(e)}'
            })
        }