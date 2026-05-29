"""
대시보드 빌더 (예스24 + 알라딘).

DB를 읽어 docs/index.html 정적 페이지를 생성.
STORE_LABELS에 서점을 추가하면 자동으로 모든 섹션에 반영됩니다.
(나중에 교보 추가 시 여기에 'kyobo' 한 줄만 더하면 됨)

인사이트:
  1) 공통 상위권 (모든 서점에 등장)
  2) 서점별 단독 등장
  3) 순위 변동 추이
  4) 서점별 베스트 100
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "bestsellers.db"
OUT_PATH = ROOT / "docs" / "index.html"

# 서점 추가 시 여기만 수정 (예: "kyobo": "교보문고")
STORE_LABELS = {"yes24": "예스24", "aladin": "알라딘", "kyobo": "교보문고"}
STORE_COUNT = len(STORE_LABELS)


def fetch_latest_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT MAX(collected_at) AS d FROM bestsellers")
    latest_date = cur.fetchone()["d"]
    if not latest_date:
        conn.close()
        return None

    cur.execute("""
        SELECT store, rank, title, author, publisher, price, pub_date, url, cover_url, title_key
        FROM bestsellers WHERE collected_at = ?
        ORDER BY store, rank
    """, (latest_date,))
    latest_rows = [dict(r) for r in cur.fetchall()]

    # title_key별로 묶기
    by_key = {}
    for r in latest_rows:
        by_key.setdefault(r["title_key"], {"info": r, "ranks": {}})
        by_key[r["title_key"]]["ranks"][r["store"]] = r["rank"]

    # 공통 상위권: 모든 서점에 등장
    common = [
        {
            "title": v["info"]["title"],
            "author": v["info"]["author"],
            "publisher": v["info"]["publisher"],
            "cover_url": v["info"]["cover_url"],
            "ranks": v["ranks"],
            "avg_rank": sum(v["ranks"].values()) / len(v["ranks"]),
        }
        for v in by_key.values()
        if len(v["ranks"]) == STORE_COUNT
    ]
    common.sort(key=lambda x: x["avg_rank"])

    # 서점별 단독 등장
    unique_by_store = {s: [] for s in STORE_LABELS}
    for v in by_key.values():
        if len(v["ranks"]) == 1:
            store = list(v["ranks"].keys())[0]
            if store in unique_by_store:
                unique_by_store[store].append({
                    "title": v["info"]["title"],
                    "author": v["info"]["author"],
                    "rank": v["ranks"][store],
                })
    for s in unique_by_store:
        unique_by_store[s].sort(key=lambda x: x["rank"])

    # 순위 추이 (최근 14일, 공통 상위 10권)
    cur.execute("SELECT DISTINCT collected_at FROM bestsellers ORDER BY collected_at DESC LIMIT 14")
    recent_dates = sorted([r["collected_at"] for r in cur.fetchall()])

    title_to_key = {v["info"]["title"]: k for k, v in by_key.items()}
    trend_keys = [title_to_key[c["title"]] for c in common[:10] if c["title"] in title_to_key]

    trend_data = {}
    if trend_keys and recent_dates:
        ph = ",".join("?" * len(trend_keys))
        dph = ",".join("?" * len(recent_dates))
        cur.execute(f"""
            SELECT collected_at, store, title, title_key, rank
            FROM bestsellers
            WHERE title_key IN ({ph}) AND collected_at IN ({dph})
            ORDER BY collected_at, store
        """, (*trend_keys, *recent_dates))
        for r in cur.fetchall():
            k = r["title_key"]
            trend_data.setdefault(k, {"title": r["title"], "series": {}})
            trend_data[k]["series"].setdefault(r["store"], []).append({
                "date": r["collected_at"], "rank": r["rank"],
            })

    cur.execute("SELECT COUNT(DISTINCT collected_at) AS d, COUNT(*) AS n FROM bestsellers")
    stat = cur.fetchone()
    stats = {"days": stat["d"], "rows": stat["n"]}

    conn.close()

    return {
        "latest_date": latest_date,
        "stats": stats,
        "store_labels": STORE_LABELS,
        "latest_by_store": {
            s: [r for r in latest_rows if r["store"] == s] for s in STORE_LABELS
        },
        "common": common,
        "unique_by_store": unique_by_store,
        "trend": list(trend_data.values()),
        "recent_dates": recent_dates,
        "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST"),
    }


def render(data):
    payload = json.dumps(data, ensure_ascii=False) if data else "null"
    return TEMPLATE.replace("__PAYLOAD__", payload)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>베스트셀러 트래커</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,800&family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#1a1614;--paper:#f4ede2;--paper-deep:#ebe2d3;--accent:#c8451f;--line:#2a221d;--muted:#7a6f63}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans KR',sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}
body{background-image:radial-gradient(rgba(42,34,29,0.04) 1px,transparent 1px);background-size:4px 4px}
.wrap{max-width:1180px;margin:0 auto;padding:48px 32px 96px}
header.masthead{border-top:6px solid var(--ink);border-bottom:1px solid var(--line);padding:24px 0 20px;margin-bottom:36px;display:grid;grid-template-columns:1fr auto;align-items:end;gap:24px}
.masthead h1{font-family:'Fraunces',serif;font-weight:800;font-size:clamp(40px,6vw,72px);line-height:0.96;letter-spacing:-0.02em}
.masthead h1 em{font-style:italic;color:var(--accent);font-weight:400}
.masthead .meta{text-align:right;font-size:12px;color:var(--muted);letter-spacing:0.02em}
.masthead .meta b{display:block;color:var(--ink);font-size:16px;font-weight:600;margin-top:4px}
.stats{display:flex;border:1px solid var(--line);background:var(--paper-deep);margin-bottom:48px}
.stat{flex:1;padding:16px 24px;border-right:1px solid var(--line)}
.stat:last-child{border-right:none}
.stat .label{font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted)}
.stat .value{font-family:'Fraunces',serif;font-size:32px;font-weight:600;font-feature-settings:"tnum";margin-top:4px}
section{margin-bottom:64px}
.section-head{display:flex;align-items:baseline;gap:16px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:24px}
.section-head h2{font-family:'Fraunces',serif;font-size:28px;font-weight:600}
.section-head .kicker{font-size:12px;letter-spacing:0.16em;text-transform:uppercase;color:var(--accent);font-weight:600}
.section-head .note{margin-left:auto;font-size:12px;color:var(--muted)}
.tabs{display:flex;gap:4px;margin-bottom:16px;border-bottom:2px solid var(--line)}
.tab{padding:12px 20px;background:none;border:none;border-bottom:2px solid transparent;font-family:inherit;font-size:14px;font-weight:500;cursor:pointer;color:var(--muted);margin-bottom:-2px}
.tab.active{color:var(--ink);border-bottom-color:var(--accent)}
.book-list{display:grid;grid-template-columns:repeat(2,1fr);border:1px solid var(--line)}
.book-row{display:grid;grid-template-columns:32px 48px 1fr auto;gap:16px;padding:12px 16px;border-bottom:1px solid rgba(42,34,29,0.12);align-items:center}
.book-row:nth-child(odd){border-right:1px solid var(--line)}
.book-row .rank{font-family:'Fraunces',serif;font-size:20px;font-weight:600;font-feature-settings:"tnum"}
.book-row .rank.top{color:var(--accent)}
.book-row .cover{width:48px;height:64px;object-fit:cover;background:var(--paper-deep);border:1px solid rgba(42,34,29,0.15);display:block}
.book-row .cover-empty{width:48px;height:64px;background:var(--paper-deep);border:1px solid rgba(42,34,29,0.15)}
.book-row .info{min-width:0}
.book-row .title{font-weight:500;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.book-row .meta-line{font-size:12px;color:var(--muted);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.book-row .price{font-size:12px;color:var(--muted);font-feature-settings:"tnum"}
.common-table{width:100%;border-collapse:collapse;background:var(--paper);border:1px solid var(--line)}
.common-table th,.common-table td{padding:12px 16px;text-align:left;border-bottom:1px solid rgba(42,34,29,0.1);font-size:14px}
.common-table th{background:var(--ink);color:var(--paper);font-weight:500;font-size:12px;letter-spacing:0.12em;text-transform:uppercase}
.common-table td.rank-cell{font-family:'Fraunces',serif;font-size:20px;font-feature-settings:"tnum";text-align:center;width:64px}
.rank-pill{display:inline-block;min-width:32px;padding:4px 8px;background:var(--paper-deep);border:1px solid var(--line);font-family:'Fraunces',serif;font-feature-settings:"tnum";font-size:14px;text-align:center}
.rank-pill.top10{background:var(--accent);color:var(--paper);border-color:var(--accent)}
.book-title-cell{font-weight:500;word-break:keep-all}
.ct-book{display:flex;align-items:center;gap:12px}
.ct-cover{width:40px;height:56px;object-fit:cover;background:var(--paper-deep);border:1px solid rgba(42,34,29,0.15);flex-shrink:0}
.ct-cover-empty{width:40px;height:56px;background:var(--paper-deep);border:1px solid rgba(42,34,29,0.15);flex-shrink:0}
.ct-info{min-width:0}
.book-title-cell .author{color:var(--muted);font-size:12px;margin-top:4px}
.unique-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}
.unique-col h3{font-family:'Fraunces',serif;font-size:20px;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid var(--ink)}
.unique-col ol{list-style:none;counter-reset:u}
.unique-col li{counter-increment:u;padding:8px 0;border-bottom:1px dotted rgba(42,34,29,0.2);font-size:12px;line-height:1.6}
.unique-col li .num-badge{font-family:'Fraunces',serif;color:var(--muted);font-feature-settings:"tnum";margin-right:8px}
.unique-col li .utitle{word-break:keep-all;line-height:1.5}
.unique-col .uauthor{color:var(--muted);font-size:12px}
.trend-wrap{background:var(--paper-deep);border:1px solid var(--line);padding:24px;margin-top:8px}
.trend-select{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}
.trend-chip{padding:8px 12px;background:var(--paper);border:1px solid var(--line);font-size:12px;cursor:pointer;font-family:inherit;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.trend-chip.active{background:var(--ink);color:var(--paper);border-color:var(--ink)}
#trendChart{width:100%;height:320px}
footer{margin-top:80px;padding-top:24px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);display:flex;justify-content:space-between}
.empty{padding:80px 24px;text-align:center;color:var(--muted);border:1px dashed var(--line);font-family:'Fraunces',serif;font-size:16px;font-style:italic}
@media (max-width:820px){.book-list{grid-template-columns:1fr}.book-row:nth-child(odd){border-right:none}.unique-grid{grid-template-columns:1fr}.masthead{grid-template-columns:1fr}.masthead .meta{text-align:left}}
</style>
</head>
<body>
<div class="wrap">
<header class="masthead">
  <div><h1>Bestseller <em>Almanac</em></h1></div>
  <div class="meta">수집 기준일<b id="latestDate">—</b><span style="margin-top:6px;display:block" id="generatedAt"></span></div>
</header>
<div class="stats" id="stats"></div>
<section>
  <div class="section-head"><span class="kicker">01</span><h2>서점 공통 상위권</h2><span class="note" id="commonNote"></span></div>
  <div id="commonContainer"></div>
</section>
<section>
  <div class="section-head"><span class="kicker">02</span><h2>서점별 단독 등장</h2><span class="note">한 서점에서만 100위에 등장한 책 상위 10권</span></div>
  <div class="unique-grid" id="uniqueContainer"></div>
</section>
<section>
  <div class="section-head"><span class="kicker">03</span><h2>순위 변동 추이</h2><span class="note">책을 선택하면 일자별 순위가 그려집니다</span></div>
  <div class="trend-wrap"><div class="trend-select" id="trendChips"></div><canvas id="trendChart"></canvas></div>
</section>
<section>
  <div class="section-head"><span class="kicker">04</span><h2>서점별 베스트 100</h2><span class="note">탭으로 전환</span></div>
  <div class="tabs" id="storeTabs"></div>
  <div id="storeBooks"></div>
</section>
<footer><span>Bestseller Tracker · 매일 자동 수집</span><span id="footerStats"></span></footer>
</div>
<script>
const DATA = __PAYLOAD__;
const STORE_COLORS = {yes24:"#2d6a4f", aladin:"#3d5a80", kyobo:"#c8451f"};

function init(){
  if(!DATA){document.querySelector('.wrap').innerHTML='<div class="empty">아직 수집된 데이터가 없습니다.<br>크롤러가 처음 돌고 나면 여기에 결과가 나타납니다.</div>';return;}
  const LBL = DATA.store_labels;
  document.getElementById('latestDate').textContent = DATA.latest_date;
  document.getElementById('generatedAt').textContent = '생성: ' + DATA.generated_at;
  const storeNames = Object.values(LBL).join('·');
  document.getElementById('commonNote').textContent = storeNames + ' 모두 100위 안에 등장한 책';
  renderStats(LBL); renderCommon(LBL); renderUnique(LBL); renderTrend(LBL); renderStores(LBL);
}
function renderStats(LBL){
  const s=DATA.stats;
  document.getElementById('stats').innerHTML=`
    <div class="stat"><div class="label">Days Tracked</div><div class="value">${s.days}</div></div>
    <div class="stat"><div class="label">Total Records</div><div class="value">${s.rows.toLocaleString()}</div></div>
    <div class="stat"><div class="label">공통 (오늘)</div><div class="value">${DATA.common.length}</div></div>
    <div class="stat"><div class="label">Stores</div><div class="value">${Object.keys(LBL).length}</div></div>`;
  document.getElementById('footerStats').textContent=`${s.rows.toLocaleString()} rows · ${s.days} days`;
}
function renderCommon(LBL){
  const c=DATA.common;
  if(!c.length){document.getElementById('commonContainer').innerHTML='<div class="empty">아직 공통 상위권 책이 없습니다.</div>';return;}
  const stores=Object.keys(LBL);
  let head=stores.map(s=>`<th>${LBL[s]}</th>`).join('');
  let rows='';
  for(const b of c.slice(0,30)){
    let cells=stores.map(s=>{const r=b.ranks[s];return `<td><span class="rank-pill ${r<=10?'top10':''}">${r||'-'}</span></td>`}).join('');
    const cover=b.cover_url?`<img class="ct-cover" src="${escapeHtml(b.cover_url)}" alt="" loading="lazy" onerror="this.outerHTML='<div class=\\'ct-cover-empty\\'></div>'">`:`<div class="ct-cover-empty"></div>`;
    rows+=`<tr><td class="rank-cell">${b.avg_rank.toFixed(1)}</td>
      <td class="book-title-cell"><div class="ct-book">${cover}<div class="ct-info">${escapeHtml(b.title)}<div class="author">${escapeHtml(b.author||'')} · ${escapeHtml(b.publisher||'')}</div></div></div></td>
      ${cells}</tr>`;
  }
  document.getElementById('commonContainer').innerHTML=`<table class="common-table"><thead><tr><th>평균순위</th><th>도서</th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}
function renderUnique(LBL){
  let html='';
  for(const[store,books]of Object.entries(DATA.unique_by_store)){
    const items=books.slice(0,10).map((b,i)=>`<li><span class="utitle"><span class="num-badge">#${i+1}</span>${escapeHtml(b.title)} <span style="color:var(--muted)">· ${b.rank}위</span></span><div class="uauthor">${escapeHtml(b.author||'')}</div></li>`).join('')||'<li style="color:var(--muted)">단독 등장 없음</li>';
    html+=`<div class="unique-col"><h3 style="color:${STORE_COLORS[store]||'#000'}">${LBL[store]}</h3><ol>${items}</ol></div>`;
  }
  document.getElementById('uniqueContainer').innerHTML=html;
}
function renderStores(LBL){
  const stores=Object.keys(LBL);
  document.getElementById('storeTabs').innerHTML=stores.map((s,i)=>`<button class="tab ${i===0?'active':''}" data-store="${s}">${LBL[s]}</button>`).join('');
  function show(store){
    const books=DATA.latest_by_store[store]||[];
    if(!books.length){document.getElementById('storeBooks').innerHTML='<div class="empty">데이터 없음</div>';return;}
    document.getElementById('storeBooks').innerHTML=`<div class="book-list">${books.map(b=>`
      <div class="book-row"><div class="rank ${b.rank<=10?'top':''}">${b.rank}</div>
      ${b.cover_url?`<img class="cover" src="${escapeHtml(b.cover_url)}" alt="" loading="lazy" onerror="this.outerHTML='<div class=\\'cover-empty\\'></div>'">`:`<div class="cover-empty"></div>`}
      <div class="info"><div class="title">${b.url?`<a href="${escapeHtml(b.url)}" target="_blank" style="color:inherit;text-decoration:none">${escapeHtml(b.title)}</a>`:escapeHtml(b.title)}</div>
      <div class="meta-line">${escapeHtml(b.author||'')}${b.publisher?' · '+escapeHtml(b.publisher):''}</div></div>
      <div class="price">${b.price?b.price.toLocaleString()+'원':''}</div></div>`).join('')}</div>`;
  }
  document.querySelectorAll('#storeTabs .tab').forEach(btn=>btn.addEventListener('click',()=>{
    document.querySelectorAll('#storeTabs .tab').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');show(btn.dataset.store);
  }));
  show(stores[0]);
}
let selIdx=0;
function renderTrend(LBL){
  const t=DATA.trend;
  if(!t.length){document.getElementById('trendChips').innerHTML='<span style="color:var(--muted);font-size:13px">추이를 표시하려면 최소 2일 이상 수집이 필요합니다.</span>';return;}
  document.getElementById('trendChips').innerHTML=t.map((x,i)=>`<button class="trend-chip ${i===0?'active':''}" data-idx="${i}" title="${escapeHtml(x.title)}">${escapeHtml(x.title)}</button>`).join('');
  document.querySelectorAll('.trend-chip').forEach(c=>c.addEventListener('click',()=>{
    document.querySelectorAll('.trend-chip').forEach(x=>x.classList.remove('active'));
    c.classList.add('active');selIdx=parseInt(c.dataset.idx);drawTrend(LBL);
  }));
  drawTrend(LBL);
}
function drawTrend(LBL){
  const canvas=document.getElementById('trendChart');
  const dpr=window.devicePixelRatio||1;const rect=canvas.getBoundingClientRect();
  canvas.width=rect.width*dpr;canvas.height=320*dpr;
  const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);
  const W=rect.width,H=320,padL=50,padR=24,padT=20,padB=40;
  const plotW=W-padL-padR,plotH=H-padT-padB;
  ctx.clearRect(0,0,W,H);
  const trend=DATA.trend[selIdx];if(!trend)return;
  const dates=DATA.recent_dates;
  if(dates.length<2){ctx.fillStyle='#7a6f63';ctx.font="italic 14px 'Fraunces',serif";ctx.textAlign='center';ctx.fillText('최소 2일 이상의 데이터가 필요합니다',W/2,H/2);return;}
  const yMax=100,yMin=1,xStep=plotW/Math.max(1,dates.length-1);
  ctx.strokeStyle='rgba(42,34,29,0.1)';ctx.lineWidth=1;
  [1,25,50,75,100].forEach(r=>{const y=padT+((r-yMin)/(yMax-yMin))*plotH;
    ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(W-padR,y);ctx.stroke();
    ctx.fillStyle='#7a6f63';ctx.font="11px 'IBM Plex Sans KR'";ctx.textAlign='right';ctx.fillText(r+'위',padL-8,y+4)});
  dates.forEach((d,i)=>{const x=padL+xStep*i;ctx.fillStyle='#7a6f63';ctx.font="10px 'IBM Plex Sans KR'";ctx.textAlign='center';ctx.fillText(d.slice(5),x,H-padB+18)});
  for(const[store,points]of Object.entries(trend.series)){
    const color=STORE_COLORS[store]||'#999';
    ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=2.5;ctx.beginPath();let started=false;
    points.forEach(p=>{const di=dates.indexOf(p.date);if(di<0)return;const x=padL+xStep*di,y=padT+((p.rank-yMin)/(yMax-yMin))*plotH;if(!started){ctx.moveTo(x,y);started=true}else ctx.lineTo(x,y)});
    ctx.stroke();
    points.forEach(p=>{const di=dates.indexOf(p.date);if(di<0)return;const x=padL+xStep*di,y=padT+((p.rank-yMin)/(yMax-yMin))*plotH;ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill()});
  }
  const ly=padT+8;let lx=padL+12;
  Object.keys(trend.series).forEach(store=>{ctx.fillStyle=STORE_COLORS[store]||'#999';ctx.fillRect(lx,ly,10,10);ctx.fillStyle='#1a1614';ctx.font="500 12px 'IBM Plex Sans KR'";ctx.textAlign='left';ctx.fillText(LBL[store]||store,lx+16,ly+9);lx+=100});
}
function escapeHtml(s){return(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
window.addEventListener('resize',()=>drawTrend(DATA?DATA.store_labels:{}));
init();
</script>
</body>
</html>
"""


def build():
    print("Building dashboard...")
    data = fetch_latest_data()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render(data), encoding="utf-8")
    if data is None:
        print(f"  (no data yet) Empty dashboard → {OUT_PATH}")
    else:
        print(f"  Dashboard built → {OUT_PATH}")
        print(f"  latest_date: {data['latest_date']}, common: {len(data['common'])}, trend: {len(data['trend'])}")


if __name__ == "__main__":
    build()
