"""
교보문고 베스트셀러 크롤러.

URL 구조: https://product.kyobobook.co.kr/bestseller/total?page=N&per=20
정적 HTML로 렌더링되며 requests + BeautifulSoup로 충분.

⚠️ 셀렉터 유지보수 주의:
사이트 리뉴얼 시 SELECTORS 딕셔너리만 수정하면 됩니다.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URL = "https://product.kyobobook.co.kr/bestseller/total"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

# ⬇️ 사이트 리뉴얼 시 여기만 수정
SELECTORS = {
    "item": "li.prod_item",
    "rank": ".prod_rank",
    "title": ".prod_info a.prod_link",
    "author": ".prod_author",
    "price": ".prod_price .price",
    "link": ".prod_info a.prod_link",
}


def _to_int(text: str) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _parse_author_field(text: str) -> tuple[str, str, str]:
    """
    교보 author 필드 예시: '한강 · 창비 · 2024.10.10'
    → (저자, 출판사, 출간일)
    """
    if not text:
        return "", "", ""
    parts = [p.strip() for p in re.split(r"[·•∙]", text) if p.strip()]
    author = parts[0] if len(parts) > 0 else ""
    publisher = parts[1] if len(parts) > 1 else ""
    pub_date = parts[2] if len(parts) > 2 else ""
    return author, publisher, pub_date


def fetch_page(page: int) -> list[dict]:
    """페이지 1개 (보통 20권) 가져오기."""
    params = {"page": page, "per": 20}
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = soup.select(SELECTORS["item"])
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    books = []

    for item in items:
        rank_el = item.select_one(SELECTORS["rank"])
        title_el = item.select_one(SELECTORS["title"])
        author_el = item.select_one(SELECTORS["author"])
        price_el = item.select_one(SELECTORS["price"])

        if not (rank_el and title_el):
            continue

        rank = _to_int(rank_el.get_text(strip=True))
        title = title_el.get_text(strip=True)
        author, publisher, pub_date = _parse_author_field(
            author_el.get_text(" ", strip=True) if author_el else ""
        )
        price = _to_int(price_el.get_text(strip=True)) if price_el else None
        url = title_el.get("href", "")
        if url and not url.startswith("http"):
            url = "https://product.kyobobook.co.kr" + url

        books.append({
            "collected_at": today,
            "store": "kyobo",
            "rank": rank,
            "title": title,
            "author": author,
            "publisher": publisher,
            "price": price,
            "pub_date": pub_date,
            "url": url,
        })
    return books


def fetch_top100() -> list[dict]:
    """1~100위 수집."""
    all_books = []
    for page in range(1, 6):  # 5페이지 × 20 = 100
        try:
            print(f"  [kyobo] page {page} ...", end=" ")
            books = fetch_page(page)
            print(f"{len(books)} books")
            all_books.extend(books)
            time.sleep(1.5)  # 매너 딜레이
        except Exception as e:
            print(f"ERROR: {e}")
    return all_books


if __name__ == "__main__":
    books = fetch_top100()
    print(f"\nTotal: {len(books)} books")
    for b in books[:3]:
        print(b)
