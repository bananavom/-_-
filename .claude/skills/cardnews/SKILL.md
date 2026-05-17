---
name: cardnews
description: 옵시디언 미션 제출(.md)을 1080×1080 인스타 카드뉴스(8장, 단일 HTML)로 변환. AAA Selfmarketing Design System v1.0 적용. 사용자: 스폰지클럽·셀피쉬클럽 크루. 트리거: "카드뉴스 만들어줘", "/cardnews <파일경로>", "submit.md를 인스타용으로".
---

# Obsidian Cardnews Skill

옵시디언에 올라온 미션 제출(.md)을 받아서 **인스타그램용 1080×1080 카드뉴스 8장**을 **단일 HTML 파일**로 만든다. AAA Selfmarketing Design System v1.0을 그대로 따르며, 스폰지클럽 1기 운영을 위해 마스코트·푸터를 추가했다.

## 호출 방식

- 슬래시 커맨드: `/cardnews <submit.md 경로>`
- 자연어: "이 submit 파일을 카드뉴스로 만들어줘" + 파일 경로

## 입력 → 출력

**입력**: 옵시디언 미션 제출 마크다운 파일 1개
- 예: `02_mission/1주차_0510/5조/5조_오웬_1주차_submit.md`

**출력 (vault의 `05_카드뉴스/{N}주차/{X}조/` 폴더에 2개 파일)**:
1. `{원본이름}_cardnews.html` — 자립형 8장 캐러셀 (base64 인라인, 어디서든 동작)
2. `{원본이름}_cardnews.md` — 옵시디언 노트 (frontmatter + 인스타 캡션 + 슬라이드 카피 + 체크리스트)

예시:
```
입력:  02_mission/1주차_0510/5조/5조_오웬_1주차_submit.md
출력:  05_카드뉴스/1주차/5조/5조_오웬_1주차_cardnews.html
       05_카드뉴스/1주차/5조/5조_오웬_1주차_cardnews.md
```

폴더가 없으면 자동 생성 (`mkdir -p`).

---

## 실행 절차

### 1단계 · 경로 파싱

`$ARGUMENTS`에서 받은 파일 경로에서 메타데이터를 추출한다.

기본 컨벤션 (스폰지클럽):
```
{vault}/02_mission/{N}주차_{날짜}/{X}조/{X}조_{이름}_{N}주차_submit.md
```

추출 결과 예시:
- 브랜드: 스폰지클럽 1기 (vault 이름이 `spongeclub_*`이면)
- 주차: `1` (또는 zero-padded `01`)
- 날짜: `2026.05.10` (날짜 부분에서 추정)
- 조: `5조`
- 이름: `오웬`

**출력 경로 계산**:
- 출력 디렉토리: `{vault}/05_카드뉴스/{N}주차/{X}조/`
- 디렉토리 없으면 `mkdir -p` 로 자동 생성

> 경로 컨벤션이 다르면 사용자에게 메타데이터를 직접 확인받는다.

### 2단계 · 본인 캐릭터 확인 / 등록

캐릭터(마스코트) 관리는 `{vault}/05_카드뉴스/.cardnews-mascots.json` 파일에서 한다.

```json
{
  "오웬": "_mascots/오웬.png",
  "비비안": "_mascots/비비안.png"
}
```

**절차**:

1. `.cardnews-mascots.json` 파일이 있으면 읽고, 본인 이름(1단계에서 파싱)이 키로 등록되어 있는지 확인
2. **이미 등록**되어 있으면 → 해당 PNG 경로 사용 (다음 단계 진행)
3. **등록 안 됨** → 사용자에게 물어본다:

   ```
   {이름}님의 개인 캐릭터가 아직 등록 안 됐어요.
   sponge-dressup (https://sponge-dressup.vercel.app) 에서 만든 캐릭터 PNG 파일 경로를 알려주세요.
   
   예: ~/Downloads/sponge-OWEN.png
   ```

4. 사용자가 경로 알려주면:
   - 해당 PNG를 `{vault}/05_카드뉴스/_mascots/{이름}.png` 로 복사 (`cp` 명령)
   - `.cardnews-mascots.json` 에 `"이름": "_mascots/이름.png"` 추가 (없으면 파일 새로 생성)
   - 메시지: "{이름}님 캐릭터 등록 완료. 다음부터 자동으로 사용됩니다."

5. 이제 본인 캐릭터 PNG 경로가 확정됨 → 다음 단계로

> 캐릭터 PNG가 없으면(예: sponge-dressup 못 만든 경우): 기본 캐릭터(`{skill_root}/assets/mascots/mascot-blue.png`) 사용.
> 사용자가 "기본으로 진행"이라고 하면 등록 단계 건너뛰고 기본 캐릭터로.

