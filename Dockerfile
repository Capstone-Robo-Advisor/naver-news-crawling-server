FROM ubuntu:22.04

# 비대화형 설치 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

# 기본 패키지 및 Python 설치
RUN apt-get update && \
    apt-get install -y \
    python3.9 \
    python3-pip \
    wget \
    curl \
    unzip \
    tzdata \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# AWS Lambda Runtime Interface Emulator 설치
RUN curl -Lo /usr/local/bin/aws-lambda-rie \
    https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie && \
    chmod +x /usr/local/bin/aws-lambda-rie

# 작업 디렉토리 설정
WORKDIR /var/task

# Python 패키지 설치
COPY requirements.txt .
RUN echo "Installing Python packages..." && \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir playwright awslambdaric && \
    echo "Python packages installed successfully"

# Playwright 브라우저 설치 (수정된 부분)
ENV PLAYWRIGHT_BROWSERS_PATH=/var/task/browser
RUN echo "Installing Playwright browsers..." && \
    playwright install --with-deps chromium && \
    echo "Playwright browsers installed successfully"

# 애플리케이션 코드 복사
COPY crawlling/ /var/task/crawlling/
COPY lambda_function.py /var/task/

# 디버그용 테스트 스크립트 생성
RUN echo 'import sys\n\
import os\n\
import json\n\
import logging\n\
\n\
# 로깅 설정\n\
logging.basicConfig(level=logging.INFO)\n\
\n\
print("=== Environment Variables ===")\n\
for key, value in os.environ.items():\n\
    if "RDS" in key:\n\
        print(f"{key}: {value}")\n\
\n\
print("\\n=== Python Path ===")\n\
print(sys.path)\n\
\n\
print("\\n=== Starting Crawler ===")\n\
try:\n\
    import lambda_function\n\
    print("Lambda function imported successfully")\n\
    result = lambda_function.lambda_handler({}, None)\n\
    print("\\n=== Execution Result ===")\n\
    print(json.dumps(result, indent=2))\n\
except Exception as e:\n\
    print(f"\\n=== Error Occurred ===")\n\
    print(f"Error: {str(e)}")\n\
    import traceback\n\
    print("\\n=== Traceback ===")\n\
    print(traceback.format_exc())\n\
' > /var/task/debug.py

# 환경 변수 설정
ENV PYTHONPATH="/var/task"
ENV PLAYWRIGHT_BROWSERS_PATH="/var/task/browser"
ENV PYTHONUNBUFFERED=1

# Lambda 실행을 위한 bootstrap 스크립트 생성
RUN mkdir -p /var/runtime && \
    echo '#!/bin/bash\n\
if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then\n\
    exec /usr/local/bin/aws-lambda-rie /usr/local/bin/python3 -m awslambdaric "$@"\n\
else\n\
    exec /usr/local/bin/python3 -m awslambdaric "$@"\n\
fi' > /var/runtime/bootstrap && \
    chmod +x /var/runtime/bootstrap

ENTRYPOINT ["/var/runtime/bootstrap"]
CMD ["lambda_function.lambda_handler"]