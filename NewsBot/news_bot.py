"""
디스코드 뉴스 봇
------------------
NewsAPI.org의 top-headlines 엔드포인트에서 뉴스를 가져와,
지정된 디스코드 채널에 헤드라인 + 짧은 설명 + 링크를 임베드로 게시한다.

동작 방식:
1) 봇이 켜지면(on_ready) 슬래시 커맨드를 동기화하고, 백그라운드 루프(news_loop)를 시작한다.
2) news_loop는 CHECK_INTERVAL_MINUTES 간격으로 자동 실행되어 새 기사를 찾아 올린다.
3) 사용자는 언제든 /news 커맨드로 즉시 최신 뉴스를 강제로 가져올 수 있다.
4) 이미 올린 기사(URL 기준)는 seen_urls.json에 저장해두고, 다음에 다시 안 올리도록 걸러낸다.
"""

import os
import json
import asyncio
from datetime import datetime, timezone

import aiohttp                       # 비동기 HTTP 요청 (NewsAPI 호출용)
import discord                       # 디스코드 봇 SDK 본체
from discord import app_commands     # 슬래시 커맨드(/news) 등록용
from discord.ext import tasks        # 일정 주기로 반복 실행되는 백그라운드 루프용
from dotenv import load_dotenv       # .env 파일에서 환경변수를 읽어오기 위함

# .env 파일에 적어둔 DISCORD_TOKEN, NEWSAPI_KEY, CHANNEL_ID 값을
# os.environ에 로드한다. (배포 환경에서는 .env 대신 플랫폼의
# 환경변수 설정(Railway Variables 등)을 그대로 써도 동일하게 동작함)
load_dotenv()

# ── 환경변수 ────────────────────────────────────────────────
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")          # 디스코드 봇 로그인 토큰
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")               # NewsAPI.org 발급 API 키
CHANNEL_ID = int(os.getenv("CHANNEL_ID","0"))      # 뉴스를 올릴 채널의 ID (정수)


# ── 설정값 ──────────────────────────────────────────────────
# 몇 분 간격으로 새 뉴스를 체크할지. NewsAPI 무료 티어는 하루 100회 요청
# 제한이 있으므로, 너무 짧게 잡으면 (QUERIES 개수 * 하루 체크 횟수)가
# 100을 넘지 않는지 계산해보고 값을 정할 것.
CHECK_INTERVAL_MINUTES = 60

# 조회할 뉴스 카테고리/키워드 목록.
# label: 디스코드에 표시될 태그 이름 (예: "[속보] BBC News")
# params: NewsAPI top-headlines 엔드포인트에 그대로 전달되는 쿼리 파라미터
#         (category, language, country, q 등 NewsAPI 문서의 파라미터를 사용 가능)
# 리스트 항목 하나당 매 체크 주기마다 API 요청이 1회씩 발생한다.
QUERIES = [
    {"label": "속보", "params": {"category": "general", "language": "en"}},
    {"label": "테크", "params": {"category": "technology", "language": "en"}},
    {"label": "금융", "params": {"category": "business", "language": "en"}},
    {"label": "정부", "params": {"q": "government OR politics OR policy", "language": "en"}},
]

SEEN_FILE = "seen_urls.json"   # 이미 게시한 기사 URL 목록을 저장하는 파일
MAX_SEEN = 500                 # seen_urls가 무한정 커지지 않도록 최근 500개만 유지

# ── 디스코드 클라이언트 설정 ───────────────────────────────────
# Intents: 봇이 받아볼 이벤트 범위를 지정. 이 봇은 메시지 내용을 읽을 필요
# 없이 "보내기"만 하므로 기본 intents로 충분 (MESSAGE CONTENT INTENT 불필요).
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# 슬래시 커맨드(/news 등)를 등록하고 관리하는 커맨드 트리
tree = app_commands.CommandTree(client)


def load_seen() -> set:
    """
    seen_urls.json 파일을 읽어서 이미 게시한 기사 URL들의 집합(set)을 반환.
    - 파일이 없으면 빈 집합을 반환 (봇을 처음 실행하는 경우).
    - 파일이 손상되어 JSON 파싱에 실패해도 빈 집합을 반환해서 봇이 죽지 않게 함.
    """
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_seen(seen: set):
    """
    현재까지 게시한 URL 집합을 파일에 저장.
    set은 저장 순서가 보장되지 않으므로, list로 바꾼 뒤 뒤쪽 MAX_SEEN개만
    잘라서 저장한다 (파일이 계속 커지는 것을 방지하기 위함).
    주의: Railway 같은 일부 무료 호스팅은 재배포 시 파일 시스템이 초기화될
    수 있어서, 이 경우 seen_urls.json도 사라지고 예전 기사가 다시 올라갈 수 있음.
    """
    trimmed = list(seen)[-MAX_SEEN:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False)


