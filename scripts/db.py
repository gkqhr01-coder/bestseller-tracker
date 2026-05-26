"""
SQLite 초기화 및 공통 DB 유틸리티.

스키마 설계 원칙:
- 한 행 = (수집일자, 서점, 순위)의 유일한 조합
- 책의 정체성은 (제목 + 저자)로 식별 — 서점마다 ISBN을 노출하지 않는 경우가 있어
  완전 표준화는 어려움. 따라서 분석 시에는 normalize_title()로 정규화한 키 사용.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bestsellers.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """테이블이 없으면 생성."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestsellers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        collected_at TEXT NOT NULL,           -- YYYY-MM-DD (KST)
        store       TEXT NOT NULL,            -- kyobo / yes24 / aladin
        rank        INTEGER NOT NULL,
        title       TEXT NOT NULL,
        author      TEXT,
        publisher   TEXT,
        price       INTEGER,
        pub_date    TEXT,                     -- 출간일 (원본 문자열)
        url         TEXT,
        title_key   TEXT NOT NULL,            -- 정규화 키 (조인용)
        UNIQUE(collected_at, store, rank)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_title_key ON bestsellers(title_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_collected_at ON bestsellers(collected_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_store_date ON bestsellers(store, collected_at)")
    conn.commit()
    conn.close()


def normalize_title(title: str) -> str:
    """
    제목 정규화 — 서점 간 같은 책을 매칭하기 위함.
    공백·괄호 안 부가설명·특수문자를 제거하고 소문자화.
    """
    if not title:
        return ""
    import re
    t = title.lower()
    # 괄호와 그 안의 내용 제거 (예: "소년이 온다 (양장본)")
    t = re.sub(r"[\(\[\{].*?[\)\]\}]", "", t)
    # 특수문자/공백 제거
    t = re.sub(r"[^\w가-힣]", "", t)
    return t.strip()


def insert_books(books: list[dict]):
    """수집한 책 리스트를 DB에 삽입. 중복(같은 날짜·서점·순위)은 무시."""
    if not books:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    for b in books:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO bestsellers
                (collected_at, store, rank, title, author, publisher, price, pub_date, url, title_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                b["collected_at"], b["store"], b["rank"],
                b["title"], b.get("author"), b.get("publisher"),
                b.get("price"), b.get("pub_date"), b.get("url"),
                normalize_title(b["title"]),
            ))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"  [insert error] {b.get('title')}: {e}")
    conn.commit()
    conn.close()
    return inserted


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
