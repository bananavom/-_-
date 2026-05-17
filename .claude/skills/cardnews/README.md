# obsidian-cardnews-skill

> 옵시디언에 올라온 미션 제출(.md)을 받아서 **인스타그램용 1080×1080 카드뉴스 8장**을 단일 HTML 파일로 만들어주는 Claude Code 스킬.
>
> AAA Selfmarketing Design System v1.0을 그대로 따른다. 스폰지클럽 1기 운영을 위해 마스코트·푸터 변주를 추가했다.

---

## 미리보기

[examples/sample-cardnews.html](examples/sample-cardnews.html) 더블클릭으로 브라우저에서 열기.

- 입력: [examples/sample-submit.md](examples/sample-submit.md) (스폰지클럽 1기 5조 오웬의 1주차 제출)
- 출력: [examples/sample-cardnews.html](examples/sample-cardnews.html) (자립형 HTML, 마스코트 base64 인라인)
- 옵시디언 노트: [examples/sample-cardnews.md](examples/sample-cardnews.md)

---

## 무엇을 하는가

submit.md 1개 → 카드뉴스 8장 HTML + 옵시디언 노트

**출력 위치**: vault의 `05_카드뉴스/{N}주차/{X}조/` (자동 생성)

```
입력: 02_mission/1주차_0510/5조/5조_오웬_1주차_submit.md
출력: 05_카드뉴스/1주차/5조/5조_오웬_1주차_cardnews.html
      05_카드뉴스/1주차/5조/5조_오웬_1주차_cardnews.md
```

8장 표준 플로우:

```
1. Hero (white)    — 질문형 후킹
2. Stats (ink)     — 결과 숫자
3. List (white)    — 선택지/옵션
4. Hero (yellow)   — 핵심 결과물 (시각 임팩트)
5. Split (white)   — 반전/비교
6. Quote (ink)     — 가장 큰 깨달음 (1번 질문의 답)
7. List (white)    — 배운 것 3가지
8. CTA (white)     — 콜백 질문 + 다음 단계
```

스토리텔링 호흡: **질문(1) → 결과(2) → 선택(3) → 첫 결과물(4) → 반전(5) → 답(6) → 배움(7) → 콜백(8)**

마스코트는 앞 2장 + 뒤 2장(슬라이드 1·2·7·8)에만, **본인 캐릭터** 사용.
중간 4장(3·4·5·6)은 메시지에 집중하느라 마스코트 없음.

## 본인 캐릭터 등록

처음 실행 시 본인 캐릭터 PNG를 한 번 등록하면, 다음부터 자동 사용됨.

1. https://sponge-dressup.vercel.app 에서 본인 캐릭터 만들고 PNG 다운로드
2. `/cardnews <submit.md>` 실행
3. 스킬이 묻는다: "본인 캐릭터 PNG 경로 알려주세요"
4. 다운받은 파일 경로 입력 (예: `~/Downloads/sponge-OWEN.png`)
5. 스킬이 `{vault}/05_카드뉴스/_mascots/{이름}.png` 로 복사 + 등록
6. 다음번부터 자동 사용

등록된 마스코트 매핑은 `{vault}/05_카드뉴스/.cardnews-mascots.json` 에서 관리.

---

## 설치

