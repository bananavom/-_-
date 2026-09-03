#!/usr/bin/env python3
"""
포스터에서 색상 키로 잡히는 덩어리(글자·낙서·별·하트)의 위치를 자동으로 재서
spec/layout.json 의 sprites 박스를 잡을 때 쓰는 보조 도구.

눈대중으로 좌표를 넣으면 글자가 잘리거나 이웃 요소를 물어서 키잉이 어긋난다.
이 도구는 실제 픽셀에서 덩어리를 찾아 정규화 박스를 뽑아 준다.

  python3 src/measure.py                 # 기본 키 전부
  python3 src/measure.py yellow white    # 특정 키만
  python3 src/measure.py --gap 26        # 덩어리 병합 간격(px) 조정
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from extract_layers import key_alpha  # 추출과 똑같은 키잉 기준을 쓴다

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*", help="검사할 키 (기본: 전부)")
    ap.add_argument("--poster", default=str(ROOT / "assets" / "poster.png"))
    ap.add_argument("--gap", type=int, default=22, help="이 픽셀 이내면 한 덩어리로 묶는다")
    ap.add_argument("--min-area", type=int, default=90, help="이보다 작은 덩어리는 무시")
    a = ap.parse_args()

    spec = json.loads((ROOT / "spec" / "layout.json").read_text(encoding="utf-8"))
    img = np.asarray(Image.open(a.poster).convert("RGB"), np.float32) / 255.0
    H, W = img.shape[:2]
    print(f"원본 {W}x{H}\n")

    for key in (a.keys or ["white", "yellow", "pink", "chalk"]):
        cfg = spec["keys"].get(key)
        if cfg is None:
            print(f"[{key}] 스펙에 없는 키입니다")
            continue
        alpha = key_alpha(img, key, cfg)
        mask = alpha > 0.35
        # 가까운 획끼리 묶어 한 요소로 본다 (글자 낱자가 따로 잡히는 걸 방지)
        merged = ndimage.binary_dilation(mask, np.ones((a.gap, a.gap), bool))
        lab, n = ndimage.label(merged)
        print(f"[{key}] 덩어리 {n}개")
        rows = []
        for i, sl in enumerate(ndimage.find_objects(lab), start=1):
            if sl is None:
                continue
            ys, xs = sl
            # 병합용 팽창을 되돌려 실제 잉크 범위만 남긴다
            sub = mask[ys, xs]
            if sub.sum() < a.min_area:
                continue
            yy, xx = np.nonzero(sub)
            x0, x1 = xs.start + xx.min(), xs.start + xx.max() + 1
            y0, y1 = ys.start + yy.min(), ys.start + yy.max() + 1
            rows.append((y0, x0, x1, y1, int(sub.sum())))
        for y0, x0, x1, y1, area in sorted(rows):
            print(f"   [{x0/W:.3f}, {y0/H:.3f}, {x1/W:.3f}, {y1/H:.3f}]"
                  f"   px({x0},{y0})-({x1},{y1})  {x1-x0}x{y1-y0}  잉크 {area}")
        print()


if __name__ == "__main__":
    main()
