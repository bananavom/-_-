#!/usr/bin/env python3
"""
같은 레이어로 다른 연출을 만든다.

포스터를 분해한 결과(plate·타일·스프라이트)는 연출이 달라져도 그대로다. 달라지는 건
등장 순서·타이밍·Ken Burns 세기·소멸 순서뿐이라, 레이어를 다시 뽑거나 복사하지 않고
meta.json 위에 덮어쓴 사본만 만든다.

  python3 src/make_variant.py b        # spec/variant-b.json → build/layers/meta-b.json
  python3 src/render.py --meta meta-b.json --out ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYERS = ROOT / "build" / "layers"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", help="연출 이름 (spec/variant-<이름>.json 을 읽는다)")
    ap.add_argument("--base", default="meta.json", help="바탕이 되는 meta 파일명")
    a = ap.parse_args()

    base_path = LAYERS / a.base
    spec_path = ROOT / "spec" / f"variant-{a.variant}.json"
    if not base_path.exists():
        sys.exit(f"먼저 src/extract_layers.py 를 실행해 주세요 ({base_path} 없음)")
    if not spec_path.exists():
        sys.exit(f"연출 스펙이 없습니다: {spec_path}")

    meta = json.loads(base_path.read_text(encoding="utf-8"))
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    ids = {p["id"] for p in meta["photos"]}
    waves = spec.get("photo_wave", {})
    kb = spec.get("kenburns", {})
    for unknown in (set(waves) | set(kb)) - ids:
        sys.exit(f"연출 스펙이 모르는 사진을 가리킵니다: {unknown}")

    for ph in meta["photos"]:
        if ph["id"] in waves:
            ph["wave"] = waves[ph["id"]]
        # kenburns 는 스펙에 적힌 사진만 갖는다 (안 적힌 사진은 정지).
        ph["kenburns"] = kb.get(ph["id"])

    meta["timeline"] = {**meta["timeline"], **spec.get("timeline", {})}
    if "outro_order" in spec:
        meta["outro_order"] = spec["outro_order"]

    # 소멸 순서에 빠진 요소가 있으면 끝까지 남아 루프가 깨진다. 씬에서도 막지만
    # 렌더를 11분 돌리기 전에 여기서 먼저 걸러 준다.
    listed = {k for g in meta.get("outro_order", []) for k in g}
    if listed:
        missing = [s["id"] for s in meta["sprites"] if s["id"] not in listed]
        missing += [f"@tile{w}" for w in sorted({p["wave"] for p in meta["photos"]})
                    if f"@tile{w}" not in listed]
        if "@plate" not in listed:
            missing.append("@plate")
        if missing:
            sys.exit(f"outro_order 에 빠진 항목: {', '.join(missing)}")

    dst = LAYERS / f"meta-{a.variant}.json"
    dst.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    tl = meta["timeline"]
    nwave = len({p["wave"] for p in meta["photos"]})
    print(f"연출 '{a.variant}' → {dst}")
    print(f"  사진 웨이브 {nwave}개, tiles {tl['tiles']['start']}s 부터 "
          f"{tl['tiles']['wave_gap']}s 간격")
    print(f"  Ken Burns: {[p['id'] for p in meta['photos'] if p['kenburns']]}")
    print(f"  아웃트로 그룹 {len(meta.get('outro_order', []))}개")


if __name__ == "__main__":
    main()