### 3단계 · 콘텐츠 추출

submit.md를 읽고 다음을 뽑는다:

- **결과물**: 만든 것의 이름·구조·핵심 수치
- **과정**: 단계, 사용한 도구, 시간/숫자
- **삽질**: 막혔던 지점 (보통 `[!warning]` 블록)
- **인사이트**: "공유할만한 인사이트", "배운 것" 같은 섹션의 핵심 3-5개
- **다음 단계**: 진행 계획, 다음 주 예고
- **OS 선언문 / 핵심 한 줄**: 본인 톤이 가장 잘 드러난 한 문장 (Quote 슬라이드용)

> 길이가 짧으면 (10바이트 이하) 사용자에게 알리고 종료.

### 4단계 · 8장 표준 플로우 매핑

```
1. Hero (white)    — 질문형 후킹 + 첫 인상
2. Stats (ink)     — 결과 숫자 (1-2개)
3. List (white)    — 선택지 / 옵션 노출 (1번에 .active)
4. Hero (yellow)   — 핵심 결과물 / 시각 임팩트
5. Split (white)   — 반전 / 비교 / 발견의 순간
6. Quote (ink)     — 가장 큰 깨달음 / OS 선언문 (1번 질문의 답)
7. List (white)    — 배운 것 3가지 (1번에 .active)
8. CTA (white)     — 콜백 질문 + 다음 단계
```

**스토리텔링 호흡**: 질문(1) → 결과(2) → 선택(3) → 첫 결과물(4) → 반전(5) → 답(6) → 배움(7) → 콜백(8)

각 슬라이드에 콘텐츠를 매핑하되 다음 룰을 지킨다:
- 1번은 **질문형** (선언형 금지)
- 6번 Quote는 1번 질문의 **답**으로 회수 (스토리 연결)
- 4번에서 깐 컨텍스트(예: 시간·장소)를 8번 CTA에서 **콜백**
- `.hl` (옐로우 박스 강조)는 슬라이드당 1개만, 핵심 단어에

### 5단계 · 카피 초안 테이블 출력

사용자에게 다음 형식으로 보여준다:

```markdown
| # | 레이아웃 | 카피 |
|---|---------|------|
| 1 | Hero (white) | title: "..." / .hl: "..." / sub: "..." |
| 2 | Stats (ink) | label: "..." / figure 1: "1장 · ..." / figure 2: "..." / footnote: "..." |
| 3 | List (white) | title: "... .hl ..." / 1. ... (active) 2. ... 3. ... |
| 4 | Hero (yellow) | eyebrow: "..." / title: "... .hl ..." / sub: "..." |
| 5 | Split (white) | title: "... .hl ..." / left: "..." / right: "..." |
| 6 | Quote (ink) | blockquote: "... .hl ..." / cite: "..." |
| 7 | List (white) | title: "... .hl ..." / 1-3 |
| 8 | CTA (white) | title: "... .hl ..." / sub: "..." / hint: "..." |
```

그리고 묻는다: **"이 흐름·카피 OK? 수정할 슬라이드 있으면 알려줘."**

### 6단계 · 카피 검토 루프

사용자가 수정 요청하면 ("3번 더 짧게", "Quote 톤 부드럽게") 해당 슬라이드만 다시 제안.
"OK", "좋아", "진행" 등 승인 신호 받으면 7단계로.

### 7단계 · HTML 생성 (자립형)

이 스킬의 assets + 2단계에서 확정된 본인 캐릭터 PNG를 읽어 HTML에 인라인으로 박는다.

**스킬 경로** (기본): `~/.claude/skills/obsidian-cardnews-skill/`

읽어야 할 파일:
- `assets/design-system.css` — 전체 CSS
- **2단계에서 확정된 본인 캐릭터 PNG** — base64로 인코딩 (예: `{vault}/05_카드뉴스/_mascots/오웬.png`)

> 더 이상 Purple/Blue/Orange/Red 4색 마스코트는 사용하지 않는다. **본인 캐릭터 1종만** 사용.

Bash 명령으로 base64 변환:
```bash
MASCOT_PATH="{2단계에서 확정된 PNG 경로}"
python3 - << EOF
import base64
with open("$MASCOT_PATH",'rb') as f:
    print('--mascot-self: url("data:image/png;base64,'+base64.b64encode(f.read()).decode()+'");')
EOF
```

