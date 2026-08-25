"""
NewsPick - Discord News Bot
---------------------------
/news 명령어로 원하는 영어 뉴스 종류를 선택해서 가져오는 디스코드 뉴스 봇

뉴스 종류:
1. 🌎 영어 일반 뉴스
2. 💻 영어 테크 뉴스
3. 💰 영어 금융 뉴스

자동 뉴스:
- 60분마다 영어 일반 / 테크 / 금융 뉴스를 자동으로 가져와
  지정 채널에 게시
"""

import os
import json
import asyncio

from datetime import datetime, timezone

import aiohttp
import discord

from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv


# ============================================================
# 환경변수
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))


# ============================================================
# 설정
# ============================================================

CHECK_INTERVAL_MINUTES = 60

SEEN_FILE = "seen_urls.json"
MAX_SEEN = 500


# ============================================================
# Discord 설정
# ============================================================

intents = discord.Intents.default()

client = discord.Client(intents=intents)

tree = app_commands.CommandTree(client)


# ============================================================
# 이미 게시한 기사 관리
# ============================================================

def load_seen() -> set:
    """
    이미 게시한 기사 URL을 불러온다.
    """

    if os.path.exists(SEEN_FILE):

        try:

            with open(
                SEEN_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return set(json.load(f))

        except Exception as e:

            print(
                f"[seen_urls 로드 오류] {e}"
            )

            return set()

    return set()


def save_seen(seen: set):
    """
    최근 MAX_SEEN개의 URL만 저장한다.
    """

    trimmed = list(seen)[-MAX_SEEN:]

    with open(
        SEEN_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            trimmed,
            f,
            ensure_ascii=False,
            indent=2
        )


seen_urls = load_seen()


# ============================================================
# NewsAPI
# ============================================================

async def fetch_newsapi(
    session: aiohttp.ClientSession,
    params: dict,
    page_size: int = 5
):
    """
    NewsAPI에서 영어 뉴스를 가져온다.
    """

    url = "https://newsapi.org/v2/top-headlines"

    query = {
        "apiKey": NEWSAPI_KEY,
        "pageSize": page_size,
        **params
    }

    try:

        async with session.get(
            url,
            params=query,
            timeout=15
        ) as resp:

            if resp.status != 200:

                text = await resp.text()

                print(
                    f"[NewsAPI 오류] "
                    f"status={resp.status} "
                    f"body={text}"
                )

                return []

            data = await resp.json()

            return data.get(
                "articles",
                []
            )

    except asyncio.TimeoutError:

        print(
            "[NewsAPI 오류] 요청 시간이 초과되었습니다."
        )

        return []

    except aiohttp.ClientError as e:

        print(
            f"[NewsAPI 연결 오류] {e}"
        )

        return []

    except Exception as e:

        print(
            f"[NewsAPI 요청 오류] {e}"
        )

        return []


# ============================================================
# Embed 생성
# ============================================================

def build_news_embed(
    article: dict,
    label: str
) -> discord.Embed:

    title = (
        article.get("title")
        or "(제목 없음)"
    )

    description = (
        article.get("description")
        or ""
    )

    url = (
        article.get("url")
        or ""
    )

    source = (
        article.get("source")
        or {}
    ).get(
        "name",
        "알 수 없음"
    )

    published_at = (
        article.get("publishedAt")
        or ""
    )

    # 설명이 너무 길면 자르기
    if len(description) > 300:

        description = (
            description[:300]
            + "..."
        )

    embed = discord.Embed(

        title=title[:256],

        url=url,

        description=description,

        color=discord.Color.blue(),

        timestamp=datetime.now(timezone.utc)
    )

    # 뉴스 종류 + 언론사
    embed.set_author(
        name=f"[{label}] {source}"
    )

    # 기사 이미지
    image_url = article.get(
        "urlToImage"
    )

    if image_url:

        embed.set_thumbnail(
            url=image_url
        )

    # 발행 시간
    if published_at:

        embed.set_footer(
            text=f"발행: {published_at}"
        )

    return embed


# ============================================================
# 영어 뉴스 가져오기
# ============================================================

async def post_english_news(
    channel: discord.abc.Messageable
) -> int:

    posted = 0

    queries = [

        {
            "label": "영어 · 일반",
            "params": {
                "category": "general",
                "language": "en"
            }
        },

        {
            "label": "영어 · 테크",
            "params": {
                "category": "technology",
                "language": "en"
            }
        },

        {
            "label": "영어 · 금융",
            "params": {
                "category": "business",
                "language": "en"
            }
        }

    ]

    async with aiohttp.ClientSession() as session:

        for query in queries:

            articles = await fetch_newsapi(
                session,
                query["params"],
                page_size=5
            )

            for article in articles:

                url = article.get(
                    "url"
                )

                # URL이 없는 기사 제외
                if not url:
                    continue

                # 이미 게시한 기사 제외
                if url in seen_urls:
                    continue

                # 게시 전에 seen에 추가
                seen_urls.add(url)

                embed = build_news_embed(
                    article,
                    query["label"]
                )

                try:

                    await channel.send(
                        embed=embed
                    )

                    posted += 1

                    # 너무 빠르게 보내지 않도록 대기
                    await asyncio.sleep(1)

                except discord.HTTPException as e:

                    print(
                        f"[Discord 전송 오류] {e}"
                    )

    save_seen(seen_urls)

    return posted


# ============================================================
# 특정 뉴스 카테고리 가져오기
# ============================================================

async def post_category_news(
    channel: discord.abc.Messageable,
    label: str,
    category: str
) -> int:

    posted = 0

    async with aiohttp.ClientSession() as session:

        articles = await fetch_newsapi(

            session,

            {
                "category": category,
                "language": "en"
            },

            page_size=10
        )

        for article in articles:

            url = article.get(
                "url"
            )

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            embed = build_news_embed(
                article,
                label
            )

            try:

                await channel.send(
                    embed=embed
                )

                posted += 1

                await asyncio.sleep(1)

            except discord.HTTPException as e:

                print(
                    f"[Discord 전송 오류] {e}"
                )

    save_seen(seen_urls)

    return posted


# ============================================================
# 뉴스 선택 버튼
# ============================================================

class NewsView(discord.ui.View):

    def __init__(self):

        # 5분 동안 버튼 사용 가능
        super().__init__(
            timeout=300
        )


    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        return True


    # --------------------------------------------------------
    # 일반 뉴스
    # --------------------------------------------------------

    @discord.ui.button(
        label="영어 뉴스",
        emoji="🌎",
        style=discord.ButtonStyle.primary,
        custom_id="news_general"
    )
    async def general_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            thinking=True
        )

        channel = interaction.channel

        if channel is None:

            await interaction.followup.send(
                "채널을 확인할 수 없습니다."
            )

            return

        count = await post_category_news(

            channel,

            "영어 · 일반",

            "general"
        )

        if count == 0:

            await interaction.followup.send(
                "🌎 새로운 영어 뉴스가 없어요."
            )

        else:

            await interaction.followup.send(
                f"🌎 영어 뉴스 {count}건을 가져왔어요!"
            )


    # --------------------------------------------------------
    # 테크 뉴스
    # --------------------------------------------------------

    @discord.ui.button(
        label="테크 뉴스",
        emoji="💻",
        style=discord.ButtonStyle.success,
        custom_id="news_technology"
    )
    async def technology_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            thinking=True
        )

        channel = interaction.channel

        if channel is None:

            await interaction.followup.send(
                "채널을 확인할 수 없습니다."
            )

            return

        count = await post_category_news(

            channel,

            "영어 · 테크",

            "technology"
        )

        if count == 0:

            await interaction.followup.send(
                "💻 새로운 테크 뉴스가 없어요."
            )

        else:

            await interaction.followup.send(
                f"💻 테크 뉴스 {count}건을 가져왔어요!"
            )


    # --------------------------------------------------------
    # 금융 뉴스
    # --------------------------------------------------------

    @discord.ui.button(
        label="금융 뉴스",
        emoji="💰",
        style=discord.ButtonStyle.secondary,
        custom_id="news_business"
    )
    async def business_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            thinking=True
        )

        channel = interaction.channel

        if channel is None:

            await interaction.followup.send(
                "채널을 확인할 수 없습니다."
            )

            return

        count = await post_category_news(

            channel,

            "영어 · 금융",

            "business"
        )

        if count == 0:

            await interaction.followup.send(
                "💰 새로운 금융 뉴스가 없어요."
            )

        else:

            await interaction.followup.send(
                f"💰 금융 뉴스 {count}건을 가져왔어요!"
            )