### 1단계 — Claude Code 스킬 폴더에 클론

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/owenleekr/obsidian-cardnews-skill.git
```

> 폴더명을 그대로 `obsidian-cardnews-skill`로 두는 게 중요. 스킬 내부에서 이 경로를 참조함.

### 2단계 — (옵션) 슬래시 커맨드로 등록

자연어 호출("이 submit 카드뉴스로 만들어줘")로도 동작하지만, 슬래시 커맨드로 쓰고 싶으면:

```bash
mkdir -p ~/.claude/commands
ln -s ~/.claude/skills/obsidian-cardnews-skill/SKILL.md ~/.claude/commands/cardnews.md
```

이제 `/cardnews <submit.md 경로>` 로 호출 가능.

### 3단계 — Claude Code 재시작

새 세션에서 스킬 자동 디스커버리가 잡힘. 같은 세션이면 `SKILL.md`를 직접 읽으라고 요청.

---

## 사용법

### 슬래시 커맨드

```
/cardnews 02_mission/1주차_0510/5조/5조_오웬_1주차_submit.md
```

### 자연어

```
이 submit 파일로 카드뉴스 만들어줘.
경로: 02_mission/1주차_0510/5조/5조_오웬_1주차_submit.md
```

### 진행 순서

1. 스킬이 submit.md 읽고 경로에서 메타데이터 추출 (조, 이름, 주차, 날짜)
2. **본인 캐릭터 확인** — 등록 안 됐으면 PNG 경로 묻고 등록
3. 8장 카피 초안을 테이블로 보여줌
4. 검토 — "3번 더 짧게", "Quote 톤 부드럽게" 등 자유롭게 수정 요청
5. "OK" / "진행" 같은 승인 신호 → HTML + 옵시디언 노트 생성
6. `05_카드뉴스/{N}주차/{X}조/` 폴더에 두 파일 생성됨:
   - `{원본이름}_cardnews.html` — 자립형 캐러셀 (본인 캐릭터 base64 인라인, 어디서든 열림)
   - `{원본이름}_cardnews.md` — 옵시디언 노트 (캡션 + 카피 + 체크리스트)

---

## 입력 파일 컨벤션 (기본값)

스폰지클럽 1기 폴더 구조를 기본으로 가정:

```
{vault}/02_mission/{N}주차_{날짜}/{X}조/{X}조_{이름}_{N}주차_submit.md
```

이 컨벤션에서 자동 추출:

- **브랜드**: vault 폴더명이 `spongeclub_*`이면 → "스폰지클럽 N기"
- **주차**: `N주차_*` 폴더에서
- **날짜**: 주차 폴더명 뒤 숫자에서 (예: `1주차_0510` → 2026.05.10)
- **조**: `X조` 폴더명
- **이름**: 파일명 `X조_{이름}_N주차_submit.md`

> 다른 컨벤션이면 스킬이 사용자에게 메타데이터를 직접 묻고 진행.

---

## 출력 형태

### HTML 파일

- 1080×1080 슬라이드 8장이 세로로 나열
- 마스코트 4종 base64 인라인 (외부 의존성 0)
- Pretendard Variable 폰트만 CDN으로 로드
- 단일 파일 약 800KB~1MB
- 옵시디언 iframe / 브라우저 더블클릭 / 이메일 첨부 어디서나 동작

### 옵시디언 노트

- frontmatter (team, member, week, date 등)
- iframe으로 HTML 캐러셀 임베드
- 인스타그램 캡션 초안 + 해시태그
- 슬라이드별 카피 (편집용)
- 스토리 흐름 설명
- Do/Don't 자체 검수 결과
- 발행 체크리스트

---

## 인스타그램 업로드용 PNG 추출

스킬이 HTML까지만 생성하고 PNG 추출은 수동:

**옵션 1 — 브라우저 우클릭**
1. HTML을 크롬에서 열기
2. 각 `.slide` 요소 우클릭 → 검사 → 우측 패널에서 `.slide` 요소 우클릭 → Capture node screenshot

**옵션 2 — Puppeteer 일괄 (개발자용)**
```javascript
// 별도 스크립트로 실행
const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1080, deviceScaleFactor: 2 });
  await page.goto('file:///path/to/cardnews.html');
  const slides = await page.$$('.slide');
  for (let i = 0; i < slides.length; i++) {
    await slides[i].screenshot({ path: `slide-${i+1}.png` });
  }
  await browser.close();
})();
```

**옵션 3 — 캔바/피그마 가이드로**
HTML을 디자인 출발점으로 두고 캔바·피그마에서 본인 톤으로 마무리.

---

## 디자인 시스템 v1.0

AAA Selfmarketing Design System의 핵심만:

- **3색**: Ink `#0A0A0A` / Paper `#FFFFFF` / Yellow `#E9ED12`
- **타이포**: Pretendard Variable
- **6 레이아웃**: Hero / Split / Quote / Stats / List / CTA
- **절대 룰**: 한 슬라이드 한 메시지, `.hl` 슬라이드당 1개, 페이지 번호 없음, 이모지/그라디언트/AI slop 없음
- **톤**: 구어체, 질문형 훅, 숫자 앞세움, 겸양어 금지

풀 스펙: [docs/design-system.md](docs/design-system.md)

---

## 다른 스터디 그룹에 적용하려면

기본은 스폰지클럽 1기 브랜딩(마스코트 4종, 푸터). 다른 그룹은:

1. **마스코트 교체**: `assets/mascots/mascot-{purple,blue,orange,red}.png` 를 본인 그룹 캐릭터로
2. **브랜드 텍스트 변경**: SKILL.md 의 "브랜드" 추출 로직에서 본인 vault 이름 패턴 추가
3. **8장 플로우 조정**: 원하면 SKILL.md 의 표준 플로우 섹션 본인 톤으로 수정

마스코트 없이 쓰고 싶으면 모든 슬라이드 `.foot`에 `no-mascot` 클래스만 붙이면 됨.

---

## 출처 / 라이선스

- **디자인 시스템**: AAA Selfmarketing v1.0 (셀피쉬클럽 AAA팀 내부)
- **마스코트**: 스폰지클럽 1기 운영팀 자산 (사용 권한은 스폰지클럽 멤버 한정)
- **스킬 코드**: MIT License — [LICENSE](LICENSE)
- **만든 사람**: 오웬 ([@owenleekr](https://github.com/owenleekr))

마스코트 이미지는 별도 권리로, 스폰지클럽 외부 배포 시 교체할 것.

---

## 문제 해결

**Q. 자동 디스커버리가 안 잡혀요.**
A. Claude Code 재시작. 또는 같은 세션에서 `~/.claude/skills/obsidian-cardnews-skill/SKILL.md`를 직접 읽으라고 요청.

**Q. 경로가 스폰지클럽 컨벤션이 아니에요.**
A. 스킬이 자동으로 사용자에게 메타데이터(조/이름/주차)를 묻고 진행함.

**Q. 마스코트가 깨진 이미지로 보여요.**
A. 자립형 HTML 생성 시 base64 인라인이 정상 동작했는지 확인. 또는 `assets/mascots/*.png` 파일이 모두 존재하는지 확인.

**Q. iframe이 옵시디언 안에서 안 보여요.**
A. 옵시디언 보안 설정 또는 Custom File Extensions plugin 활성화 필요. HTML 파일을 직접 브라우저로 여는 게 가장 확실.

---

## 변경 로그

- **v1.0** (2026-05) — 첫 릴리즈, 스폰지클럽 1기 5조 오웬 1주차 submit 기반 검증
