#!/usr/bin/env python3
"""
원본 포스터 1장을 애니메이션 가능한 레이어로 분해한다.

출력 (build/layers/):
  plate.png        원본에서 글자/낙서/테이프를 지우고(인페인팅) 남긴 사진 콜라주 판
  tile_<id>.png    plate 를 사진 영역별로 페더(부드러운 가장자리) 크롭한 조각
  sp_<id>.png      원본에서 색상 키잉으로 뜬 글자/낙서/테이프 스프라이트 (RGBA)
  meta.json        씬이 읽는 픽셀 단위 기하 정보

핵심 보장: 모든 레이어가 정지 상태(scale 1, opacity 1)일 때 합성 결과는 원본 포스터와
동일하다. 타일은 plate 의 크롭이고 plate 위에 같은 자리로 얹히며, 지워진 글자 자리는
원본에서 뜬 스프라이트가 정확히 덮는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec" / "layout.json"
OUT = ROOT / "build" / "layers"


# ---------------------------------------------------------------- helpers
def smoothstep(lo: float, hi: float, x: np.ndarray) -> np.ndarray:
    if hi == lo:
        return (x >= hi).astype(np.float32)
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rgb_to_hsv(rgb: np.ndarray):
    """rgb float 0..1, shape (H,W,3) -> h 0..360, s 0..1, v 0..1"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-6
    with np.errstate(invalid="ignore"):
        rm = nz & (mx == r)
        gm = nz & (mx == g) & ~rm
        bm = nz & (mx == b) & ~rm & ~gm
        h[rm] = ((g - b)[rm] / d[rm]) % 6.0
        h[gm] = ((b - r)[gm] / d[gm]) + 2.0
        h[bm] = ((r - g)[bm] / d[bm]) + 4.0
    h *= 60.0
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def blur(a: np.ndarray, radius: float) -> np.ndarray:
    """가우시안 블러. 2D 또는 3D float 배열."""
    if radius <= 0:
        return a
    if a.ndim == 2:
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L")
        return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255.0
    chans = [blur(a[..., i], radius) for i in range(a.shape[2])]
    return np.stack(chans, -1)


def dilate(mask: np.ndarray, px: int) -> np.ndarray:
    """binary/float 마스크를 px 만큼 팽창."""
    if px <= 0:
        return mask
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "L")
    remaining = px
    while remaining > 0:
        k = min(9, remaining * 2 + 1)
        if k % 2 == 0:
            k += 1
        im = im.filter(ImageFilter.MaxFilter(k))
        remaining -= (k - 1) // 2
    return np.asarray(im, np.float32) / 255.0


def drop_small_components(binary: np.ndarray, min_area: int) -> np.ndarray:
    """면적이 min_area 미만인 덩어리를 제거 (사진 속 밝은 점이 글자로 오인되는 것 방지)."""
    if min_area <= 1 or not binary.any():
        return binary
    h, w = binary.shape
    label = np.full((h, w), -1, np.int32)
    keep = np.zeros((h, w), bool)
    flat = binary.ravel()
    lab = label.ravel()
    stack: list[int] = []
    nxt = 0
    for start in np.flatnonzero(flat):
        if lab[start] != -1:
            continue
        stack.append(int(start))
        lab[start] = nxt
        comp = [int(start)]
        while stack:
            p = stack.pop()
            y, x = divmod(p, w)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        q = ny * w + nx
                        if flat[q] and lab[q] == -1:
                            lab[q] = nxt
                            stack.append(q)
                            comp.append(q)
        if len(comp) >= min_area:
            keep.ravel()[comp] = True
        nxt += 1
    return keep


