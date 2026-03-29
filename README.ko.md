# Dormammu — Dormammu

[English](README.md) | **한국어**

**시뮬레이션 특화 자율 AI 개발 하네스**

Dormammu는 AI 에이전트가 자율적으로 세계 시뮬레이션을 빌드하고, 실행하고, 개선할 수 있게 합니다. 범용 코딩 하네스가 코드 양을 측정하는 것과 달리, Dormammu는 시뮬레이션 출력 품질을 피드백 신호로 사용합니다 — 제품이 AI에게 다음에 뭘 개선할지 알려줍니다.

---

## 무엇이 다른가

범용 하네스: *"코드가 컴파일됐나?"*
Dormammu: *"시뮬레이션이 흥미로운가?"*

| | 범용 하네스 | Dormammu |
|---|---|---|
| **피드백 신호** | 테스트 통과/실패 | 시뮬레이션 품질 점수 |
| **측정 대상** | 코드 라인, 커버리지 | 창발성, 서사, 다양성, 신선함 |
| **명세** | 정적, 사전 작성 | 제품 출력이 개발을 이끔 |
| **산출물** | 코드 diff | 세대별 시뮬레이션 개선 |

핵심 인사이트: 시뮬레이션 출력은 *정량적으로 측정 가능*합니다. `0.31 → 0.58`로 움직이는 점수가 AI에게 정확히 무엇이 바뀌었고 도움이 됐는지 알려줍니다. 루프 안에 사람의 판단이 필요 없습니다.

---

## 빠른 시작

```bash
# 설치
git clone https://github.com/gmuffiness/dormammu.git
cd dormammu
pip install -e ".[dev]"
cp .env.example .env  # OPENAI_API_KEY 추가

# 시뮬레이션 실행
dormammu run "앞으로 100년, 인류에게는 어떤 미래가 올 것인가?"

# 빠른 벤치마크 (~$0.30)
dormammu run "인류 최초의 화성 식민지 50년" --max-depth 1 --cost-limit 0.5

# 자율 개선 루프
dormammu evolve "인류 최초의 화성 식민지 50년" --max-iterations 10
```

---

## 피드백 루프

```
┌─ 빌드 ──────────────────────────────┐
│ AI가 시뮬레이션 엔진 코드를 수정     │
└──────────────┬───────────────────────┘
               ↓
┌─ 실행 ──────────────────────────────┐
│ dormammu benchmark (고정 조건 시뮬레이션) │
└──────────────┬───────────────────────┘
               ↓
┌─ 측정 ──────────────────────────────┐
│ emergence: 0.45  narrative: 0.62    │
│ diversity: 0.31  novelty: 0.50     │
│ composite: 0.48                     │
└──────────────┬───────────────────────┘
               ↓
┌─ 진단 ──────────────────────────────┐
│ "diversity가 가장 낮음 →            │
│  agents/agent.py의 decide_action()  │
│  에서 페르소나별 프롬프트 분화 필요" │
└──────────────┬───────────────────────┘
               ↓
           (반복)
```

매 세대마다 AI가 가장 낮은 점수를 찾아 해당 모듈을 추적하고, 타겟 코드를 수정한 뒤 개선을 확인한 후에야 커밋합니다. 점수가 하락하면 자동 롤백됩니다.

---

## 명령어

| 명령어 | 설명 |
|--------|------|
| `dormammu run <주제>` | DFS 시나리오 탐색으로 새 시뮬레이션 시작 |
| `dormammu resume <id>` | 일시정지된 시뮬레이션 재개 |
| `dormammu replay <id>` | 완료된 시뮬레이션을 속도 조절하며 재생 |
| `dormammu list` | 모든 시뮬레이션 목록 (점수, 상태) |
| `dormammu status <id>` | 시뮬레이션 상태, 점수, 비용 표시 |
| `dormammu auto <주제>` | 자율 시뮬레이션 루프 |
| `dormammu serve` | 2D 시각화 프론트엔드용 FastAPI 서버 시작 |
| `dormammu benchmark` | 고정 벤치마크 시뮬레이션 실행 및 점수 리포트 |
| `dormammu diagnose` | 가장 약한 품질 차원을 찾아 소스 코드에 매핑 |
| `dormammu improve` | 최신 벤치마크 진단에서 개선 계획 생성 |
| `dormammu evolve <주제>` | 자율 개선 루프: benchmark → diagnose → improve → 반복 |

---

## 시뮬레이션 예시

엔진은 네 가지 카테고리의 자유 형식 주제를 다룹니다:

**미래 예측**
- "앞으로 100년, 인류에게는 어떤 미래가 올 것인가?"
- "AI가 인간의 일자리를 완전히 대체한 세계 50년"
- "기후변화로 해수면이 5m 상승한 도시의 100년"

**대체 역사 (what-if)**
- "진격의 거인 — 에렌이 땅울림을 하지 않았다면 100년 후"
- "냉전이 열전으로 전환됐다면 이후 50년"
- "인터넷이 발명되지 않았다면 현재까지"