# 모듈이 로드될 때 한 번 파일에서 읽어와 메모리에 올려둔다.
# 이후 post_new_articles()에서 이 전역 변수를 갱신하고, 다시 파일에 저장한다.
seen_urls = load_seen()


# 뉴스 get 해오는 부분 (비동기처리)
async def fetch_news(session: aiohttp.ClientSession, params: dict, page_size: int = 5):
    """
    NewsAPI.org의 top-headlines 엔드포인트를 호출해서 기사 목록을 가져온다.

    Args:
        session: 재사용할 aiohttp 세션 (매 호출마다 새로 만들지 않기 위해 인자로 받음)
        params: category/language/country/q 등 NewsAPI에 전달할 추가 쿼리 파라미터
        page_size: 한 번에 가져올 기사 개수 (NewsAPI 기본 최대값은 100)

    Returns:
        기사 정보 딕셔너리들의 리스트. 요청 실패 시 빈 리스트.
        각 기사 딕셔너리는 보통 title, description, url, urlToImage,
        publishedAt, source(dict) 등의 키를 가짐.
    """
    url = "https://newsapi.org/v2/top-headlines"
    query = {
        "apiKey": NEWSAPI_KEY,   # 인증 키
        "pageSize": page_size,
        **params,                 # QUERIES에서 넘어온 category/language 등을 병합
    }
    async with session.get(url, params=query, timeout=15) as resp:
        if resp.status != 200:
            # 200이 아니면 (401 키 오류, 429 요청 제한 초과 등) 에러 내용을
            # 콘솔에 로그로 남기고, 봇이 죽지 않도록 빈 리스트를 반환한다.
            text = await resp.text()
            print(f"[NewsAPI 오류] status={resp.status} body={text}")
            return []
        data = await resp.json()
        return data.get("articles", [])


def build_embed(article: dict, label: str) -> discord.Embed:
    """
    NewsAPI 기사 딕셔너리 하나를 디스코드 Embed 객체로 변환한다.
    Embed는 디스코드에서 카드 형태로 예쁘게 렌더링되는 메시지 형식.

    Args:
        article: fetch_news()가 반환한 기사 딕셔너리 1개
        label: 이 기사가 어느 QUERIES 항목에서 왔는지 표시할 태그 (예: "속보")
    """
    # NewsAPI 응답 필드가 null일 수도 있으므로 or ""/기본값으로 방어.
    title = article.get("title") or "(제목 없음)"
    description = article.get("description") or ""
    url = article.get("url") or ""
    source = (article.get("source") or {}).get("name", "알 수 없음")
    published_at = article.get("publishedAt", "")

    embed = discord.Embed(
        title=title[:256],          # 디스코드 Embed 제목은 최대 256자 제한
        url=url,                     # 제목 클릭 시 이동할 기사 링크
        # 설명이 300자를 넘으면 잘라내고 "..." 붙임 (Embed 설명 자체는
        # 최대 4096자까지 허용되지만, 채팅창에서 너무 길어지지 않도록 제한)
        description=(description[:300] + "...") if len(description) > 300 else description,
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),  # Embed 우측 하단에 표시되는 시각
    )
    # 작성자 필드를 "[라벨] 출처" 형태로 표시 (예: "[테크] The Verge")
    embed.set_author(name=f"[{label}] {source}")
    if article.get("urlToImage"):
        # 기사에 썸네일 이미지가 있으면 Embed 우측에 작게 표시
        embed.set_thumbnail(url=article["urlToImage"])
    if published_at:
        embed.set_footer(text=f"발행: {published_at}")
    return embed


