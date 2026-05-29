"""
알라딘 베스트셀러 크롤러 (2026년 5월 검증 버전).

URL: https://www.aladin.co.kr/shop/common/wbest.aspx?BranchType=1&page=N
- 한 페이지에 50권 → 2페이지로 100권
- 인코딩: UTF-8 (예전엔 EUC-KR이었으나 현재 UTF-8. r.content로 파싱)
- 순위: 박스 등장 순서 = 순위 (페이지별 오프셋 적용)

⚠️ 사이트 리뉴얼 시 SELECTORS와 파싱 로직 확인.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URL = "https://www.aladin.co.kr/shop/common/wbest.aspx"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

SELECTORS = {
    "item": "div.ss_book_box",
    "title": "a.bo3",
    "price": ".ss_p2",
}


def _to_int(text):
    if not text:
        return None
    d = re.sub(r"[^\d]", "", text)
    return int(d) if d else None


def _parse_author_publisher(box) -> tuple[str, str, str]:
    """
    저자/출판사/날짜가 들어있는 li를 찾아 파싱.
    형태 예: '한강 (지은이), 김역자 (옮긴이) | 창비 | 2024년 10월'
    → (저자, 출판사, 날짜)
    """
    for li in box.select(".ss_book_list li"):
        txt = li.get_text(" ", strip=True)
        # 출판사·날짜 구분자 '|'가 있고 '지은이/옮긴이/엮은이' 등이 있는 li
        if "|" in txt and any(k in txt for k in ["지은이", "옮긴이", "엮은이", "지음", "저"]):
            parts = [p.strip() for p in txt.split("|")]
            author = re.sub(r"\(.*?\)", "", parts[0]).strip().rstrip(",").strip() if parts else ""
            publisher = parts[1].strip() if len(parts) > 1 else ""
            pub_date = parts[2].strip() if len(parts) > 2 else ""
            return author, publisher, pub_date
    return "", "", ""


def fetch_page(page: int, rank_offset: int) -> list[dict]:
    params = {"BranchType": 1, "page": page}
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")  # content로 UTF-8 자동 처리

    items = soup.select(SELECTORS["item"])
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    books = []

    for idx, box in enumerate(items, start=1):
        title_el = box.select_one(SELECTORS["title"])
        if not title_el:
            continue

        rank = rank_offset + idx
        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")

        author, publisher, pub_date = _parse_author_publisher(box)

        price_el = box.select_one(SELECTORS["price"])
        price = _to_int(price_el.get_text()) if price_el else None

        # 표지: src에 'cover'가 포함된 이미지
        cover_url = ""
        for img in box.select("img"):
            src = img.get("src") or ""
            if "cover" in src.lower():
                cover_url = src
                break

        books.append({
            "collected_at": today,
            "store": "aladin",
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
    offset = 0
    for page in range(1, 3):  # 50 × 2 = 100
        try:
            print(f"  [aladin] page {page} ...", end=" ")
            books = fetch_page(page, offset)
            offset += len(books)
            all_books.extend(books)
            print(f"{len(books)} books")
            time.sleep(1.5)
        except Exception as e:
            print(f"ERROR: {e}")
    all_books = [b for b in all_books if b["rank"] <= 100]
    all_books.sort(key=lambda x: x["rank"])
    return all_books


if __name__ == "__main__":
    books = fetch_top100()
    print(f"\nTotal: {len(books)} books")
    for b in books[:5]:
        print(f"[{b['rank']}] {b['title']} / {b['author']} / {b['publisher']} / {b['price']}")
