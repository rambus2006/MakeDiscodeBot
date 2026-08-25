# 디스코드 뉴스 봇

NewsAPI.org에서 최신 뉴스를 가져와 디스코드 채널에 자동으로 올려주는 봇입니다.
1시간마다 새 기사를 체크하고, `/news` 명령어로 즉시 조회도 가능합니다.

## 1. 사전 준비

### 1) 디스코드 봇 생성 및 토큰 발급
1. https://discord.com/developers/applications 접속 → New Application
2. 왼쪽 메뉴 **Bot** → Reset Token 눌러서 토큰 복사 (`DISCORD_TOKEN`)
3. **Bot** 메뉴에서 `MESSAGE CONTENT INTENT`는 필요 없음 (임베드만 보내므로 꺼둬도 됨)
4. **OAuth2 → URL Generator**에서 scope: `bot`, `applications.commands` 체크,
   권한: `Send Messages`, `Embed Links` 체크 → 생성된 URL로 서버에 봇 초대

### 2) 채널 ID 확인
디스코드 설정 → 고급 → 개발자 모드 ON → 뉴스 올릴 채널 우클릭 → "ID 복사" (`CHANNEL_ID`)

### 3) NewsAPI 키 발급
https://newsapi.org/register 에서 무료 가입 후 API 키 발급 (`NEWSAPI_KEY`)
무료 티어는 하루 100회 요청 제한이 있어서 체크 주기를 너무 짧게 하면 금방 소진됩니다.

## 2. 로컬 테스트

```bash
pip install -r requirements.txt
cp .env.example .env   # 값 채워넣기
python news_bot.py
```

## 3. Railway 배포

1. GitHub 저장소에 이 폴더 push
2. https://railway.app 에서 New Project → Deploy from GitHub repo 선택
3. Variables 탭에서 `DISCORD_TOKEN`, `NEWSAPI_KEY`, `CHANNEL_ID` 등록
4. Railway가 `Procfile`을 자동 인식해서 `python news_bot.py`로 실행됨
5. Deploy 후 로그에서 "로그인 완료" 메시지 확인

## 4. Replit 배포 (대안)

1. Replit에서 이 폴더 업로드 (Python 템플릿)
2. Secrets 탭에서 위 3개 환경변수 등록
3. Run 버튼으로 실행 (단, Replit 무료 플랜은 잠들 수 있으니 UptimeRobot 같은 걸로 핑을 주거나 Railway를 추천)

## 5. 커스터마이징

- `news_bot.py`의 `QUERIES` 리스트에서 카테고리/키워드 추가·수정 가능
  (예: `{"label": "한국", "params": {"country": "kr"}}` — 단, NewsAPI 무료 플랜은 country 필터가 제한적일 수 있음)
- `CHECK_INTERVAL_MINUTES` 값으로 체크 주기 조절
- 이미 올린 기사는 `seen_urls.json`에 저장되어 중복 게시 방지 (Railway 재배포 시 파일 시스템이 초기화될 수 있으니, 완전히 영속적인 저장이 필요하면 추후 DB 연동 고려)
