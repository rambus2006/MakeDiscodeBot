import os
import time
import re
import html
import requests
import feedparser
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

# 확인 주기: 60초
CHECK_INTERVAL = 60

# 한 번에 보낼 최대 뉴스 개수
MAX_NEWS = 5

# 이미 보낸 뉴스 저장
sent_news = set()


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
    print(" NewsPick 실시간 뉴스봇 시작")
    print("================================")

    if not WEBHOOK_URL:

        print("ERROR: DISCORD_WEBHOOK_URL이 없습니다.")

        return

    while True:

        try:

            news_list = get_news()

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"새 뉴스 {len(news_list)}개 발견"
            )

            # 너무 많은 뉴스가 한번에 올라가는 것을 방지
            for news in news_list[:MAX_NEWS]:

                send_to_discord(
                    title=news["title"],
                    description=news["summary"],
                    url=news["link"],
                    category=news["category"]
                )

                sent_news.add(news["id"])

                # 너무 빠르게 전송하지 않기
                time.sleep(1)

            # 메모리 관리
            if len(sent_news) > 1000:

                sent_news.clear()

            print(
                f"다음 확인까지 {CHECK_INTERVAL}초 대기..."
            )

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:

            print("\n뉴스봇 종료")
            break

        except Exception as e:

            print(f"[ERROR] {e}")

            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()