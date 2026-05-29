"""
메인 실행 진입점 (예스24 + 알라딘).
맥에서 매일 실행되어 SQLite에 적재한다.

교보문고는 JS 렌더링 방식이라 현재 제외.
나중에 scraper_kyobo.py(Selenium 버전)를 추가하면
아래 STORES 리스트에 한 줄만 더하면 됩니다.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from db import init_db, insert_books
from scraper_yes24 import fetch_top100 as fetch_yes24
from scraper_aladin import fetch_top100 as fetch_aladin
from scraper_kyobo import fetch_top100 as fetch_kyobo

STORES = [
    ("예스24", fetch_yes24),
    ("알라딘", fetch_aladin),
    ("교보문고", fetch_kyobo),
]


def run():
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")
    print(f"=== Bestseller collection started: {now} ===\n")

    init_db()
    total_inserted = 0

    for name, fetcher in STORES:
        print(f"\n▶ {name} 수집 중...")
        try:
            books = fetcher()
            count = insert_books(books)
            total_inserted += count
            print(f"  → {len(books)}권 수집, {count}권 신규 적재")
        except Exception as e:
            print(f"  ❌ {name} 실패: {e}")

    print(f"\n=== Done. Total {total_inserted} rows inserted. ===")


if __name__ == "__main__":
    run()
