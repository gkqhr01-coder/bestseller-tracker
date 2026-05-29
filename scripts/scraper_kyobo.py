"""
교보문고 베스트셀러 크롤러 (2026년 5월, 내부 API 방식).

교보는 페이지가 JS로 렌더링되어 일반 HTML 크롤링이 안 되지만,
페이지가 내부적으로 호출하는 JSON API를 직접 부르면 데이터를 받을 수 있다.

API: GET https://store.kyobobook.co.kr/api/gw/best/best-seller/total
  params: page, per, period=002(주간), bsslBksClstCode=A(전체)
  ⚠️ 헤더에 X-Api-Gw-Key (라이센스 키)가 반드시 필요. 없으면 401.
     이 키는 ~/kyobo_key.txt 파일에서 읽어온다.

응답 구조: data.bestSeller[] 배열, 각 항목:
  prstRnkn   → 순위
  cmdtName   → 제목
  chrcName   → 저자
  pbcmName   → 출판사
  saleCmdtid → 상품ID (상세페이지 링크용)
  cmdtCode   → ISBN (표지 이미지 URL 생성용)

표지: https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/{ISBN}.jpg

⚠️ API 키(X-Api-Gw-Key)는 JWT 형태로 만료될 수 있음.
   401이 뜨면 크롬 개발자도구에서 키를 다시 따와 ~/kyobo_key.txt를 갱신해야 한다.
"""

import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_URL = "https://store.kyobobook.co.kr/api/gw/best/best-seller/total"
KEY_PATH = os.path.expanduser("~/kyobo_key.txt")
COVER_TMPL = "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/{isbn}.jpg"

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://store.kyobobook.co.kr/bestseller/total",
}


def _load_key() -> str:
    """API 키를 파일에서 읽는다. 없으면 안내 메시지와 함께 예외."""
    if not os.path.exists(KEY_PATH):
        raise FileNotFoundError(
            f"교보 API 키 파일이 없습니다: {KEY_PATH}\n"
            "크롬 개발자도구에서 X-Api-Gw-Key 값을 복사해 저장하세요."
        )
    with open(KEY_PATH) as f:
        key = f.read().strip()
    if not key:
        raise ValueError(f"{KEY_PATH} 파일이 비어 있습니다.")
    return key


def fetch_page(page: int, per: int, headers: dict) -> list[dict]:
    params = {"page": page, "per": per, "period": "002", "bsslBksClstCode": "A"}
    r = requests.get(API_URL, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    raw_books = data.get("data", {}).get("bestSeller", [])

    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    books = []
    for b in raw_books:
        rank = b.get("prstRnkn")
        title = (b.get("cmdtName") or "").strip()
        if not rank or not title:
            continue

        author = (b.get("chrcName") or "").strip()
        publisher = (b.get("pbcmName") or "").strip()
        sale_id = b.get("saleCmdtid") or ""
        isbn = b.get("cmdtCode") or ""

        url = f"https://product.kyobobook.co.kr/detail/{sale_id}" if sale_id else ""
        cover_url = COVER_TMPL.format(isbn=isbn) if isbn else ""

        books.append({
            "collected_at": today,
            "store": "kyobo",
            "rank": rank,
            "title": title,
            "author": author,
            "publisher": publisher,
            "price": None,  # API 응답에 가격이 명확히 없어 생략
            "pub_date": "",
            "url": url,
            "cover_url": cover_url,
        })
    return books


def fetch_top100() -> list[dict]:
    key = _load_key()
    headers = {**HEADERS_BASE, "X-Api-Gw-Key": key}

    all_books = []
    per = 50  # 한 번에 50권 → 2번이면 100권
    for page in range(1, 3):
        try:
            print(f"  [kyobo] page {page} ...", end=" ")
            books = fetch_page(page, per, headers)
            all_books.extend(books)
            print(f"{len(books)} books")
            time.sleep(1.5)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            if code == 401:
                print("ERROR 401: API 키 만료/누락 → ~/kyobo_key.txt 갱신 필요")
            else:
                print(f"ERROR: {e}")
            break
        except Exception as e:
            print(f"ERROR: {e}")
            break

    # 순위 중복 제거 후 100위까지
    seen = set()
    uniq = []
    for b in sorted(all_books, key=lambda x: x["rank"]):
        if b["rank"] in seen or b["rank"] > 100:
            continue
        seen.add(b["rank"])
        uniq.append(b)
    return uniq


if __name__ == "__main__":
    books = fetch_top100()
    print(f"\nTotal: {len(books)} books")
    for b in books[:5]:
        print(f"[{b['rank']}] {b['title']} / {b['author']} / {b['publisher']}")
        print(f"     표지: {b['cover_url']}")
