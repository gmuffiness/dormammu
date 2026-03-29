---
name: dormammu-slides
description: "발표 자료 생성 — Marp 기반 피치덱 PDF/PPTX/HTML 생성"
version: 1.0.0
---

# Dormammu Slides — 발표 자료 생성 스킬

## 개요

Marp CLI를 사용하여 Dormammu 프로젝트의 발표 자료를 생성합니다.
Markdown 한 파일로 작성하고, PDF/PPTX/HTML로 빌드합니다.

## 사용법

```
/dormammu:slides                     ← 기존 슬라이드를 빌드 (PDF + PPTX + HTML)
/dormammu:slides build               ← 동일
/dormammu:slides new "발표 제목"     ← 새 슬라이드 생성 + 빌드
/dormammu:slides edit "수정 지시"    ← 기존 슬라이드 수정 + 리빌드
/dormammu:slides preview             ← HTML을 브라우저에서 열기
```

## 실행 절차

### Step 1: 입력 해석

사용자 입력(`$ARGUMENTS`)을 분석하여 모드를 결정합니다:

- **인자 없음 / `build`**: 기존 `docs/slides/dormammu-pitch.md`를 빌드만 수행
- **`new "제목"`**: 새 슬라이드 Markdown 생성 후 빌드
- **`edit "지시"`**: 기존 슬라이드를 지시에 따라 수정 후 리빌드
- **`preview`**: HTML 파일을 브라우저에서 열기

### Step 2: 슬라이드 작성/수정 (new 또는 edit 모드)

#### 파일 위치

```
docs/slides/
├── theme.css              ← 커스텀 다크 테마 (수정 가능)
├── dormammu-pitch.md      ← 메인 슬라이드 소스
├── dormammu-pitch.pdf     ← 빌드 결과
├── dormammu-pitch.pptx    ← 빌드 결과
└── dormammu-pitch.html    ← 빌드 결과 (프레젠테이션 모드)
```

#### Marp Markdown 규칙

```markdown
---
marp: true
theme: dormammu
paginate: true
size: 16:9
---

<!-- _class: lead -->
# 타이틀 슬라이드

---

# 일반 슬라이드
내용
```

#### 사용 가능한 슬라이드 클래스

| 클래스 | 용도 |
|--------|------|
| `lead` | 타이틀/엔딩 슬라이드 (중앙 정렬, 그라데이션 배경) |
| `section-header` | 섹션 구분 슬라이드 |
| `cols` | 2컬럼 레이아웃 |
| `diagram tech` | 다이어그램 슬라이드 (격자 배경, 작은 폰트) |
| `numbers` | 숫자 강조 슬라이드 (중앙 정렬) |

#### 디자인 원칙

- **한 슬라이드에 한 메시지** — 텍스트 과다 금지
- **표/비교를 적극 활용** — 픽사 vs Dormammu 같은 대비
- **blockquote(`>`)로 핵심 문장 강조** — 보라색 액센트 박스
- **이모지는 다이어그램에서만** — 본문에서는 자제
- **코드 블록은 아키텍처 다이어그램용** — monospace 다이어그램

### Step 3: 빌드

다음 명령어를 순차 실행합니다:

```bash
cd docs/slides

# PDF 빌드
npx @marp-team/marp-cli --theme theme.css dormammu-pitch.md -o dormammu-pitch.pdf --allow-local-files

# PPTX 빌드
npx @marp-team/marp-cli --theme theme.css dormammu-pitch.md -o dormammu-pitch.pptx --allow-local-files

# HTML 빌드
npx @marp-team/marp-cli --theme theme.css dormammu-pitch.md -o dormammu-pitch.html --allow-local-files
```

**주의:** `docs/slides`는 **워크스페이스 루트** (`personal-agent-workspace/docs/slides/`) 기준입니다.
절대 경로: `/Users/daejeong/agent-workspace/personal-agent-workspace/docs/slides/`

### Step 4: 미리보기

빌드 완료 후 PDF를 자동으로 엽니다:

```bash
open docs/slides/dormammu-pitch.pdf
```

`preview` 모드에서는 HTML을 엽니다:

```bash
open docs/slides/dormammu-pitch.html
```

### Step 5: 결과 보고

빌드 결과를 사용자에게 보고합니다:

```
생성 완료:
- PDF:  docs/slides/dormammu-pitch.pdf
- PPTX: docs/slides/dormammu-pitch.pptx
- HTML: docs/slides/dormammu-pitch.html (브라우저에서 발표 가능)

슬라이드 [N]장, 테마: dormammu (다크)
```

## 테마 커스터마이징

`docs/slides/theme.css`를 수정하면 됩니다. 핵심 변수:

```css
:root {
  --color-bg: #0a0a0f;           /* 배경 */
  --color-accent: #a855f7;       /* 보라 (메인 액센트) */
  --color-cyan: #22d3ee;         /* 시안 (보조 액센트) */
  --color-accent-dim: #7c3aed;   /* 테이블 헤더 */
}
```

## 참고

- Marp 공식: https://marp.app/
- 커스텀 테마 가이드: https://marpit.marp.app/theme-css
- 발표 전략 문서: `docs/ralphthon-2-presentation-strategy.md`