async def post_new_articles(channel: discord.abc.Messageable, manual: bool = False) -> int:
    """
    QUERIES에 정의된 모든 쿼리에 대해 뉴스를 조회하고,
    아직 게시하지 않은(seen_urls에 없는) 기사만 골라 채널에 전송한다.

    Args:
        channel: 메시지를 보낼 디스코드 채널/스레드 객체
        manual: /news 커맨드로 수동 호출된 것인지 여부
                (현재는 로직 분기에 쓰이진 않고, 추후 로깅/구분용으로 확장 가능)

    Returns:
        새로 게시한 기사 개수
    """
    global seen_urls
    posted = 0

    # aiohttp 세션은 요청마다 새로 만들지 않고 하나를 재사용하는 것이 효율적.
    # 'async with'가 끝나면 세션이 자동으로 정리(close)된다.
    async with aiohttp.ClientSession() as session:
        for q in QUERIES:
            articles = await fetch_news(session, q["params"])
            for article in articles:
                url = article.get("url")
                # url이 없거나 이미 게시한 적 있는 기사는 건너뛴다 (중복 방지 핵심 로직).
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                await channel.send(embed=build_embed(article, q["label"]))
                posted += 1
                # 디스코드 API 레이트리밋(짧은 시간에 너무 많은 메시지를 보내면
                # 차단당함)을 피하기 위해 메시지 사이에 1초씩 쉬어준다.
                await asyncio.sleep(1)

    # 이번 호출에서 새로 추가된 URL들을 포함해 파일에 다시 저장.
    save_seen(seen_urls)
    return posted


# ── 자동 반복 작업 ──────────────────────────────────────────
# @tasks.loop는 discord.py가 제공하는 백그라운드 스케줄러 데코레이터.
# minutes=CHECK_INTERVAL_MINUTES 간격으로 news_loop() 함수를 계속 반복 호출한다.
@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def news_loop():
    """CHECK_INTERVAL_MINUTES마다 자동으로 실행되어 새 뉴스를 게시하는 함수."""
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        # CHANNEL_ID가 잘못됐거나, 봇이 해당 채널이 있는 서버에 초대되지
        # 않은 경우 여기 걸림.
        print("채널을 찾을 수 없습니다. CHANNEL_ID를 확인하세요.")
        return
    count = await post_new_articles(channel)
    print(f"[{datetime.now()}] 새 기사 {count}건 게시")


@news_loop.before_loop
async def before_news_loop():
    """
    news_loop가 시작되기 전에 반드시 실행되는 훅.
    client.wait_until_ready()로 봇의 디스코드 연결이 완전히 준비될 때까지
    대기해서, 연결되기 전에 get_channel()을 호출해 None이 반환되는 상황을 막는다.
    """
    await client.wait_until_ready()


# ── 슬래시 커맨드 ───────────────────────────────────────────
@tree.command(name="news", description="지금 바로 최신 뉴스를 가져옵니다")
async def news_command(interaction: discord.Interaction):
    """
    사용자가 디스코드에서 '/news'를 입력했을 때 실행되는 슬래시 커맨드.
    news_loop의 자동 주기를 기다리지 않고 즉시 뉴스를 가져와 올린다.
    """
    # NewsAPI 호출 + 여러 메시지 전송에 시간이 걸릴 수 있으므로,
    # 먼저 defer()로 "생각 중..." 상태를 보여줘서 3초 응답 제한을 피한다.
    await interaction.response.defer(thinking=True)
    channel = interaction.channel
    count = await post_new_articles(channel, manual=True)
    if count == 0:
        await interaction.followup.send("새로 올릴 기사가 없어요 (이미 다 올렸거나 결과 없음).")
    else:
        await interaction.followup.send(f"새 기사 {count}건 게시 완료!")


# ── 봇 생명주기 이벤트 ──────────────────────────────────────
@client.event
async def on_ready():
    """
    봇이 디스코드에 성공적으로 로그인하고 연결이 완료되면 자동 호출되는 이벤트.
    - tree.sync(): 로컬에 정의된 슬래시 커맨드(/news)를 디스코드 서버에 등록/갱신.
      (커맨드를 새로 추가하거나 수정했을 때 디스코드 UI에 반영되려면 필요)
    - news_loop.start(): 아직 시작 안 됐으면 자동 뉴스 체크 루프를 시작.
      is_running() 체크는 재연결(reconnect) 시 루프가 중복으로 시작되는 것을 방지.
    """
    await tree.sync()
    print(f"{client.user} 로그인 완료")
    if not news_loop.is_running():
        news_loop.start()


# ── 엔트리 포인트 ───────────────────────────────────────────
if __name__ == "__main__":
    # 필수 환경변수 중 하나라도 비어있으면, 알 수 없는 에러 대신
    # 바로 무엇이 문제인지 알려주고 종료한다.
    if not DISCORD_TOKEN or not NEWSAPI_KEY or not CHANNEL_ID:
        raise SystemExit("DISCORD_TOKEN, NEWSAPI_KEY, CHANNEL_ID를 .env에 설정하세요.")
    # 봇 실행 (내부적으로 이벤트 루프를 만들고 디스코드에 로그인해서 대기 상태로 들어감)
    client.run(DISCORD_TOKEN)