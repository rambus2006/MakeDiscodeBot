# 📰 NewsPicker

> Google News RSS를 활용하여 관심 분야의 최신 뉴스를 수집하고 Discord Webhook으로 전송하는 Python 기반 뉴스 알림 봇

NewsPicker는 사용자가 원하는 뉴스 카테고리의 최신 기사를 Google News RSS에서 수집하고, 새로운 뉴스만 Discord 채널에 Embed 형태로 전송하는 프로젝트입니다.

별도의 서버를 직접 운영하지 않고 **GitHub Actions를 이용해 주기적으로 자동 실행**할 수 있도록 구성했습니다.

---

## ✨ 주요 기능

* 📰 Google News RSS 기반 최신 뉴스 수집
* 🇰🇷 한국 뉴스
* 💻 IT 뉴스
* 🤖 AI 뉴스
* 💰 경제 뉴스
* 🌎 국제 뉴스
* 🚨 속보
* 🔗 뉴스 원문 링크 제공
* 🎨 Discord Embed 형태로 뉴스 전송
* 🚫 이미 전송한 뉴스 중복 방지
* 💾 `sent_news.json`을 이용한 전송 기록 저장
* 🔐 `.env`와 GitHub Secrets를 이용한 Webhook 보안 관리
* ☁️ GitHub Actions를 이용한 자동 실행

---

## 🛠️ Tech Stack

| 분야              | 기술              |
| --------------- | --------------- |
| Language        | Python 3.13     |
| RSS             | Google News RSS |
| HTTP            | Requests        |
| RSS Parser      | Feedparser      |
| Environment     | python-dotenv   |
| Notification    | Discord Webhook |
| Automation      | GitHub Actions  |
| Version Control | Git / GitHub    |

---

## 📁 프로젝트 구조

```text
NewsPicker/
│
├── .github/
│   └── workflows/
│       └── news.yml
│
├── WebHookNewsPicker.py
├── sent_news.json
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

> `.venv`와 `.env`는 GitHub에 업로드하지 않습니다.

---

# 🚀 실행 방법

## 1. Python 가상환경 생성

프로젝트 폴더에서 다음 명령어를 실행합니다.

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

정상적으로 활성화되면 터미널 앞에 다음과 같이 표시됩니다.

```text
(.venv)
```

---

## 2. 필요한 라이브러리 설치

가상환경이 활성화된 상태에서 다음 명령어를 실행합니다.

```bash
pip install requests feedparser python-dotenv
```

설치한 라이브러리를 `requirements.txt`에 저장합니다.

```bash
pip freeze > requirements.txt
```

---

# 🔐 환경변수 설정

Discord Webhook URL은 코드에 직접 작성하지 않고 환경변수로 관리합니다.

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
DISCORD_WEBHOOK_URL=여기에_디스코드_웹훅_URL
```

`.env`에는 민감한 정보가 포함되므로 GitHub에 업로드하지 않습니다.

### `.gitignore`

```gitignore
.venv/
.env
__pycache__/
*.pyc
```

---

# 📰 뉴스 수집

NewsPicker는 Google News RSS를 이용하여 별도의 뉴스 크롤링 서버 없이 최신 기사를 가져옵니다.

현재 지원하는 뉴스 카테고리는 다음과 같습니다.

```python
RSS_FEEDS = {
    "🇰🇷 한국": "...",
    "💻 IT": "...",
    "🤖 AI": "...",
    "💰 경제": "...",
    "🌎 국제": "...",
    "🚨 속보": "..."
}
```

각 RSS Feed에서 최신 뉴스의 제목과 링크를 추출한 후 Discord로 전송합니다.

---

# 🚫 뉴스 중복 방지

NewsPicker는 동일한 뉴스가 반복해서 전송되는 것을 방지하기 위해 **뉴스 링크를 고유 ID로 사용**합니다.

```python
news_id = link
```

전송이 완료된 뉴스의 ID는 `sent_news.json`에 저장됩니다.

```text
sent_news.json
```

따라서 프로그램을 다시 실행하더라도 이전에 전송했던 뉴스는 다시 전송하지 않습니다.

### 동작 과정

```text
Google News RSS
       ↓
   뉴스 수집
       ↓
뉴스 제목 / 링크 추출
       ↓
sent_news.json 확인
       ↓
이미 전송한 뉴스인가?
    ↙          ↘
  YES           NO
   ↓             ↓
 건너뜀       Discord 전송
                 ↓
        sent_news.json 저장
```

---

# 💬 Discord 전송

수집된 뉴스는 Discord Webhook을 통해 Embed 형태로 전송됩니다.

