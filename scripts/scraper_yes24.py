"""
예스24 베스트셀러 크롤러 (2026년 5월 검증 버전).

URL: https://www.yes24.com/product/category/bestseller?categoryNumber=001&pageNumber=N
- 한 페이지에 24권 → 약 5페이지로 100권 이상 확보 후 100위까지 사용
- 인코딩: UTF-8
- 실제 저장 HTML로 셀렉터 검증 완료

⚠️ 사이트 리뉴얼 시 SELECTORS만 수정하면 됩니다.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URL = "https://www.yes24.com/product/category/bestseller"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

SELECTORS = {
    "item": "#yesBestList > li",
    "rank": ".ico.rank",
    "title": ".gd_name",
    "authpub": ".authPub",   # [0]=저자, [1]=출판사, [2]=날짜 (보통)
    "date": ".info_date",
    "price": ".yes_b",
}


def _to_int(text):
    if not text:
        return None
    d = re.sub(r"[^\d]", "", text)
    return int(d) if d else None


def fetch_page(page: int) -> list[dict]:
    params = {"categoryNumber": "001", "pageNumber": page}
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")  # content = 원본 바이트 (인코딩 안전)

    items = soup.select(SELECTORS["item"])
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    books = []

    for it in items:
        title_el = it.select_one(SELECTORS["title"])
        if not title_el:
            continue

        rank_el = it.select_one(SELECTORS["rank"])
        rank = _to_int(rank_el.get_text()) if rank_el else None

        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")
        if url and not url.startswith("http"):
            url = "https://www.yes24.com" + url

        # authPub: 보통 [저자, 출판사, 날짜] 순
        authpubs = it.select(SELECTORS["authpub"])
        author = authpubs[0].get_text(" ", strip=True) if len(authpubs) > 0 else ""
        publisher = authpubs[1].get_text(strip=True) if len(authpubs) > 1 else ""
        date_el = it.select_one(SELECTORS["date"])
        pub_date = date_el.get_text(strip=True) if date_el else (
            authpubs[2].get_text(strip=True) if len(authpubs) > 2 else ""
        )

        price_el = it.select_one(SELECTORS["price"])
        price = _to_int(price_el.get_text()) if price_el else None

        # 표지: lazy 이미지의 data-original에 실제 주소
        img_el = it.select_one("img.lazy") or it.select_one("img")
        cover_url = ""
        if img_el:
            cover_url = img_el.get("data-original") or img_el.get("src") or ""

        books.append({
            "collected_at": today,
            "store": "yes24",
            "rank": rank,
            "title": title,
            "author": author,
            "publisher": publisher,
            "price": price,
            "pub_date": pub_date,
            "url": url,
            "cover_url": cover_url,
        })
    return books


def fetch_top100() -> list[dict]:
    all_books = []
    seen_ranks = set()
    for page in range(1, 7):  # 24권 × 6 = 144 → 100 확보 충분
        try:
            print(f"  [yes24] page {page} ...", end=" ")
            books = fetch_page(page)
            # 중복 순위 방지 (페이지 경계 안전장치)
            new = [b for b in books if b["rank"] and b["rank"] not in seen_ranks]
            for b in new:
                seen_ranks.add(b["rank"])
            all_books.extend(new)
            print(f"{len(new)} books")
            if len([b for b in all_books if b['rank'] and b['rank'] <= 100]) >= 100:
                break
            time.sleep(1.5)
        except Exception as e:
            print(f"ERROR: {e}")
    # 100위까지만
    all_books = [b for b in all_books if b["rank"] and b["rank"] <= 100]
    all_books.sort(key=lambda x: x["rank"])
    return all_books


if __name__ == "__main__":
    books = fetch_top100()
    print(f"\nTotal: {len(books)} books")
    for b in books[:5]:
        print(f"[{b['rank']}] {b['title']} / {b['author']} / {b['publisher']} / {b['price']}")
