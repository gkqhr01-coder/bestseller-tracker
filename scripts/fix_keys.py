"""
정규화 로직 변경 후, 기존 DB의 title_key를 다시 계산한다.
db.py 업데이트 후 한 번만 실행하면 됨.
"""
import db

conn = db.get_conn()
cur = conn.cursor()
rows = cur.execute("SELECT id, title FROM bestsellers").fetchall()
updated = 0
for r in rows:
    new_key = db.normalize_title(r["title"])
    cur.execute("UPDATE bestsellers SET title_key = ? WHERE id = ?", (new_key, r["id"]))
    updated += 1
conn.commit()
conn.close()
print(f"✓ title_key 재계산 완료: {updated}건")