**가상 세계관 시뮬레이션**
- "삼체 — 삼체인이 지구에 도착한 이후 50년"
- "반지의 제왕 — 사우론이 반지를 되찾았다면"
- "스타워즈 — 제국이 승리한 은하계 100년"

**사회 실험**
- "기본소득이 전면 시행된 국가 30년"
- "모든 국경이 사라진 세계 100년"
- "화폐가 폐지되고 신용 기반 경제로 전환된 사회"

---

## 아키텍처

```
Dormammu
├── Engine          DFS 시나리오 트리, 에이전트 턴, 월드 스테이트
│   ├── ScenarioTree    분기 가설 트리 (DFS 탐색)
│   ├── WorldState      에이전트, 관계, 이벤트, 자원
│   └── TurnExecutor    1턴: 에이전트 결정 → 서사 생성
│
├── Agents          기억과 성격을 가진 LLM 기반 페르소나
│   ├── Persona         Big-5 성격, 배경, 목표 (에이전트별)
│   ├── Agent           메모리 (롤링, 감정 가중치로 정리)
│   └── Interaction     OpenAI 호출 + 재시도 + 비용 추적
│
├── Hypothesis      분기 생성, 점수 매기기, SF 영감
│   ├── Generator       노드당 3개 자식 분기 (LLM)
│   ├── Evaluator       점수: 창발성(35%), 서사(30%),
│   │                   다양성(20%), 신선함(15%)
│   └── Inspiration     3세대마다 SF/문학 시드 주입
│
├── Harness         자율 개선 레이어
│   ├── Benchmark       일관된 점수 측정용 고정 파라미터 시뮬레이션
│   ├── Diagnose        약한 점수를 담당 소스 모듈에 매핑
│   └── Evolve          외부 루프: benchmark → diagnose → improve → commit
│
├── Orchestrator    비동기 DFS 드라이버, 스케일 감지, 비용 관리
│
├── Storage         SQLite (WAL 모드), JSONL 턴 로그, 리플레이
│
└── Frontend        FastAPI + React 2D 캔버스 시각화
```

**의존성 규칙:** `engine/`은 `orchestrator/`나 `api/`에서 절대 임포트하지 않음. `agents/`는 `orchestrator/`에서 임포트하지 않음. 하네스는 시뮬레이션 외부에 위치 — 점수를 읽고 소스를 수정하되, 시뮬레이션 내부를 직접 건드리지 않음.

---

## 2D 시각화

`dormammu serve`로 FastAPI 백엔드(포트 8000)를 시작합니다. React 프론트엔드(포트 5173, `cd frontend && npm run dev`)가 렌더링하는 것들:

- **Canvas2D** — 2D 맵 위 실시간 에이전트 위치와 상호작용
- **ScenarioTree** — 노드별 점수가 있는 실시간 DFS 분기 탐색
- **EventLog** — 턴별 서사 스트림
- **Dashboard** — 세대별 종합 점수 추이
- **TimelineControls** — 완료된 시뮬레이션을 스크러빙

---

## 품질 점수

| 점수 | 가중치 | 측정 대상 |
|------|--------|----------|
| `emergence` | 35% | 에이전트 상호작용에서 예상치 못한 사건이 발생했는가 |
| `narrative` | 30% | 이야기가 흥미롭고 관찰할 가치가 있는가 |
| `diversity` | 20% | 에이전트들이 서로 구별되게 행동했는가 |
| `novelty` | 15% | 이 분기가 형제 분기와 의미 있게 다른가 |
| `composite` | — | 가중 합계; >0.3이면 분기 확장, ≤0.3이면 가지치기 |

---

## 영감을 준 것들

- **[Karpathy의 autoresearch](https://github.com/karpathy/autoresearch)** — 실험 → 측정 → 반복 패턴. 고정 시간 실행, 단일 스칼라 지표, 회귀 시 자동 폐기.
- **[Ouroboros](https://github.com/Q00/ouroboros)** — 명세 우선 하네스. 불변 시드(CLAUDE.md + feature_list.json), 다단계 평가, 드리프트 감지.
- **[Anthropic autonomous-coding quickstart](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)** — feature_list.json 진행 추적, claude-progress.txt 세션 연속성, git 커밋을 롤백 포인트로 활용.
- **[Stanford Generative Agents](https://arxiv.org/abs/2304.03442)** — 에이전트 메모리 스트림, 성찰, 계획. Dormammu는 에이전트 품질을 자동으로 측정·개선하는 외부 하네스로 이를 확장.

---

## 기술 스택

Python 3.10+, OpenAI API (gpt-4o), SQLite + sqlite-utils, FastAPI + uvicorn, Click, Rich — React 18 + Vite + TypeScript + Tailwind CSS + HTML5 Canvas

---

## 라이선스

MIT
