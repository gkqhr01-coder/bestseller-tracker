# 베스트셀러 트래커

교보문고·예스24·알라딘 베스트셀러 100위를 매일 자동 수집해 SQLite에 누적하고, GitHub Pages 대시보드로 시각화합니다.

## 폴더 구조

```
bestseller-tracker/
├── scripts/
│   ├── db.py                  # SQLite 초기화·정규화·삽입
│   ├── scraper_kyobo.py       # 교보문고 크롤러
│   ├── scraper_yes24.py       # 예스24 크롤러
│   ├── scraper_aladin.py      # 알라딘 크롤러
│   ├── run_all.py             # 메인 실행 (3사 순차)
│   └── build_dashboard.py     # docs/index.html 생성
├── data/
│   └── bestsellers.db         # 누적 데이터 (자동 생성)
├── docs/
│   └── index.html             # GitHub Pages 대시보드 (자동 생성)
├── .github/workflows/
│   └── daily.yml              # 매일 9시(KST) 자동 실행
├── requirements.txt
└── README.md
```

## 셋업 가이드 (10분)

### 1단계 — GitHub 레포 만들기

1. GitHub에서 새 레포 생성 (예: `bestseller-tracker`). Public 추천 (GitHub Pages 무료).
2. 로컬에 다운받은 폴더를 푸시:
   ```bash
   cd bestseller-tracker
   git init
   git add .
   git commit -m "initial setup"
   git branch -M main
   git remote add origin https://github.com/<당신이름>/bestseller-tracker.git
   git push -u origin main
   ```

### 2단계 — GitHub Pages 활성화

레포 페이지에서 **Settings → Pages**:
- **Source**: GitHub Actions
- 저장 후 첫 워크플로우가 실행되면 `https://<당신이름>.github.io/bestseller-tracker/` 에서 대시보드 확인 가능.

### 3단계 — 워크플로우 권한 확인

**Settings → Actions → General → Workflow permissions**:
- ✅ **Read and write permissions** 선택
- ✅ **Allow GitHub Actions to create and approve pull requests** 체크

### 4단계 — 첫 수동 실행

**Actions 탭 → Daily Bestseller Collection → Run workflow** 버튼 클릭.
3~5분 후 완료되면 `data/bestsellers.db`와 `docs/index.html`이 자동 커밋됩니다.

이후엔 매일 **오전 9시(KST)** 에 자동 실행됩니다.

## 로컬에서 테스트하려면

```bash
pip install -r requirements.txt
cd scripts
python run_all.py           # 실제 크롤링 (3사 합쳐서 약 5분 소요)
python build_dashboard.py   # 대시보드 빌드
open ../docs/index.html     # 브라우저로 열기
```

## 대시보드가 보여주는 것

1. **3사 공통 상위권** — 교보·예스24·알라딘 모두 100위 안에 등장한 책. 평균 순위 순으로 정렬되고, 각 서점 순위가 한눈에 비교됩니다. 시장 합의가 높은 책일수록 위에 있습니다.
2. **서점별 단독 등장** — 한 서점에서만 100위에 등장한 책. 서점별 독자 성향 차이를 드러냅니다 (알라딘 인문서 강세, 예스24 자기계발 강세 등).
3. **순위 변동 추이** — 공통 상위 10권의 일자별 순위 그래프. 책별로 칩을 클릭해 전환합니다. 신간이 치고 올라오는 패턴, 떨어지는 책의 하강 속도를 관찰할 수 있습니다.
4. **서점별 베스트 100** — 각 서점의 그날 100위 전체 목록 (탭 전환).

## 셀렉터 유지보수

서점 사이트가 리뉴얼되면 크롤러가 깨질 수 있습니다. 그럴 땐:

- `scripts/scraper_<store>.py` 상단의 `SELECTORS` 딕셔너리만 수정하면 됩니다.
- 변경 확인 방법: 해당 사이트를 브라우저에서 열고 개발자 도구로 책 리스트의 HTML 구조 확인 → CSS 셀렉터 업데이트.
- GitHub Actions가 실패하면 이메일로 알림이 옵니다 (기본 활성).

## 데이터 추가 분석 (옵션)

`data/bestsellers.db`는 표준 SQLite 파일입니다. DBeaver, TablePlus, 또는 Python의 pandas로 직접 분석 가능:

```python
import sqlite3, pandas as pd
df = pd.read_sql("SELECT * FROM bestsellers", sqlite3.connect("data/bestsellers.db"))
# 예: 출판사별 평균 순위
df.groupby("publisher")["rank"].mean().sort_values().head(20)
```

## 주의사항

- 베스트셀러 페이지의 robots.txt를 존중하며, 요청 간 1.5초 딜레이를 둡니다. 개인 분석·내부 참고용으로만 사용하세요.
- 수집 데이터의 **재배포·상업적 이용은 금지**됩니다 (각 서점의 데이터 권리).
- 사이트 구조 변경, IP 차단 등으로 일시적 실패가 발생할 수 있습니다.
