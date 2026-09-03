#!/usr/bin/env bash
# 스폰지클럽 3기 오프라인 모임 · 67초 세로형 모션 포스터
#
#   ./run.sh                     assets/poster.png 으로 전체 렌더
#   ./run.sh path/to/poster.png  다른 원본으로 렌더
#   ./run.sh --preview           스틸 컨택트 시트만 (타이밍 확인용)
set -euo pipefail
cd "$(dirname "$0")"

POSTER="assets/poster.png"
PREVIEW=""
for a in "$@"; do
  case "$a" in
    --preview) PREVIEW="--preview" ;;
    *) POSTER="$a" ;;
  esac
done

if [ ! -f "$POSTER" ]; then
  echo "원본 포스터가 없습니다: $POSTER"
  echo "  → 원본을 assets/poster.png 로 넣거나, 경로를 인자로 넘겨 주세요."
  echo "  → 원본 없이 파이프라인만 확인하려면: python3 src/make_reference_poster.py"
  exit 1
fi

echo "▸ 1/2  레이어 분해"
python3 src/extract_layers.py "$POSTER"

echo "▸ 2/2  렌더"
python3 src/render.py $PREVIEW
