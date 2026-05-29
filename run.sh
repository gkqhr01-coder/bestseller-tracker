#!/bin/bash
#
# 베스트셀러 수집 → 대시보드 생성 → GitHub 업로드까지 한 번에.
# 맥 터미널에서 실행:  bash run.sh
#
# 자동 실행(launchd) 설정 전, 이 스크립트로 수동 실행해보며 확인하세요.

# 이 스크립트가 있는 폴더로 이동 (어디서 실행하든 안전)
cd "$(dirname "$0")" || exit 1

echo "=================================================="
echo " 베스트셀러 수집 시작: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================="

# 1) 크롤링 + DB 적재 + 대시보드 생성
cd scripts || exit 1
python3 run_all.py
echo ""
python3 build_dashboard.py
cd ..

# 2) GitHub에 업로드 (data/ 와 docs/ 변경분)
echo ""
echo "▶ GitHub 업로드 중..."
git add data/ docs/
if git diff --staged --quiet; then
    echo "  변경사항 없음 (업로드 생략)"
else
    git commit -m "data: $(date '+%Y-%m-%d') 수집"
    git push
    echo "  ✓ 업로드 완료"
fi

echo ""
echo "=================================================="
echo " 완료! 대시보드: https://gkqhr01-coder.github.io/bestseller-tracker/"
echo "=================================================="
