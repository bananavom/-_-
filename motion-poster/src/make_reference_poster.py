#!/usr/bin/env python3
"""
원본 포스터(assets/poster.png)가 아직 없을 때 쓰는 **대역 포스터** 생성기.

원본과 동일한 9:16 캔버스에, spec/layout.json 과 동일한 좌표로 사진 셀·찢어진 종이
가장자리·테이프·타이포그래피를 배치한다. 사진 자리는 실제 인물 사진 대신 자리표시용
블록이 들어간다. 파이프라인(키잉 → 인페인팅 → 타일 → 렌더)을 원본 없이 검증하고
모션 타이밍을 눈으로 확인하기 위한 용도다.

원본 poster.png 를 넣으면 이 스크립트는 더 이상 쓰지 않는다.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / "spec" / "layout.json").read_text(encoding="utf-8"))
W, H = SPEC["canvas"]["width"], SPEC["canvas"]["height"]

FONT_DIR = ROOT / "assets" / "fonts"
_WEIGHTS = {"Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800}
_FACES = [
    f'@font-face {{ font-family:P; src:url("{(FONT_DIR / f"Pretendard-{n}.otf").as_uri()}"); '
    f"font-weight:{w} }}"
    for n, w in _WEIGHTS.items()
    if (FONT_DIR / f"Pretendard-{n}.otf").exists()
]
FACE_CSS = "\n".join(_FACES)
if not _FACES:
    print("경고: assets/fonts 에 Pretendard 가 없어 시스템 기본 글꼴로 대체합니다.\n"
          "      (대역 포스터의 한글이 어색해 보일 수 있습니다. 파이프라인 동작에는 영향 없음)\n"
          "      https://github.com/orioncactus/pretendard 에서 받아 assets/fonts 에 두세요.")

# 자리표시용 사진 셀: (색조 A, 색조 B, 회전각)
CELL_TONE = [
    ("#3b3a36", "#1b1a17", -0.8), ("#26303f", "#12161d", 0.6),
    ("#333029", "#191712", 1.1), ("#2f3338", "#16181b", -0.7),
    ("#3a352c", "#1c1a15", 0.9), ("#2b2f33", "#141618", -1.2),
    ("#38322a", "#1a1714", 0.8), ("#2e3239", "#15171b", -0.5),
    ("#37342d", "#1a1815", 1.0), ("#3f3a30", "#1d1a15", -0.4),
    ("#2d3136", "#14161a", 0.7), ("#39332b", "#1b1813", -0.9),
    ("#31352b", "#171912", 0.5), ("#343029", "#181613", -1.1),
    ("#2c3037", "#14161a", 0.9),
]


def cells_html() -> str:
    out = []
    for i, ph in enumerate(SPEC["photos"]):
        x0, y0, x1, y1 = ph["box"]
        a, b, rot = CELL_TONE[i % len(CELL_TONE)]
        L, T = x0 * W, y0 * H
        Wd, Ht = (x1 - x0) * W, (y1 - y0) * H
        # 실내 사진처럼 보이도록 몇 개의 흐릿한 덩어리를 얹는다
        blobs = "".join(
            f'<div class="blob" style="left:{(7+j*23)%78}%;top:{(18+j*29)%62}%;'
            f'width:{16+((j*13)%18)}%;height:{26+((j*11)%26)}%;'
            f'opacity:{0.10+0.05*((j*7)%4)}"></div>'
            for j in range(6)
        )
        out.append(
            f'<div class="cell" style="left:{L:.1f}px;top:{T:.1f}px;'
            f'width:{Wd:.1f}px;height:{Ht:.1f}px;transform:rotate({rot}deg)">'
            f'<div class="photo" style="background:'
            f'radial-gradient(120% 90% at 30% 22%, {a}, {b} 78%)">{blobs}'
            f'<div class="glare"></div></div></div>'
        )
    return "\n".join(out)


HTML = f"""<!doctype html><meta charset="utf-8">
<style>
{FACE_CSS}
* {{ margin:0; padding:0; box-sizing:border-box }}
body {{ background:#000 }}
#p {{ position:relative; width:{W}px; height:{H}px; overflow:hidden;
      background:#15120f; font-family:P, sans-serif }}

/* ── 찢어진 종이 사진 셀 ── */
.cell {{ position:absolute; padding:9px; background:#efe9dd;
         filter:url(#torn) drop-shadow(0 6px 14px rgba(0,0,0,.55)) }}
.photo {{ position:relative; width:100%; height:100%; overflow:hidden }}
.blob {{ position:absolute; border-radius:50%; background:#cfd6dd; filter:blur(16px) }}
.glare {{ position:absolute; inset:0;
          background:linear-gradient(160deg, rgba(255,255,255,.10), rgba(255,255,255,0) 55%) }}
/* 콜라주 전체를 어둡게 눌러 글자가 읽히게 (원본 포스터와 같은 처리) */
#dim {{ position:absolute; inset:0; background:
        radial-gradient(78% 46% at 50% 45%, rgba(0,0,0,.72), rgba(0,0,0,.34) 70%, rgba(0,0,0,.46));
        pointer-events:none }}

.t {{ position:absolute; white-space:nowrap; transform:translate(-50%,-50%) }}
#title1 {{ left:50%; top:37.0%; font-weight:800; font-size:89px; color:#fff; letter-spacing:-2px;
           text-shadow:0 4px 18px rgba(0,0,0,.6) }}
#title2 {{ left:50%; top:44.0%; font-weight:800; font-size:120px; color:#F3C74B; letter-spacing:-3px;
           text-shadow:0 5px 20px rgba(0,0,0,.6) }}
#sub1 {{ left:50%; top:53.6%; font-weight:500; font-size:40px; color:#f2efe9; letter-spacing:-.5px }}
#sub2 {{ left:50%; top:58.2%; font-weight:500; font-size:45px; color:#f2efe9; letter-spacing:-.5px }}
#tape {{ left:50%; top:63.1%; transform:translate(-50%,-50%) rotate(-.6deg);
         padding:13px 34px 15px; background:#e8e2d6; color:#241f1a;
         font-weight:600; font-size:34px; letter-spacing:3px;
         filter:url(#torn) drop-shadow(0 4px 10px rgba(0,0,0,.5)) }}
.doodle {{ position:absolute; color:#e6e2d8; font-weight:500; font-style:italic;
           opacity:.82; letter-spacing:1px; line-height:1.18 }}
#d_bt {{ left:4.6%; top:6.2%;  font-size:40px }}
#d_gv {{ left:3.4%; top:79.0%; font-size:40px }}
#d_sc {{ left:77.6%; top:89.4%; font-size:40px }}
svg.ov {{ position:absolute; inset:0; width:{W}px; height:{H}px; overflow:visible }}
</style>

<div id="p">
  <svg class="ov" style="position:absolute;width:0;height:0">
    <filter id="torn">
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="4" seed="7" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="11" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </svg>

  {cells_html()}
  <div id="dim"></div>

  <div class="t" id="title1">스폰지클럽 3기</div>
  <div class="t" id="title2">오프라인 모임</div>
  <div class="t" id="sub1">온라인에서 함께한 우리,</div>
  <div class="t" id="sub2">드디어 만나요.</div>
  <div class="t" id="tape">2026. 09. 05 SAT</div>

  <div class="doodle" id="d_bt">Better<br>Together ♡</div>
  <div class="doodle" id="d_gv">Good<br>Vibes ☺</div>
  <div class="doodle" id="d_sc">Sponge<br>Club ♡</div>

  <svg class="ov" viewBox="0 0 {W} {H}">
    <!-- 노란 밑줄 (손으로 그은 획) -->
    <path d="M 178 944 C 380 924, 700 926, 908 940" stroke="#F3C74B" stroke-width="9"
          fill="none" stroke-linecap="round"/>
    <!-- 드디어를 감싼 손그림 원 -->
    <ellipse cx="447" cy="1117" rx="88" ry="37" stroke="#F3C74B" stroke-width="6"
             fill="none" transform="rotate(-2 447 1117)"/>
    <!-- 핑크 하트 · 사선 -->
    <path d="M 995 900 c -14 -16 -34 -4 -26 12 c 6 12 26 24 26 24 s 20 -12 26 -24 c 8 -16 -12 -28 -26 -12 z"
          fill="#F49BB4"/>
    <path d="M 762 1108 c -11 -13 -27 -3 -21 10 c 5 9 21 19 21 19 s 16 -10 21 -19 c 6 -13 -10 -23 -21 -10 z"
          fill="#F49BB4"/>
    <g stroke="#F49BB4" stroke-width="7" stroke-linecap="round">
      <path d="M 78 800 L 96 768"/><path d="M 104 796 L 122 764"/><path d="M 130 792 L 148 760"/>
    </g>
    <!-- 별 (한 번만 반짝일 별들) -->
    <g fill="none" stroke-width="5" stroke-linejoin="round" transform="translate(-25,172)">
      <path d="M 454 262 l 12 -30 l 12 30 l 30 12 l -30 12 l -12 30 l -12 -30 l -30 -12 z"
            stroke="#efeae0"/>
      <path d="M 629 281 l 13 -32 l 13 32 l 32 13 l -32 13 l -13 32 l -13 -32 l -32 -13 z"
            stroke="#F3C74B"/>
      <path d="M 666 313 l 11 -27 l 11 27 l 27 11 l -27 11 l -11 27 l -11 -27 l -27 -11 z"
            stroke="#F3C74B"/>
    </g>
  </svg>
</div>
"""


def main() -> None:
    from playwright.sync_api import sync_playwright

    chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))[-1]
    dst = ROOT / "assets" / "poster.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "build" / "_refposter.html"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(HTML, encoding="utf-8")

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=chrome,
                               args=["--no-sandbox", "--disable-dev-shm-usage",
                                     "--force-color-profile=srgb", "--hide-scrollbars"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(700)
        pg.locator("#p").screenshot(path=str(dst))
        b.close()
    print(f"대역 포스터 생성 → {dst}  ({W}x{H})")


if __name__ == "__main__":
    main()
