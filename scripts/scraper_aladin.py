"""
알라딘 베스트셀러 크롤러.

URL: https://www.aladin.co.kr/shop/common/wbest.aspx?BranchType=1&page=N
페이지당 25권 × 4페이지 = 100권 (사이트 기본 페이지네이션).
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
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def _to_int(text: str) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _parse_author_publisher(text: str) -> tuple[str, str, str]:
    """
    알라딘 author 영역 예시: '한강 (지은이) | 창비 | 2024년 10월'
    → (저자, 출판사, 출간일)
    """
    if not text:
        return "", "", ""
    parts = [p.strip() for p in text.split("|")]
    author = re.sub(r"\(.*?\)", "", parts[0]).strip() if len(parts) > 0 else ""
    publisher = parts[1] if len(parts) > 1 else ""
    pub_date = parts[2] if len(parts) > 2 else ""
    return author, publisher, pub_date


def fetch_page(page: int) -> list[dict]:
    params = {"BranchType": 1, "page": page}  # BranchType=1: 종합
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    r.encoding = "euc-kr"  # 알라딘은 EUC-KR
    soup = BeautifulSoup(r.text, "html.parser")

    # 알라딘은 div.ss_book_box 단위로 책 정보가 묶임
    items = soup.select("div.ss_book_box")
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    books = []

    for item in items:
        # 순위: .ss_book_list 안 첫 b 태그가 보통 순위
        rank_el = item.select_one("li b") or item.select_one(".ss_ht1")
        title_el = item.select_one("a.bo3, a.bo3 b")

        if not title_el:
            continue

        # 순위 추출
        rank = None
        for b_tag in item.select("li b"):
            n = _to_int(b_tag.get_text(strip=True))
            if n and 1 <= n <= 200:
                rank = n
                break

        title = title_el.get_text(strip=True)
        link_el = item.select_one("a.bo3")
        url = link_el.get("href", "") if link_el else ""
        if url and not url.startswith("http"):
            url = "https://www.aladin.co.kr" + url

        # 저자/출판사: 책 박스 안 li 텍스트들에서 추출
        author_text = ""
        for li in item.select("li"):
            txt = li.get_text(" ", strip=True)
            if "지은이" in txt or "옮긴이" in txt or "|" in txt:
                author_text = txt
                break

        author, publisher, pub_date = _parse_author_publisher(author_text)

        # 가격: 'class="ss_p2"' 영역 또는 '원' 포함 텍스트
        price = None
        price_el = item.select_one(".ss_p2, .ss_p")
        if price_el:
            price = _to_int(price_el.get_text())

        if rank and title:
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
            })
    return books


def fetch_top100() -> list[dict]:
    all_books = []
    # 알라딘은 페이지당 25권 정도, 4페이지면 100권
    for page in range(1, 5):
        try:
            print(f"  [aladin] page {page} ...", end=" ")
            books = fetch_page(page)
            print(f"{len(books)} books")
            all_books.extend(books)
            time.sleep(1.5)
        except Exception as e:
            print(f"ERROR: {e}")
    # 100위까지만 자르기 (혹시 더 들어왔을 경우)
    all_books = sorted(all_books, key=lambda x: x["rank"])[:100]
    return all_books


if __name__ == "__main__":
    books = fetch_top100()
    print(f"\nTotal: {len(books)} books")
    for b in books[:3]:
        print(b)
