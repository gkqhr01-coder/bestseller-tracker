"""SQLite 초기화 및 공통 DB 유틸리티."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bestsellers.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bestsellers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        collected_at TEXT NOT NULL,
        store        TEXT NOT NULL,
        rank         INTEGER NOT NULL,
        title        TEXT NOT NULL,
        author       TEXT,
        publisher    TEXT,
        price        INTEGER,
        pub_date     TEXT,
        url          TEXT,
        cover_url    TEXT,
        title_key    TEXT NOT NULL,
        UNIQUE(collected_at, store, rank)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_title_key ON bestsellers(title_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_collected_at ON bestsellers(collected_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_store_date ON bestsellers(store, collected_at)")
    # 기존 DB에 cover_url 컬럼이 없으면 추가 (마이그레이션)
    cols = [r[1] for r in cur.execute("PRAGMA table_info(bestsellers)").fetchall()]
    if "cover_url" not in cols:
        cur.execute("ALTER TABLE bestsellers ADD COLUMN cover_url TEXT")
    conn.commit()
    conn.close()


def normalize_title(title):
    if not title:
        return ""
    import re
    t = title.lower()
    # 괄호(여러 종류)와 그 안의 내용 제거
    t = re.sub(r"[\(\[\{（［].*?[\)\]\}）］]", "", t)
    # 특전판류: 앞 수식어(트리플/더블/한정 등)와 함께 제거 (괄호 없는 버전 대응)
    t = re.sub(r"(트리플|더블|싱글|한정|특별|기념|개정|증보|합본|세트|박스|양장|특전)?\s*특전판", "", t)
    # 기타 판형/세트 표기 제거
    t = re.sub(r"(양장본|반양장|개정판|개정증보판|특별판|한정판|합본판|박스세트|세트)", "", t)
    # 공백/특수문자 제거
    t = re.sub(r"[^\w가-힣]", "", t)
    return t.strip()


def insert_books(books):
    if not books:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    for b in books:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO bestsellers
                (collected_at, store, rank, title, author, publisher, price, pub_date, url, cover_url, title_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                b["collected_at"], b["store"], b["rank"],
                b["title"], b.get("author"), b.get("publisher"),
                b.get("price"), b.get("pub_date"), b.get("url"), b.get("cover_url"),
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
