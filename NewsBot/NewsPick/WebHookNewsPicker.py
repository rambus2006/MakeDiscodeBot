import os
import time
import re
import html
import requests
import json
import feedparser
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


# 한 번에 보낼 최대 뉴스 개수
MAX_NEWS = 5

# 이미 보낸 뉴스 저장
SENT_NEWS_FILE = "sent_news.json"


def load_sent_news():

    if not os.path.exists(SENT_NEWS_FILE):
        return set()

    try:
        with open(SENT_NEWS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))

    except Exception:
        return set()


def save_sent_news(sent_news):

    with open(SENT_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_news), f, ensure_ascii=False, indent=2)
sent_news = load_sent_news()



# --------------------------------
# 뉴스 RSS 주소
# --------------------------------

RSS_FEEDS = {
    "🇰🇷 한국": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",

    "💻 IT": "https://news.google.com/rss/search?q=IT&hl=ko&gl=KR&ceid=KR:ko",

    "🤖 AI": "https://news.google.com/rss/search?q=AI&hl=ko&gl=KR&ceid=KR:ko",

    "💰 경제": "https://news.google.com/rss/search?q=경제&hl=ko&gl=KR&ceid=KR:ko",

    "🌎 국제": "https://news.google.com/rss/search?q=국제&hl=ko&gl=KR&ceid=KR:ko",

    "🚨 속보": "https://news.google.com/rss/search?q=속보&hl=ko&gl=KR&ceid=KR:ko",
}


# --------------------------------
# Discord Webhook 전송
# --------------------------------

def send_to_discord(title, description, url, category):

    data = {
        "username": "NewsPick 📰",

        "embeds": [
            {
                "title": f"{category} {title}",
                "url": url,
                "description": description[:4000],

                "color": 3447003,

                "footer": {
                    "text": "NewsPick • 실시간 뉴스"
                },

                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }

    response = requests.post(
        WEBHOOK_URL,
        json=data,
        timeout=10
    )

    if response.status_code in (200, 204):
        print(f"[전송 완료] {title}")

    else:
        print(
            f"[Discord 오류] "
            f"{response.status_code} "
            f"{response.text}"
        )


# --------------------------------
# 뉴스 가져오기
# --------------------------------
def clean_html(text):
    """HTML 태그를 제거하고 일반 텍스트로 변환"""

    if not text:
        return ""

    # HTML 엔티티 변환
    text = html.unescape(text)

    # HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)

    # 공백 정리
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def get_news():

    all_news = []

    for category, rss_url in RSS_FEEDS.items():

        try:

            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:10]:

                title = entry.get("title", "제목 없음")
                link = entry.get("link", "")

                if not link:
                    continue

                # 제목에서 언론사 제거
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]

                news_id = link

                if news_id in sent_news:
                    continue

                all_news.append({
                    "id": news_id,
                    "category": category,
                    "title": title,
                    "link": link,

                    # RSS summary를 절대 사용하지 않음
                    "summary": "새로운 뉴스가 등록되었습니다."
                })

        except Exception as e:

            print(f"[RSS 오류] {category}: {e}")

    return all_news

# --------------------------------
# 메인 루프
# --------------------------------
def main():

    print("================================")
    print(" NewsPick 뉴스봇 실행")
    print("================================")

    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL이 없습니다.")
        return

    try:
        news_list = get_news()

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"새 뉴스 {len(news_list)}개 발견"
        )

        for news in news_list[:MAX_NEWS]:

            send_to_discord(
                title=news["title"],
                description=news["summary"],
                url=news["link"],
                category=news["category"]
            )

            sent_news.add(news["id"])
            save_sent_news(sent_news)

            # 뉴스 사이에 1초 간격
            time.sleep(1)

        print("뉴스 전송 완료")


    except Exception as e:

        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()