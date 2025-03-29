FROM mcr.microsoft.com/playwright/python:v1.36.0-focal

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY crawlling/ ./crawlling/
COPY run_crawler.py .

# Playwright 환경 변수 설정
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PYTHONUNBUFFERED=1

# 실행 권한 설정
RUN chmod +x run_crawler.py

# 컨테이너 실행 시 실행할 명령어
CMD ["python", "run_crawler.py"]