#!/usr/bin/env python3
"""
scene.html 을 프레임 단위로 시크하며 캡처해 세로형 MP4 로 인코딩한다.

브라우저의 CSS 애니메이션을 쓰지 않고 매 프레임 __seek(t) 로 상태를 직접 계산하므로
렌더 속도와 무관하게 타이밍이 정확하다(드랍 프레임 없음).

  python3 src/render.py                 # 전체 67초
  python3 src/render.py --preview       # 1초 간격 컨택트 시트만
  python3 src/render.py --from 4 --to 11  # 구간만 렌더
"""
from __future__ import annotations

import argparse
import glob
import os
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
LAYERS = ROOT / "build" / "layers"
OUTDIR = ROOT / "out"

CHROME = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
CHROME = CHROME[-1] if CHROME else None


def open_page(pw, w: int, h: int):
    browser = pw.chromium.launch(
        executable_path=CHROME,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--force-color-profile=srgb",
            "--disable-lcd-text",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
        ],
    )
    page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    page.goto((ROOT / "src" / "scene.html").as_uri())
    meta = json.loads((LAYERS / "meta.json").read_text(encoding="utf-8"))
    page.evaluate(
        "async ([meta, base]) => { await window.__build(meta, base); }",
        [meta, LAYERS.as_uri() + "/"],
    )
    page.wait_for_function("window.__ready && window.__ready()", timeout=120_000)
    return browser, page


def count_frames(ff: str, path: Path) -> int:
    """
    인코딩된 파일의 실제 프레임 수를 센다.
    -c copy 로는 frame= 카운터가 나오지 않으므로 실제로 디코드한다 (67초에 약 4초).
    """
    r = subprocess.run(
        [ff, "-hide_banner", "-v", "error", "-stats", "-i", str(path),
         "-map", "0:v", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    last = 0
    for m in re.finditer(r"frame=\s*(\d+)", r.stderr):
        last = int(m.group(1))
    return last


def encode_cmd(ff: str, fps: int, crf: int, dst: Path) -> list[str]:
    return [
        ff, "-y", "-loglevel", "error",
        "-f", "image2pipe", "-vcodec", "png", "-framerate", str(fps), "-i", "pipe:0",
        "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
        "-profile:v", "high", "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-x264-params", f"keyint={fps*2}:min-keyint={fps}:scenecut=0",
        "-movflags", "+faststart",
        "-r", str(fps),
        str(dst),
    ]


def render_chunk(job: tuple) -> str:
    """프레임 구간 하나를 렌더해 세그먼트 MP4 로 인코딩한다 (워커 프로세스에서 실행)."""
    idx, t0, i0, count, fps, crf, w, h, dst = job
    from playwright.sync_api import sync_playwright

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen(encode_cmd(ff, fps, crf, Path(dst)), stdin=subprocess.PIPE)
    with sync_playwright() as pw:
        browser, page = open_page(pw, w, h)
        for k in range(count):
            page.evaluate("t => window.__seek(t)", t0 + (i0 + k) / fps)
            proc.stdin.write(page.screenshot(type="png", animations="disabled"))
            if k % 60 == 0:
                print(f"    [워커 {idx}] {k}/{count}", flush=True)
        browser.close()
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"워커 {idx} 인코딩 실패")
    return dst


def render(args) -> None:
    meta = json.loads((LAYERS / "meta.json").read_text(encoding="utf-8"))
    c = meta["canvas"]
    W, H, FPS = c["width"], c["height"], c["fps"]
    t0 = args.start if args.start is not None else 0.0
    t1 = args.end if args.end is not None else c["duration"]
    n = int(round((t1 - t0) * FPS))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / args.out
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    jobs = max(1, min(args.jobs, n))

    # 세그먼트는 실행마다 고유한 디렉터리에 쓴다. 같은 이름을 공유하면 렌더가 두 개
    # 겹쳐 돌 때 서로의 파일을 덮어써서, 조용히 잘린 결과물이 나온다.
    tmp = Path(tempfile.mkdtemp(prefix="segs_", dir=OUTDIR))
    try:
        # 프레임 캡처 비용은 사실상 전부 브라우저의 PNG 인코딩이라, 코어 수만큼
        # 프로세스를 띄워 구간을 나눠 렌더한 뒤 세그먼트를 이어 붙인다.
        print(f"렌더 {n} 프레임 ({t0:.2f}s → {t1:.2f}s @ {FPS}fps, {W}x{H}), 워커 {jobs}개")
        bounds = [round(n * i / jobs) for i in range(jobs + 1)]
        segs = [str(tmp / f"seg{i:02d}.mp4") for i in range(jobs)]
        work = [
            (i, t0, bounds[i], bounds[i + 1] - bounds[i], FPS, args.crf, W, H, segs[i])
            for i in range(jobs)
        ]

        if jobs == 1:
            render_chunk(work[0])
        else:
            import multiprocessing as mp

            with mp.get_context("spawn").Pool(jobs) as pool:
                pool.map(render_chunk, work)

        if jobs == 1:
            Path(segs[0]).replace(out)
        else:
            lst = tmp / "concat.txt"
            lst.write_text("".join(f"file '{s}'\n" for s in segs), encoding="utf-8")
            r = subprocess.run(
                [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                 "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)]
            )
            if r.returncode != 0:
                sys.exit("세그먼트 이어붙이기 실패")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 결과물이 실제로 요청한 길이만큼 나왔는지 확인한다. 워커나 이어붙이기가
    # 조용히 실패하면 짧은 영상이 남는데, 재생해 보기 전엔 알아채기 어렵다.
    got = count_frames(ff, out)
    print(f"\n완료 → {out}  ({out.stat().st_size/1e6:.2f} MB)")
    probe = subprocess.run(
        [ff, "-hide_banner", "-i", str(out)], capture_output=True, text=True
    ).stderr
    for line in probe.splitlines():
        if "Duration" in line or "Stream #0" in line:
            print("  " + line.strip())
    if got != n:
        sys.exit(f"\n프레임 수가 맞지 않습니다: {got} (기대값 {n}). 렌더가 중간에 실패했습니다.")
    print(f"  프레임 {got}/{n} 확인")


def preview(args) -> None:
    """1초 간격 스틸을 뽑아 타이밍을 눈으로 확인하기 위한 컨택트 시트."""
    from playwright.sync_api import sync_playwright

    meta = json.loads((LAYERS / "meta.json").read_text(encoding="utf-8"))
    c = meta["canvas"]
    W, H = c["width"], c["height"]
    shots = args.times or [0.0, 1.2, 2.4, 3.6, 4.9, 5.7, 6.6, 7.8, 9.0, 9.9,
                           14.0, 30.0, 50.0, 62.0, 64.5, 66.0, 66.9]
    d = ROOT / "build" / "preview"
    d.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser, page = open_page(pw, W, H)
        for t in shots:
            page.evaluate("t => window.__seek(t)", t)
            page.locator("#stage").screenshot(path=str(d / f"t{t:06.2f}.png"))
            print(f"  t={t:6.2f}s")
        browser.close()
    print(f"프리뷰 → {d}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--times", type=float, nargs="*")
    ap.add_argument("--from", dest="start", type=float, default=None)
    ap.add_argument("--to", dest="end", type=float, default=None)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument("--out", default="sponge-club-3rd-offline.mp4")
    a = ap.parse_args()
    if not (LAYERS / "meta.json").exists():
        sys.exit("먼저 src/extract_layers.py 를 실행해 레이어를 만들어 주세요.")
    (preview if a.preview else render)(a)