**HTML 구조** (8 섹션):

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{브랜드} · {조} · {이름} · {N}주차 카드뉴스</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css">
<style>
:root {
  --ink: #0A0A0A;
  --paper: #FFFFFF;
  --yellow: #E9ED12;
  /* mascot base64 variables injected here */
}
/* design-system.css 전체 인라인 */
</style>
</head>
<body>
  <!-- Slide 1 ~ 8 (아래 각 레이아웃 템플릿 참조) -->
</body>
</html>
```

### 8단계 · 각 슬라이드 템플릿

**공통**: 모든 슬라이드는 `.brand` (상단 좌측) + `.foot` (하단) 포함.
**마스코트**: 슬라이드 1, 2, 7, 8에만 (앞 2장 + 뒤 2장). **모두 본인 캐릭터(`self` 클래스)** 사용. 3·4·5·6은 `<div class="foot no-mascot">`.

CSS 추가:
```css
.foot .mascot.self { background-image: var(--mascot-self); }
```

각 슬라이드의 `<div class="mascot self"></div>` 로 호출.

#### Hero (Slide 1, 4)
```html
<section class="slide hero{ yellow}?">
  <div class="brand">{브랜드} 1기 · Week {NN}</div>
  <div class="eyebrow">{선택 — 4번에서 주로 사용}</div>
  <h1 class="title">
    {1행}<br>
    <span class="hl">{강조어}</span>{나머지}
  </h1>
  <div class="sub">{보조 설명}</div>
  <div class="foot">
    <div class="mascot self"></div>
    <div class="byline">{조} · {이름}</div>
  </div>
</section>
```

#### Stats (Slide 2)
```html
<section class="slide stats dark">
  <div class="brand">...</div>
  <div class="label">{설명 한 줄}</div>
  <div class="figures">
    <div class="figure">
      <div class="number">{숫자}<span class="unit">{단위}</span></div>
      <div class="desc">{설명}</div>
    </div>
    <!-- 1~2개 figure -->
  </div>
  <div class="footnote">{출처/맥락}</div>
  <div class="foot">
    <div class="mascot self"></div>
    <div class="byline">{조} · {이름}</div>
  </div>
</section>
```

#### List (Slide 3, 7)
```html
<section class="slide list">
  <div class="brand">...</div>
  <h2 class="title">{제목} <span class="hl">{강조}</span></h2>
  <ol>
    <li class="active">{1번 — active로 강조}</li>
    <li>{2번}</li>
    <li>{3번}</li>
    <!-- 3~5개 -->
  </ol>
  <div class="foot{ no-mascot}?">...</div>
</section>
```

#### Split (Slide 5)
```html
<section class="slide split">
  <div class="brand">...</div>
  <h2 class="title" style="margin-top:48px">{대비 메시지} <span class="hl">{강조}</span></h2>
  <div class="columns">
    <div class="col">
      <div class="who">{대상 1}</div>
      <h3>{핵심 1}</h3>
      <dl>
        <dt>{레이블}</dt><dd>{값}</dd>
        <!-- 2~3개 -->
      </dl>
    </div>
    <div class="col">
      <div class="who">{대상 2}</div>
      <h3>{핵심 2}</h3>
      <dl>...</dl>
    </div>
  </div>
  <div class="foot no-mascot"><div class="byline">...</div></div>
</section>
```

#### Quote (Slide 6)
```html
<section class="slide quote dark">
  <div class="brand">...</div>
  <blockquote>
    {본문 한 줄 (또는 두 줄, .hl 포함)}
  </blockquote>
  <cite>— {출처/맥락}</cite>
  <div class="foot no-mascot">...</div>
</section>
```

#### CTA (Slide 8)
```html
<section class="slide cta">
  <div class="brand">...</div>
  <h2 class="title">{질문형 메인} <span class="hl">{강조}</span></h2>
  <div class="sub">{보조 설명}</div>
  <div class="hint">{작게, 다음 단계 예고}</div>
  <div class="foot">
    <div class="mascot self"></div>
    <div class="byline">{조} · {이름}</div>
  </div>
</section>
```

### 9단계 · 8장 슬라이드 PNG 렌더링 + base64 인라인 임베드

HTML의 각 `<section class="slide">` 를 Puppeteer 등으로 1080×1080 PNG로 렌더하되, **별도 파일로 저장하지 말고 base64 문자열로 메모리에서 처리**한다.

각 슬라이드 PNG → base64 → 다음 단계에서 `.md`에 인라인으로 삽입.

> **중요**: `cardnews-slide-1.png` ~ `cardnews-slide-8.png` 같은 **개별 PNG 파일을 디스크에 저장하지 않는다**. 폴더가 어지러워짐.
> 출력 디렉토리에는 최종적으로 **`{원본이름}_cardnews.html` + `{원본이름}_cardnews.md` 2개 파일만** 남는다.

### 10단계 · 옵시디언 노트 생성

`{vault}/05_카드뉴스/{N}주차/{X}조/{원본이름}_cardnews.md` 생성. 구조:

```markdown
---
team: {조}
member: {이름}
week: {N}
date: {YYYY-MM-DD}
type: cardnews
brand: {브랜드}
design-system: AAA Selfmarketing v1.0
slides: 8
status: draft
---

