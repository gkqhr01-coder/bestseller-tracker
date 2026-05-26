"""
메인 실행 진입점.
3사 크롤러를 순차 실행해 SQLite에 적재한다.
GitHub Actions에서 이 파일을 실행한다.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from db import init_db, insert_books
from scraper_kyobo import fetch_top100 as fetch_kyobo
from scraper_yes24 import fetch_top100 as fetch_yes24
from scraper_aladin import fetch_top100 as fetch_aladin


def run():
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")
    print(f"=== Bestseller collection started: {today} ===\n")

    init_db()

    total_inserted = 0

    for name, fetcher in [
        ("교보문고", fetch_kyobo),
        ("예스24", fetch_yes24),
        ("알라딘", fetch_aladin),
    ]:
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
