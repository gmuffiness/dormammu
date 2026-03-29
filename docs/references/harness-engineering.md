# 하네스 엔지니어링 레퍼런스

> Dormammu 시뮬레이션 하네스 설계에 참고한 프로젝트, 아티클, 패턴 정리

---

## 1. Autoresearch (Karpathy)

- **GitHub:** https://github.com/karpathy/autoresearch
- **핵심:** 630줄 Python. AI 에이전트가 `train.py`를 수정 → 5분 학습 → val_bpb 측정 → 개선이면 유지, 아니면 폐기. 2일간 700실험 → 19% 성능 향상.

### Dormammu에 적용할 포인트

| Autoresearch 패턴 | Dormammu 적용 |
|---|---|
| **단일 측정 지표 (val_bpb)** | `dormammu benchmark`의 composite_score |
| **고정 시간 실험 (5분)** | 고정 파라미터 벤치마크 시뮬레이션 |
| **수정 → 실행 → 측정 → 판단** | `diagnose → improve → benchmark → compare` |
| **program.md로 방향 제시** | `CLAUDE.md` 하네스 + `feature_list.json` |
| **수정 범위 제한 (train.py만)** | feature_list의 target_module로 범위 제한 |
| **전체 코드가 컨텍스트에 들어감 (630줄)** | 모듈 단위 작업으로 컨텍스트 관리 |

### 핵심 인사이트
- 제약이 많을수록 자율 실행이 안정적. "뭐든 고쳐도 됨" < "이 파일만 고쳐"
- 실험 단위가 짧고 비교 가능해야 700번 반복 가능
- 사람은 `program.md`(방향)만 관리, 에이전트는 실험을 반복

---

## 2. Ouroboros

- **GitHub:** https://github.com/Q00/ouroboros
- **핵심:** 명세 기반 자율 개발. 인터뷰 → Seed(불변 명세) → 실행 → 3단계 평가 → 진화 루프.

### Dormammu에 적용할 포인트

| Ouroboros 패턴 | Dormammu 적용 |
|---|---|
| **Socratic Interview (모호성 ≤ 0.2)** | `/dormammu-goal`로 시뮬레이션 목표 명확화 |
| **Seed (불변 명세)** | `feature_list.json` + `CLAUDE.md` |
| **3단계 평가 (기계→의미→합의)** | `pytest → benchmark → diagnose` |
| **Ralph (세션 간 지속 루프)** | `dormammu evolve` (benchmark 기반 반복) |
| **드리프트 감지 (목표 50% + 제약 30% + 온톨로지 20%)** | benchmark score 추이로 드리프트 감지 |
| **SF 영감 (lateral thinking)** | `InspirationSystem` 22개 SF 시드 |

### 핵심 인사이트
- "대부분의 AI 코딩은 출력이 아니라 입력에서 실패한다" → 사전 명세가 핵심
- Event sourcing으로 세션 간 상태 완전 복원
- 수렴 감지 (유사도 ≥ 0.95) → 자동 종료

---

## 3. Anthropic Autonomous Coding Quickstart

- **GitHub:** https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding
- **핵심:** 2-에이전트 아키텍처. Initializer(명세 생성) + Coding Agent(기능 구현). feature_list.json + progress 파일로 세션 간 연속성.

### Dormammu에 적용할 포인트

| Anthropic 패턴 | Dormammu 적용 |
|---|---|
| **feature_list.json (200+ 기능)** | 53개 기능 목록 (확장 가능) |
| **claude-progress.txt** | 세션 간 진행상황 로그 |
| **init.sh** | 환경 자동 설정 |
| **"테스트를 삭제하거나 수정하지 마라"** | CLAUDE.md 에러 복구 규칙 |
| **Git 커밋 = 롤백 포인트** | 기능당 1커밋, 점수 하락 시 revert |
| **Puppeteer로 E2E 테스트** | benchmark 시뮬레이션 = E2E 테스트 |

### 핵심 인사이트
- 200개 세분화된 기능이 "뭘 해야 하지?" 문제를 해결
- 기능 하나 = 15-30분 = 컨텍스트 관리 가능
- "완료 전 반드시 자가 검증" 규칙이 품질 유지의 핵심

---

## 4. OpenAI 하네스 엔지니어링

- **아티클:** https://openai.com/index/harness-engineering/
- **핵심:** 3명 엔지니어 + Codex → 5개월 ~100만 줄 코드, 1,500 PR. 사람이 직접 쓴 코드 0줄.

### Dormammu에 적용할 포인트

- **리포지토리가 단일 진실 원천** — Google Docs나 Slack에 있는 지식은 에이전트에게 보이지 않음. 모든 것을 코드/문서로
- **제약이 생산성을 높인다** — 의존성 규칙, import 패턴 제한, 구조적 테스트
- **엔트로피 관리** — 시간이 지나면 코드베이스가 부패. 주기적 정리 에이전트 필요

---

## 5. Martin Fowler — Harness Engineering

- **아티클:** https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html
- **핵심:** 3대 축 = Context Engineering + Architectural Constraints + Entropy Management

### 3대 축 → Dormammu 매핑

| 축 | 설명 | Dormammu |
|---|---|---|
| **Context** | 리포가 진실의 원천. 정적(CLAUDE.md) + 동적(벤치마크 점수) | CLAUDE.md + benchmark history |
| **Constraints** | 의존성 규칙, 린터, 구조 테스트 | 모듈 경계 규칙, pytest, feature scope |
| **Entropy** | 주기적 정리, 패턴 강제, 문서 일관성 | `dormammu diagnose` + `dormammu audit` |

---

## 6. Phil Schmid — Agent Harness 2026

- **아티클:** https://www.philschmid.de/agent-harness-2026
- **핵심:** "모델은 상품화됨. 하네스가 차별화 요소." 하네스 = 에이전트를 위한 운영 체제.

---

## 7. Stanford Generative Agents

- **논문:** https://arxiv.org/abs/2304.03442
- **GitHub:** https://github.com/joonspk-research/generative_agents
- **핵심:** 25 AI 에이전트가 Smallville 마을에서 자율 생활. Memory Stream + Reflection + Planning.

### Dormammu 에이전트 시스템과의 관계
- Dormammu의 `Agent.memories` + `Agent.decide_action()` = Generative Agents의 Memory Stream + Planning
- Dormammu는 시뮬레이션 "품질"을 측정하는 하네스를 추가한 것이 차별점

---

## 패턴 요약: 성공하는 하네스의 공통 구조

```
┌─ 방향 설정 ────────────────────────┐
│ program.md / CLAUDE.md / Seed YAML  │
│ "무엇을 왜 만드는가"               │
└─────────────────────────────────────┘
         ↓
┌─ 범위 제한 ────────────────────────┐
│ feature_list / train.py only        │
│ "이것만 건드려라"                   │
└─────────────────────────────────────┘
         ↓
┌─ 실행 + 측정 ──────────────────────┐
│ 5분 학습 / benchmark 시뮬레이션     │
│ val_bpb / composite_score           │
│ "결과가 더 나아졌는가?"             │
└─────────────────────────────────────┘
         ↓
┌─ 판단 + 기록 ──────────────────────┐
│ 개선 → 커밋 / 퇴보 → 롤백          │
│ progress.txt / history.jsonl        │
│ "다음 세션이 이어받을 수 있게"       │
└─────────────────────────────────────┘
         ↓ 반복
```

이 4단계가 갖춰지면, N시간 자율 실행이 가능해진다.