# {N}주차 카드뉴스 — {이름}

> 원본 HTML: 같은 폴더의 `{원본이름}_cardnews.html` (브라우저로 열어 확인).
> 아래는 8장 PNG 미리보기 (1080×1080, base64 인라인). 인스타 캐러셀 업로드 시 우클릭 → 이미지 저장.

![slide-1](data:image/png;base64,<9단계의 슬라이드 1 base64>)
![slide-2](data:image/png;base64,<9단계의 슬라이드 2 base64>)
![slide-3](data:image/png;base64,<9단계의 슬라이드 3 base64>)
![slide-4](data:image/png;base64,<9단계의 슬라이드 4 base64>)
![slide-5](data:image/png;base64,<9단계의 슬라이드 5 base64>)
![slide-6](data:image/png;base64,<9단계의 슬라이드 6 base64>)
![slide-7](data:image/png;base64,<9단계의 슬라이드 7 base64>)
![slide-8](data:image/png;base64,<9단계의 슬라이드 8 base64>)

---

## 캡션 (인스타그램 본문용)
{8장 흐름을 풀어쓴 캡션 + 해시태그}

## 슬라이드 카피 (편집용)
{각 슬라이드별 카피 — 5단계 테이블 풀어 쓰기}

## 스토리 흐름
{1→6 질문→답 회수, 4→8 콜백 구조 설명}

## Do/Don't 자체 검수
{체크리스트 — docs/design-system.md 참조, 통과한 항목 x로 표시}

## 발행 체크리스트
- [ ] (필요시) 5번 Split에 다른 사람 언급되면 양해 구함
- [ ] 본인 인스타 핸들 · 해시태그 조정
- [ ] 인스타 캐러셀 업로드 (위 8장 이미지 우클릭 → 저장 → 인스타 업로드)
- [ ] 발행 후 본인 기록처에 링크 추가
```

> 결과: .md 파일이 약 400~500KB가 됨 (8개 PNG base64 포함). 옵시디언에서 정상 렌더.

### 11단계 · 결과 안내

생성한 **두 파일 경로**를 보여주고:
- `{원본이름}_cardnews.html` — 자립형 캐러셀, 브라우저로 열기
- `{원본이름}_cardnews.md` — 옵시디언 노트, 8장 인라인 미리보기 + 캡션 + 체크리스트
- 폴더에 다른 파일(개별 PNG 등) 없는지 재확인
- Do/Don't 체크 결과 요약
- 5번 Split에 다른 멤버 언급 있으면 양해 구할 사람 안내

---

## 카피 작성 룰 (디자인 시스템 v1.0)

`docs/design-system.md` 의 톤 & 보이스 섹션 그대로 따른다. 핵심:

- **구어체 > 문어체** ("뭐가 될까", "묻는다", "맡긴다")
- **질문형 훅** (1번, 8번)
- **숫자 · 기간 · 결과 앞세움** ("90분", "1장", "5개", "3가지")
- **겸양어 금지** ("~합니다", "~한다")
- **단정형 안에서 호흡 풀기** ("17시" → "오후 5시", "한다" → "맡긴다")
- **`.hl` 슬라이드당 1개** (가장 임팩트 줄 단어)

## Do/Don't (HTML 생성 시 자체 검수)

- ✅ 팔레트 3색 (Ink/Paper/Yellow). 마스코트는 별도 변주.
- ✅ 옐로우 슬라이드 1~2장만 (보통 4번 1장)
- ✅ `.hl` 슬라이드당 정확히 1개
- ✅ 페이지 번호·섹션 마커 없음
- ✅ 이모지·그라디언트·라운드+컬러바 없음
- ✅ 한 슬라이드 한 메시지

---

## 참고 자료

- 디자인 시스템 풀 스펙: [docs/design-system.md](docs/design-system.md)
- CSS 토큰: [assets/design-system.css](assets/design-system.css)
- 입력 예시: [examples/sample-submit.md](examples/sample-submit.md)
- 출력 예시: [examples/sample-cardnews.html](examples/sample-cardnews.html)