# ---------------------------------------------------------------- inpaint
def pushpull_inpaint(rgb: np.ndarray, known: np.ndarray) -> np.ndarray:
    """
    피라미드 push-pull 로 known=0 인 구멍을 주변 색으로 매끄럽게 메운다.
    글자 뒤 배경은 어둡고 저주파라서 이 방식으로 충분히 자연스럽다.
    """
    levels = []
    c = rgb * known[..., None]
    w = known.astype(np.float32)
    levels.append((c, w))
    while min(w.shape) > 4:
        h, ww = w.shape
        hp, wp = h + (h & 1), ww + (ww & 1)
        cp = np.zeros((hp, wp, 3), np.float32)
        wp_ = np.zeros((hp, wp), np.float32)
        cp[:h, :ww] = c
        wp_[:h, :ww] = w
        c = cp.reshape(hp // 2, 2, wp // 2, 2, 3).sum((1, 3)) / 4.0
        w = wp_.reshape(hp // 2, 2, wp // 2, 2).sum((1, 3)) / 4.0
        levels.append((c, w))

    def upsample(a: np.ndarray, h: int, w: int) -> np.ndarray:
        """양선형 업샘플. 최근접으로 올리면 계단 모양 블록 아티팩트가 남는다."""
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB")
        return np.asarray(im.resize((w, h), Image.BILINEAR), np.float32) / 255.0

    c, w = levels[-1]
    filled = c / np.maximum(w, 1e-5)[..., None]
    for c, w in reversed(levels[:-1]):
        h, ww = w.shape
        up = upsample(filled, h, ww)
        own = c / np.maximum(w, 1e-5)[..., None]
        a = np.clip(w, 0.0, 1.0)[..., None]
        filled = a * own + (1.0 - a) * up
    return np.clip(blur(filled, 2.5), 0.0, 1.0)


# ---------------------------------------------------------------- keying
def key_alpha(crop: np.ndarray, key: str, cfg: dict) -> np.ndarray:
    """crop: float 0..1 (H,W,3) -> alpha 0..1"""
    if key == "rect":
        return np.ones(crop.shape[:2], np.float32)

    h, s, v = rgb_to_hsv(crop)
    lum = 0.2126 * crop[..., 0] + 0.7152 * crop[..., 1] + 0.0722 * crop[..., 2]

    # 키 종류는 이름이 아니라 설정 모양으로 정한다 (스펙에 새 키를 넣어도 그대로 동작).
    if "lum" in cfg:
        lo, hi = cfg["lum"]
        a = smoothstep(lo, hi, lum)
        smax = cfg["sat_max"]
        a *= 1.0 - smoothstep(smax, smax + 0.16, s)
    else:  # hue keyed (yellow / pink)
        h0, h1 = cfg["hue"]
        hh = h.copy()
        if h1 > 360.0:  # pink wraps past 360
            hh = np.where(hh < (h1 - 360.0), hh + 360.0, hh)
        mid, half = (h0 + h1) / 2.0, (h1 - h0) / 2.0
        d = np.abs(hh - mid)
        a = 1.0 - smoothstep(half - 6.0, half + 6.0, d)
        a *= smoothstep(cfg["sat_min"] - 0.10, cfg["sat_min"] + 0.10, s)
        a *= smoothstep(cfg["val_min"] - 0.10, cfg["val_min"] + 0.10, v)

    core = drop_small_components(a > 0.35, int(cfg.get("min_area", 24)))
    gate = blur(dilate(core.astype(np.float32), 2), 1.6)
    return np.clip(a * np.clip(gate * 1.35, 0.0, 1.0), 0.0, 1.0)


# ---------------------------------------------------------------- tiles
def feather_alpha(w: int, h: int, f: int) -> np.ndarray:
    """가장자리 f px 를 선형으로 떨어뜨린 사각 알파."""
    xs = np.minimum(np.arange(w), w - 1 - np.arange(w)).astype(np.float32)
    ys = np.minimum(np.arange(h), h - 1 - np.arange(h)).astype(np.float32)
    ax = np.clip(xs / max(f, 1), 0, 1)
    ay = np.clip(ys / max(f, 1), 0, 1)
    a = np.minimum(ax[None, :], ay[:, None])
    return a * a * (3.0 - 2.0 * a)


# ---------------------------------------------------------------- main
def main(poster_path: Path) -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    CW, CH = spec["canvas"]["width"], spec["canvas"]["height"]

    src = Image.open(poster_path).convert("RGB")
    # 9:16 으로 커버 크롭 후 캔버스 해상도에 정확히 맞춘다.
    tw, th = CW / CH, src.width / src.height
    if abs(th - tw) > 1e-3:
        if th > tw:
            nw = int(round(src.height * tw))
            src = src.crop(((src.width - nw) // 2, 0, (src.width - nw) // 2 + nw, src.height))
        else:
            nh = int(round(src.width / tw))
            src = src.crop((0, (src.height - nh) // 2, src.width, (src.height - nh) // 2 + nh))
    src = src.resize((CW, CH), Image.LANCZOS)
    img = np.asarray(src, np.float32) / 255.0

    OUT.mkdir(parents=True, exist_ok=True)
    meta: dict = {"canvas": spec["canvas"], "photos": [], "sprites": [], "timeline": spec["timeline"]}

    # --- 1. 스프라이트 키잉 -------------------------------------------------
    # 글자에는 대개 드롭섀도/글로우가 딸려 있다. 획만 오려내면 판에는 그림자가 남고
    # 스프라이트는 그림자를 잃어서, 정지 상태에서도 원본과 어긋난다.
    # 그래서 스프라이트 알파를 "획 + 그림자"를 덮는 부드러운 덩어리로 잡는다.
    halo = int(spec.get("inpaint", {}).get("halo", 12))

    cores: dict[str, np.ndarray] = {}
    for sp in spec["sprites"]:
        x0, y0, x1, y1 = sp["box"]
        px0, py0 = max(0, int(x0 * CW) - 6), max(0, int(y0 * CH) - 6)
        px1, py1 = min(CW, int(x1 * CW) + 6), min(CH, int(y1 * CH) + 6)
        cfg = spec["keys"].get(sp["key"], {})
        a = key_alpha(img[py0:py1, px0:px1], sp["key"], cfg)
        full = np.zeros((CH, CW), np.float32)
        full[py0:py1, px0:px1] = a
        cores[sp["id"]] = full

    core_any = np.zeros((CH, CW), np.float32)
    blobs: dict[str, np.ndarray] = {}
    for sid, c in cores.items():
        hard = (c > 0.02).astype(np.float32)
        b = np.clip(blur(dilate(hard, halo), halo * 0.6) * 1.35, 0, 1)
        blobs[sid] = b
        core_any = np.maximum(core_any, b)

    for sp in spec["sprites"]:
        sid = sp["id"]
        # 이웃 글자의 획은 내 덩어리에서 빼낸다 (타이틀이 올라올 때 옆 글자를 끌고
        # 올라가지 않도록). 뺀 자리는 이웃 스프라이트가 직접 그린다.
        others = np.zeros((CH, CW), np.float32)
        for oid, oc in cores.items():
            if oid != sid:
                others = np.maximum(others, dilate((oc > 0.02).astype(np.float32), 3))
        alpha = np.clip(blobs[sid] * (1.0 - others), 0, 1)

        ys, xs = np.nonzero(alpha > 0.004)
        if len(xs) == 0:
            print(f"  ! sprite {sid}: 키잉 결과가 비었습니다 — box/key 를 확인하세요")
            continue
        cx0, cx1 = max(0, xs.min() - 2), min(CW, xs.max() + 3)
        cy0, cy1 = max(0, ys.min() - 2), min(CH, ys.max() + 3)
        a = alpha[cy0:cy1, cx0:cx1]

        rgba = np.zeros((*a.shape, 4), np.uint8)
        rgba[..., :3] = (img[cy0:cy1, cx0:cx1] * 255).round().astype(np.uint8)
        rgba[..., 3] = (a * 255).round().astype(np.uint8)
        fn = f"sp_{sid}.png"
        Image.fromarray(rgba, "RGBA").save(OUT / fn)

        meta["sprites"].append(
            {
                "id": sid,
                "motion": sp.get("motion", "fade_rise"),
                "file": fn,
                "x": int(cx0),
                "y": int(cy0),
                "w": int(cx1 - cx0),
                "h": int(cy1 - cy0),
                "cover": float(a.mean()),
            }
        )
        print(f"  sprite {sid:<12} {cx1-cx0:>4}x{cy1-cy0:<4} cover={a.mean():.3f}")

    # --- 2. 클린 플레이트 (스프라이트 자리 인페인팅) ------------------------
    # 판에서 파내는 영역 = 스프라이트가 덮는 영역. 두 영역이 일치해야 정지 상태에서
    # 스프라이트를 얹었을 때 원본이 그대로 복원된다.
    known = 1.0 - (core_any > 0.5).astype(np.float32)
    filled = pushpull_inpaint(img, known)
    a3 = core_any[..., None]
    plate = np.clip(img * (1 - a3) + filled * a3, 0, 1)
    holem = core_any
    plate_u8 = (plate * 255).round().astype(np.uint8)
    Image.fromarray(plate_u8, "RGB").save(OUT / "plate.png")
    print(f"  plate.png  (인페인팅 면적 {holem.mean()*100:.2f}%)")

    # --- 3. 사진 타일 -------------------------------------------------------
    for ph in spec["photos"]:
        x0, y0, x1, y1 = ph["box"]
        f = int(ph.get("feather", 26))
        px0, py0 = max(0, int(x0 * CW) - f), max(0, int(y0 * CH) - f)
        px1, py1 = min(CW, int(x1 * CW) + f), min(CH, int(y1 * CH) + f)
        w, h = px1 - px0, py1 - py0
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[..., :3] = plate_u8[py0:py1, px0:px1]
        rgba[..., 3] = (feather_alpha(w, h, f) * 255).round().astype(np.uint8)
        fn = f"tile_{ph['id']}.png"
        Image.fromarray(rgba, "RGBA").save(OUT / fn)
        meta["photos"].append(
            {
                "id": ph["id"],
                "file": fn,
                "x": px0,
                "y": py0,
                "w": w,
                "h": h,
                "wave": ph.get("wave", 0),
                "kenburns": ph.get("kenburns"),
            }
        )
    print(f"  tiles      {len(spec['photos'])}장")

    # --- 4. 종이(배경) 색 ---------------------------------------------------
    lum = plate.mean(-1)
    dark = plate.reshape(-1, 3)[lum.ravel() <= np.percentile(lum, 4)]
    paper = (dark.mean(0) * 255).round().astype(int).tolist()
    meta["paper"] = "#%02x%02x%02x" % tuple(paper)
    print(f"  paper      {meta['paper']}")

    # 어두운 그라데이션의 H.264 밴딩을 눌러주는 그레인 타일 (실시간 필터 대신 정적 PNG)
    rng = np.random.default_rng(7)
    g = rng.normal(128, 26, (256, 256)).clip(0, 255).astype(np.uint8)
    Image.fromarray(g, "L").convert("RGB").save(OUT / "grain.png")

    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n레이어 분해 완료 → {OUT}")


if __name__ == "__main__":
    poster = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "poster.png"
    if not poster.exists():
        sys.exit(f"원본 포스터를 찾을 수 없습니다: {poster}")
    print(f"원본: {poster}")
    main(poster)