뉴스 제목과 원문 링크를 함께 제공하여 사용자가 Discord에서 바로 기사를 확인할 수 있도록 구성했습니다.

```text
┌─────────────────────────────────────┐
│ 🇰🇷 한국 뉴스                        │
│                                     │
│ 새로운 뉴스가 등록되었습니다.         │
│                                     │
│ NewsPicker                          │
│ 🔗 뉴스 원문 보기                    │
└─────────────────────────────────────┘
```

---

# ⏱️ 자동 실행

NewsPicker는 Python 프로그램 자체에서 무한 반복 실행하기보다 **GitHub Actions의 Schedule을 이용해 주기적으로 실행**하도록 구성했습니다.

예를 들어 1시간마다 실행하려면:

```yaml
on:
  schedule:
    - cron: '0 * * * *'
```

4시간마다 실행하려면:

```yaml
on:
  schedule:
    - cron: '0 */4 * * *'
```

또한 `workflow_dispatch`를 사용하면 GitHub Actions에서 수동으로 실행할 수 있습니다.

전체적인 동작 과정은 다음과 같습니다.

```text
GitHub Actions
      ↓
설정된 주기에 따라 실행
      ↓
Python 환경 구성
      ↓
NewsPicker 실행
      ↓
Google News RSS 수집
      ↓
중복 뉴스 확인
      ↓
새로운 뉴스만 Discord 전송
      ↓
실행 종료
      ↓
다음 실행 시간까지 대기
      ↓
반복
```

---

# ☁️ GitHub Actions 배포

NewsPicker는 GitHub Actions를 이용하여 별도의 PC나 서버를 계속 켜두지 않아도 자동으로 실행할 수 있도록 구성했습니다.

## 1. GitHub Repository 생성

GitHub에서 새로운 Repository를 생성합니다.

```text
NewsPicker
```

---

## 2. 프로젝트 업로드

프로젝트 폴더에서 Git을 초기화합니다.

```bash
git init
```

파일을 추가합니다.

```bash
git add .
```

커밋합니다.

```bash
git commit -m "Initial commit"
```

GitHub Repository와 연결합니다.

```bash
git remote add origin <Repository URL>
```

이후 `main` 브랜치로 Push합니다.

```bash
git branch -M main
git push -u origin main
```

---

# ⚙️ GitHub Actions Workflow

프로젝트에 다음 폴더를 생성합니다.

```text
.github/
└── workflows/
    └── news.yml
```

`news.yml`에서 NewsPicker가 자동으로 실행되도록 설정합니다.

```yaml
name: NewsPicker

on:
  schedule:
    - cron: '0 */4 * * *'

  workflow_dispatch:

jobs:
  run-news-picker:

    runs-on: ubuntu-latest

    steps:

      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run NewsPicker
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: |
          python WebHookNewsPicker.py
```

---

# 🔑 GitHub Secrets 설정

로컬에서는 `.env`를 사용하지만 GitHub Actions에서는 **GitHub Secrets**를 사용합니다.

GitHub Repository에서 다음 경로로 이동합니다.

```text
Settings
  ↓
Secrets and variables
  ↓
Actions
  ↓
New repository secret
```

다음과 같이 Secret을 생성합니다.

```text
Name:
DISCORD_WEBHOOK_URL

Secret:
Discord Webhook URL
```

Python 코드에서는 환경변수를 통해 Webhook URL을 가져옵니다.

```python
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
```

이를 통해 실제 Discord Webhook URL이 GitHub Repository의 소스 코드에 직접 노출되지 않도록 관리합니다.

---

# 📦 requirements.txt

현재 프로젝트에서 사용하는 주요 패키지는 다음과 같습니다.

```text
requests
feedparser
python-dotenv
```

설치:

```bash
pip install -r requirements.txt
```

---

# 🧪 로컬 테스트

먼저 가상환경을 활성화합니다.

```bash
.venv\Scripts\activate
```

이후 NewsPicker를 실행합니다.

```bash
python WebHookNewsPicker.py
```

정상적으로 실행되면 뉴스 RSS를 확인하고 새로운 뉴스가 Discord로 전송됩니다.

예시:

```text
================================
 NewsPicker 뉴스봇 실행
================================

[00:00:00] 새 뉴스 5개 발견
[전송 완료] 뉴스 제목
[전송 완료] 뉴스 제목

뉴스 전송 완료
```

---

# 🧩 전체 동작 구조

