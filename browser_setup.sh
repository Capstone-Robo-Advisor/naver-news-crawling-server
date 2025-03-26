#!/bin/bash

# AWS Lambda에 호환되는 Chromium 다운로드 및 설치
cd ${LAMBDA_TASK_ROOT}
wget -q https://playwright.azureedge.net/builds/chromium/1045/chromium-linux.zip
mkdir -p browser/chromium-1045
unzip -q chromium-linux.zip -d browser/chromium-1045
mv browser/chromium-1045/chromium-linux/* browser/chromium-1045/
rm -rf browser/chromium-1045/chromium-linux
rm chromium-linux.zip

# 권한 설정
chmod -R 755 browser/