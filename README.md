# 베스트셀러 트래커 (로컬 실행 버전)

예스24·알라딘 베스트셀러 100위를 **맥에서** 매일 수집해 SQLite에 누적하고,
GitHub에 올려 기존 대시보드(`gkqhr01-coder.github.io/bestseller-tracker`)를 갱신합니다.

> 교보문고는 JavaScript 렌더링 방식이라 현재 제외. 나중에 Selenium 버전으로 추가 가능
> (구조상 `scraper_kyobo.py`만 추가하고 `run_all.py`·`build_dashboard.py`에 한 줄씩 더하면 됨).

## 왜 로컬인가

서점들이 데이터센터 IP(클라우드)를 차단해서, GitHub Actions에서는 수집이 안 됩니다.
가정용 IP인 맥에서는 정상 동작하므로, 수집은 맥에서 하고 결과만 GitHub에 올립니다.

---

## 폴더 구조

```
bestseller-tracker/
├── scripts/
│   ├── db.py                # SQLite 초기화·정규화·삽입
│   ├── scraper_yes24.py     # 예스24 크롤러 (검증 완료)
│   ├── scraper_aladin.py    # 알라딘 크롤러 (검증 완료)
│   ├── run_all.py           # 수집 메인
│   └── build_dashboard.py   # docs/index.html 생성
├── data/bestsellers.db      # 누적 데이터 (자동 생성)
├── docs/index.html          # 대시보드 (자동 생성)
├── run.sh                   # 수집+업로드 한 번에 (수동 실행용)
├── com.max.bestseller.plist # 자동 실행 설정 (매일 9시)
└── README.md
```

---

## 설치 (최초 1회)

이미 어제 `requests`, `beautifulsoup4`, `lxml`은 설치하셨습니다. 추가 설치 없음.

기존 GitHub 레포를 맥에 내려받아(클론) 그 안에서 작업합니다. 터미널에서:

```bash
cd ~/Desktop
git clone https://github.com/gkqhr01-coder/bestseller-tracker.git
cd bestseller-tracker
```

그다음 이 폴더(`scripts/`, `run.sh` 등)의 파일들을 클론된 레포 안에 복사해 넣습니다.
(Finder에서 드래그하거나, 안내에 따라 진행)

---

## 매일 수동 실행 (먼저 이걸로 익숙해지기)

터미널에서:

```bash
cd ~/Desktop/bestseller-tracker
bash run.sh
```

이러면 수집 → 대시보드 생성 → GitHub 업로드까지 자동으로 됩니다.
마지막에 "완료!" 와 대시보드 주소가 뜨면 성공.

며칠 수동으로 돌려보며 문제없는 걸 확인한 뒤, 아래 자동 실행을 설정하세요.

---

## 자동 실행 설정 (매일 오전 9시)

맥의 표준 스케줄러 `launchd`를 사용합니다. 터미널에서 순서대로:

**1) 설정 파일의 경로를 실제 경로로 바꾸기** (아래 명령을 그대로 실행하면 자동 치환됩니다)

```bash
cd ~/Desktop/bestseller-tracker
RUN_SH="$(pwd)/run.sh"
LOG_DIR="$(pwd)"
sed -e "s|__RUN_SH_PATH__|$RUN_SH|" -e "s|__LOG_DIR__|$LOG_DIR|" \
    com.max.bestseller.plist > ~/Library/LaunchAgents/com.max.bestseller.plist
```

**2) 자동 실행 등록**

```bash
launchctl load ~/Library/LaunchAgents/com.max.bestseller.plist
```

이제 매일 오전 9시에 자동으로 수집·업로드됩니다.
(맥이 그 시간에 켜져 있어야 합니다. 잠자기 상태여도 보통 깨어나서 실행됩니다.)

**자동 실행 해제하려면:**

```bash
launchctl unload ~/Library/LaunchAgents/com.max.bestseller.plist
```

**제대로 등록됐는지 확인:**

```bash
launchctl list | grep bestseller
```

---

## 문제가 생기면

- **수집이 0권**: 서점이 사이트를 리뉴얼한 것. `scripts/scraper_*.py` 상단의 `SELECTORS` 수정 필요.
- **자동 실행이 안 됨**: `bestseller_error.log` 파일 확인. (레포 폴더에 생성됨)
- **git push 에러**: GitHub 로그인이 풀렸을 수 있음. 한 번 `bash run.sh`를 수동 실행하면 인증 창이 뜸.

---

## 대시보드가 보여주는 것

1. **서점 공통 상위권** — 예스24·알라딘 모두 100위에 든 책 (평균순위 정렬)
2. **서점별 단독 등장** — 한 서점에서만 등장한 책 (취향 차이)
3. **순위 변동 추이** — 책별 일자별 순위 그래프 (2일 이상 쌓이면 그려짐)
4. **서점별 베스트 100** — 각 서점 100위 전체

## 데이터 직접 분석

`data/bestsellers.db`는 표준 SQLite입니다. 예:

```python
import sqlite3, pandas as pd
df = pd.read_sql("SELECT * FROM bestsellers", sqlite3.connect("data/bestsellers.db"))
df.groupby("publisher")["rank"].mean().sort_values().head(20)  # 출판사별 평균순위
```
