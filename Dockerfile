FROM public.ecr.aws/lambda/python:3.9

# 기본 패키지 설치
RUN yum update -y && \
    yum install -y \
    wget \
    unzip \
    tar \
    gzip \
    && yum clean all

# 필요한 라이브러리 설치
RUN yum install -y \
    alsa-lib \
    atk \
    cups-libs \
    gtk3 \
    ipa-gothic-fonts \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi \
    xorg-x11-fonts-cyrillic \
    xorg-x11-fonts-misc \
    xorg-x11-fonts-Type1 \
    xorg-x11-utils \
    && yum clean all

# Playwright용 Chromium 수동 설치 (AWS Lambda에 호환되는 방식)
RUN mkdir -p ${LAMBDA_TASK_ROOT}/browser
COPY browser_setup.sh ${LAMBDA_TASK_ROOT}/
RUN chmod +x ${LAMBDA_TASK_ROOT}/browser_setup.sh && \
    ${LAMBDA_TASK_ROOT}/browser_setup.sh

# Python 패키지 설치
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir playwright

# 애플리케이션 코드 복사
COPY crawlling/ ${LAMBDA_TASK_ROOT}/crawlling/
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# 환경 변수 설정
ENV PLAYWRIGHT_BROWSERS_PATH=${LAMBDA_TASK_ROOT}/browser
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Lambda 핸들러 지정
CMD ["lambda_function.lambda_handler"]