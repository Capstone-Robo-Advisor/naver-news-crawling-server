#FROM public.ecr.aws/lambda/python:3.9
#
## 기본 패키지 설치
#RUN yum update -y && \
#    yum install -y \
#    wget \
#    unzip \
#    tar \
#    gzip \
#    && yum clean all
#
## 필요한 라이브러리 설치
#RUN yum install -y \
#    alsa-lib \
#    atk \
#    cups-libs \
#    gtk3 \
#    ipa-gothic-fonts \
#    libXcomposite \
#    libXcursor \
#    libXdamage \
#    libXext \
#    libXi \
#    libXrandr \
#    libXScrnSaver \
#    libXtst \
#    pango \
#    xorg-x11-fonts-100dpi \
#    xorg-x11-fonts-75dpi \
#    xorg-x11-fonts-cyrillic \
#    xorg-x11-fonts-misc \
#    xorg-x11-fonts-Type1 \
#    xorg-x11-utils \
#    && yum clean all
#
## Playwright용 Chromium 수동 설치 (AWS Lambda에 호환되는 방식)
#RUN mkdir -p ${LAMBDA_TASK_ROOT}/browser
#COPY browser_setup.sh ${LAMBDA_TASK_ROOT}/
#RUN chmod +x ${LAMBDA_TASK_ROOT}/browser_setup.sh && \
#    ${LAMBDA_TASK_ROOT}/browser_setup.sh
#
## Python 패키지 설치
#COPY requirements.txt ${LAMBDA_TASK_ROOT}/
#RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt
#RUN pip install --no-cache-dir playwright
#
## 애플리케이션 코드 복사
#COPY crawlling/ ${LAMBDA_TASK_ROOT}/crawlling/
#COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
#
## 환경 변수 설정
#ENV PLAYWRIGHT_BROWSERS_PATH=${LAMBDA_TASK_ROOT}/browser
#ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
#
## Lambda 핸들러 지정
#CMD ["lambda_function.lambda_handler"]

# Define function directory
ARG FUNCTION_DIR="/function"

FROM mcr.microsoft.com/playwright/python:v1.36.0-focal as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
    apt-get install -y \
    g++ \
    make \
    cmake \
    unzip \
    libcurl4-openssl-dev

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Copy function code and requirements
COPY requirements.txt ${FUNCTION_DIR}/
COPY lambda_function.py ${FUNCTION_DIR}/
COPY crawlling/ ${FUNCTION_DIR}/crawlling/
COPY .env* ${FUNCTION_DIR}/

# Install Python dependencies
RUN pip3 install --upgrade pip && \
    pip3 install --target ${FUNCTION_DIR} -r ${FUNCTION_DIR}/requirements.txt && \
    pip3 install --target ${FUNCTION_DIR} awslambdaric

# Multi-stage build: grab a fresh copy of the base image
FROM mcr.microsoft.com/playwright/python:v1.36.0-focal

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PLAYWRIGHT_HEADLESS_MODE=true
ENV PLAYWRIGHT_DISABLE_GPU=true

# Ensure execution permissions
RUN chmod 755 ${FUNCTION_DIR}/lambda_function.py

ENTRYPOINT [ "/usr/bin/python3", "-m", "awslambdaric" ]
CMD [ "lambda_function.lambda_handler" ]