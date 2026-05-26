"""
예스24 베스트셀러 크롤러.

URL: https://www.yes24.com/Product/Category/BestSeller?categoryNumber=001&PageNumber=N
페이지당 20권, 5페이지 = 100권.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URL = "https://www.yes24.com/Product/Category/BestSeller"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

SELECTORS = {
    "item": "ol#yesBestList li, ul.clearfix li",  # 백업 셀렉터 포함
    "rank": ".num, .rank",
    "title": ".gd_name",
    "author_publisher": ".info_row.info_pubGrp",
    "author": ".info_auth a, .authPub a",
    "publisher": ".info_pub a, .authPub .pub",
    "pub_date": ".info_date",
    "price": ".yes_b, strong.txt_num",
}


def _to_int(text: str) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def fetch_page(page: int) -> list[dict]:
    params = {"categoryNumber": "001", "pageNumber": page, "pageSize": 20}
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    # 예스24는 EUC-KR을 쓰던 시절이 있어 인코딩 명시
    r.encoding = r.apparent_encoding or "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    items = soup.select("ol#yesBestList > li")
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    books = []

    base_rank = (page - 1) * 20  # 페이지별 순위 오프셋 (페이지 내에서 1부터 시작하는 경우 대비)

    for idx, item in enumerate(items, start=1):
        title_el = item.select_one(".gd_name")
        if not title_el:
            continue

        # 순위: 별도 표기 있으면 우선, 없으면 인덱스로 계산
        rank_el = item.select_one(".num, .rank")
        rank = _to_int(rank_el.get_text(strip=True)) if rank_el else None
        if rank is None:
            rank = base_rank + idx

        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")
        if url and not url.startswith("http"):
            url = "https://www.yes24.com" + url

        author_el = item.select_one(".info_auth a, .authPub a")
        publisher_el = item.select_one(".info_pub a, .pub")
        pub_date_el = item.select_one(".info_date")
        price_el = item.select_one(".yes_b, strong.txt_num")

        books.append({
            "collected_at": today,
            "store": "yes24",
            "rank": rank,
            "title": title,
            "author": author_el.get_text(strip=True) if author_el else "",
            "publisher": publisher_el.get_text(strip=True) if publisher_el else "",
            "price": _to_int(price_el.get_text(strip=True)) if price_el else None,
            "pub_date": pub_date_el.get_text(strip=True) if pub_date_el else "",
            "url": url,
        })
    return books


def fetch_top100() -> list[dict]:
    all_books = []
    for page in range(1, 6):
        try:
            print(f"  [yes24] page {page} ...", end=" ")
            books = fetch_page(page)
            print(f"{len(books)} books")
            all_books.extend(books)
            time.sleep(1.5)
        except Exception as e:
            print(f"ERROR: {e}")
    return all_books


if __name__ == "__main__":
    books = fetch_top100()
    print(f"\nTotal: {len(books)} books")
    for b in books[:3]:
        print(b)
