# naver-news-crawling-server

네이버 뉴스 크롤링 자동화 서버
캡스톤디자인 프로젝트 (투자 포트폴리오 추천 시스템의 일부 구성 요소)

---

## 📦 프로젝트 개요

- 네이버 뉴스를 주기적으로 크롤링하여 GPT 모델에 활용 가능한 데이터셋을 생성
- 기존 AWS Lambda 기반 실행 구조에서 **EC2 기반 Docker 자동 배포 시스템**으로 마이그레이션
- GitHub Actions를 통해 **코드 Push → EC2 서버 자동 배포**가 이루어짐

---


## 🚀 주요 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| 크롤러 | Python |
| 컨테이너화 | Docker |
| 배포 자동화 | GitHub Actions + appleboy/ssh-action |
| 실행 스케줄 | Linux Crontab |
| 배포 대상 | AWS EC2 (Ubuntu 22.04), x86_64(현재), 차후에 arm64 아키텍처 전환 고려 |

---

## 🔁 배포 및 실행 구조

```plaintext
[1] GitHub main 브랜치로 push
    ↓
[2] GitHub Actions 트리거 (on: push)
    ↓
[3] EC2 접속 → 최신 코드로 초기화 (git reset --hard)
    ↓
[4] Docker 이미지 재빌드
    ↓
[5] run-crawler.sh 생성
    ↓
[6] 크론탭 등록 (9시, 15시, 21시, 22시 45분)
    ↓
[7] 자동으로 도커 컨테이너 실행 → 뉴스 수집 로그 저장
```

---

## 📂 디렉토리 구조 (예시)

```plaintext
naver-news-crawling-server/
├── crawlling/                   # 뉴스 크롤링 관련 Python 코드
│   ├── __init__.py
│   └── main.py
│
├── .github/                     # GitHub Actions 설정 디렉토리
│   └── workflows/
│       └── deploy.yml           # EC2 자동 배포 워크플로우
│
├── .env                         # 환경변수 파일 (Docker에서 참조)
├── .dockerignore                # Docker 이미지 빌드 시 제외할 파일
├── .gitignore                   # Git에서 추적하지 않을 파일 목록
├── Dockerfile                   # Docker 이미지 빌드 정의
```

---

## 🔧 환경 설정

- `.env` 파일을 `/home/ubuntu/.env` 경로에 생성
- 환경 변수:
```plaintext
# .env 파일 (절대 GitHub에 커밋하지 마세요!)
RDS_HOST=your_rds_host
RDS_PORT=your_rds_port
RDS_USER=your_name
RDS_PASSWORD=your_password
RDS_DB=db_name
```

---

## 🐳 도커 실행 예시 (수동 실행 시)

```plaintext
# 직접 실행 예시
/home/ubuntu/run-crawler.sh

# 도커 파일 실행 예시
docker run --rm --env-file /home/ubuntu/.env naver-news-crawler:latest
```

---

## 📚 해당 레포와 관련된 캡스톤 기록지

[캡스톤 디자인 - 크롤링 과정에서의 시행착오](https://mewing-jellyfish-e7d.notion.site/1c4e3b008f2e80a3aba9d51c830ba80f?v=1c4e3b008f2e80d4a047000c77106d46)