# ============================================================
# /news 명령어
# ============================================================

@tree.command(
    name="news",
    description="뉴스 종류를 선택합니다"
)
async def news_command(
    interaction: discord.Interaction
):

    embed = discord.Embed(

        title="📰 NewsPick",

        description=(

            "원하는 뉴스 종류를 선택해주세요.\n\n"

            "🌎 **영어 뉴스**\n"
            "해외 주요 뉴스를 영어 원문으로 가져옵니다.\n\n"

            "💻 **테크 뉴스**\n"
            "해외 IT·기술 관련 뉴스를 가져옵니다.\n\n"

            "💰 **금융 뉴스**\n"
            "해외 경제·금융 관련 뉴스를 가져옵니다."
        ),

        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="NewsPick • 원하는 뉴스를 버튼으로 선택하세요"
    )

    await interaction.response.send_message(

        embed=embed,

        view=NewsView()
    )


# ============================================================
# 자동 뉴스 루프
# ============================================================

@tasks.loop(
    minutes=CHECK_INTERVAL_MINUTES
)
async def news_loop():

    channel = client.get_channel(
        CHANNEL_ID
    )

    # 캐시에 없으면 직접 가져오기
    if channel is None:

        try:

            channel = await client.fetch_channel(
                CHANNEL_ID
            )

        except discord.NotFound:

            print(
                "[자동 뉴스] 채널 ID가 존재하지 않습니다."
            )

            return

        except discord.Forbidden:

            print(
                "[자동 뉴스] "
                "봇에게 해당 채널을 볼 권한이 없습니다."
            )

            return

        except discord.HTTPException as e:

            print(
                f"[자동 뉴스] 채널 조회 중 오류: {e}"
            )

            return

    try:

        count = await post_english_news(
            channel
        )

        print(
            f"[{datetime.now()}] "
            f"영어 뉴스 {count}건 게시"
        )

    except Exception as e:

        print(
            f"[자동 뉴스 오류] {e}"
        )


# ============================================================
# 자동 뉴스 시작 전 대기
# ============================================================

@news_loop.before_loop
async def before_news_loop():

    await client.wait_until_ready()


# ============================================================
# 봇 로그인 완료
# ============================================================

@client.event
async def on_ready():

    await tree.sync()

    print(
        f"{client.user} 로그인 완료"
    )

    print(
        "명령어: "
        "/news → 영어 뉴스 / 테크 뉴스 / 금융 뉴스"
    )

    if not news_loop.is_running():

        news_loop.start()


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    missing = []

    if not DISCORD_TOKEN:

        missing.append(
            "DISCORD_TOKEN"
        )

    if not NEWSAPI_KEY:

        missing.append(
            "NEWSAPI_KEY"
        )

    if not CHANNEL_ID:

        missing.append(
            "CHANNEL_ID"
        )

    if missing:

        raise SystemExit(

            "다음 환경변수를 설정하세요: "

            + ", ".join(missing)
        )

    client.run(
        DISCORD_TOKEN
    )