```text
                    ┌─────────────────┐
                    │  Google News    │
                    │      RSS        │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    NewsPicker   │
                    │     Python      │
                    └────────┬────────┘
                             │
                    뉴스 제목 / 링크 추출
                             │
                             ▼
                    ┌─────────────────┐
                    │ 중복 뉴스 확인   │
                    │ sent_news.json  │
                    └────────┬────────┘
                             │
                      새로운 뉴스만
                             │
                             ▼
                    ┌─────────────────┐
                    │ Discord Webhook │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Discord Channel │
                    └─────────────────┘
```

---

# 🔒 보안 관리

NewsPicker에서는 Discord Webhook URL과 같은 민감한 정보를 소스 코드와 분리하여 관리합니다.

### 로컬 환경

```text
.env
   ↓
python-dotenv
   ↓
DISCORD_WEBHOOK_URL
```

### GitHub Actions

```text
GitHub Secrets
      ↓
DISCORD_WEBHOOK_URL
      ↓
GitHub Actions
      ↓
Python 실행
```

`.env` 파일은 반드시 `.gitignore`에 등록하여 Repository에 업로드되지 않도록 합니다.

---

# 📌 프로젝트 특징

### 1. 서버 없이 자동 운영

별도의 서버를 직접 구매하거나 PC를 계속 켜두지 않고 GitHub Actions를 이용해 정해진 시간마다 프로그램을 실행합니다.

### 2. RSS 기반 뉴스 수집

뉴스 사이트를 직접 크롤링하는 대신 Google News RSS를 활용하여 비교적 간단한 구조로 최신 뉴스를 수집합니다.

### 3. 중복 뉴스 방지

`sent_news.json`에 전송한 뉴스 링크를 저장하여 같은 뉴스가 반복해서 Discord에 전송되는 것을 방지합니다.

### 4. 보안 정보 분리

Discord Webhook URL을 `.env`와 GitHub Secrets로 분리하여 코드에 민감한 정보가 노출되지 않도록 관리합니다.

### 5. 자동화된 배포 및 실행

GitHub Actions를 활용하여 코드가 Repository에 배포된 이후에도 별도의 서버 관리 없이 정해진 주기에 따라 NewsPicker를 실행할 수 있습니다.

---

# 🔮 향후 개선 계획

* [ ] 뉴스 요약 기능 추가
* [ ] 카테고리별 뉴스 전송 채널 설정
* [ ] Discord Slash Command 추가
* [ ] 사용자별 관심 카테고리 설정
* [ ] 뉴스 중요도 및 인기도 기반 필터링
* [ ] 중복 뉴스 판별 로직 개선
* [ ] 뉴스 이미지 자동 표시
* [ ] 데이터베이스 기반 뉴스 기록 관리
* [ ] 뉴스 검색 기능 추가
* [ ] AI 기반 뉴스 요약 및 분류

---

# 📚 프로젝트를 통해 배운 점

NewsPicker를 제작하면서 단순히 Python으로 기능을 구현하는 것뿐만 아니라, 실제 서비스가 지속적으로 동작하기 위해 필요한 **환경변수 관리, 외부 API 활용, Git/GitHub, 자동화 및 배포 과정**까지 경험할 수 있었습니다.

특히 로컬 환경에서 정상적으로 동작하는 프로그램을 GitHub Actions 환경으로 옮기면서 실행 환경과 환경변수의 차이를 이해하고, 민감한 정보를 GitHub Secrets로 분리하는 방법을 익혔습니다.

또한 Google News RSS를 활용하면서 별도의 서버나 복잡한 크롤링 시스템 없이도 외부 데이터를 수집하고 이를 Discord Webhook과 연결하여 하나의 자동화된 서비스로 만드는 과정을 경험했습니다.


# 어려웠던 점 
- 봇으로 만들었다가 배포할 돈도 카드도 서버지원도 없어서 막혔습니다. 다른 방법을 찾아보다가 웹후크라는 기능을 통해 파이프라인을 구축하는 방법을 알게 되었습니다. 따라서 웹후크가 더 효율적이라는 것을 깨닫고 웹후크를 이용해 개발하였습니다. 총 개발 시간은 약 4시간 정도 걸렸습니다. 또한 폴더구조를 이상하게해놓고 개발해서 최신 파일이 반영 안되는 문제를 빨리 눈치채지 못해 아쉬웠습니다. 
- 담부턴 웹후크와 깃허브 action을 적극적으로 이용해보는 걸로...

---

# 👩‍💻 Author

**RAMBUS**

Python · Web · UX/UI Design · Automation

> 사용자의 문제를 발견하고, 기술과 디자인을 활용해 더 나은 경험으로 해결하는 것을 목표로 합니다. 최고의 UX 전문가가 되어보자. 
