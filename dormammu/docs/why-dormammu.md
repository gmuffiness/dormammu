# Why Dormammu — 하네스 엔지니어링과 시뮬레이션의 만남

> 이 문서는 Dormammu의 존재 이유를 설명합니다.
> README에 녹여넣기 위한 사전 준비 자료입니다.

---

## 1. 하네스 엔지니어링이란?

### Agent = Model + Harness

2026년 현재, AI 에이전트의 성능을 결정하는 것은 모델 자체보다 **모델을 감싸는 구조(harness)**입니다.

| 시대 | 패러다임 | 핵심 레버 |
|------|----------|----------|
| ~2023 | 프롬프트 엔지니어링 | 모델에게 *뭘 말할지* |
| 2024 | 컨텍스트 엔지니어링 | 모델이 *뭘 볼지* |
| 2025-2026 | **하네스 엔지니어링** | 모델 *주변의 구조* |

프롬프팅은 모델에게 무엇을 말할지 바꿉니다. 하네스 엔지니어링은 모델이 운영되는 **구조적 환경 자체**를 바꿉니다 — 어떤 도구가 있고, 세션 간 어떤 상태가 유지되고, 어떤 검증 게이트를 통과해야 하고, 실패가 어떻게 다음 시도에 피드백되는지.

LangChain의 실험에서, 모델을 바꾸지 않고 **하네스만 바꿔서** Terminal Bench 점수가 52.8% → 66.5%로 올랐습니다. 하네스 투자의 ROI가 모델 업그레이드보다 높은 시대입니다.

> *"When coding agents underperform, check the harness before blaming the model."*
> — HumanLayer

### 하네스 = 사이버네틱스의 아키텍처 적용

@odysseus0z는 하네스 엔지니어링이 새로운 개념이 아니라 **사이버네틱스(cybernetics)의 소프트웨어 아키텍처 레이어 적용**이라고 주장합니다.

코드베이스에는 이미 사이버네틱 제어가 존재합니다:
- **컴파일러** — 문법에 대한 피드백 루프를 닫음
- **테스트 스위트** — 행동에 대한 피드백 루프를 닫음
- **린터** — 스타일에 대한 피드백 루프를 닫음

이것들은 진짜 사이버네틱 제어이지만, **기계적이고 결정적으로** 검사할 수 있는 속성에서만 작동합니다.

**하네스가 메운 공백: 아키텍처/설계 수준의 피드백 루프.** "이 변경이 시스템 전체 아키텍처에 맞는가?", "이게 올바른 추상화인가?" 같은 질문은 이전까지 사람만 판단할 수 있었습니다. 하네스 엔지니어링은 LLM 에이전트(아키텍처를 추론할 수 있음) + 결정적 린터/구조 테스트(강제할 수 있음)를 결합해서, **설계와 의도 수준에서 작동하는 최초의 사이버네틱 제어 시스템**을 만듭니다.

> *"Harness"라는 단어 자체가 사이버네틱스의 "제어 시스템" 개념에 직접 매핑됩니다. 에이전트 출력이라는 에너지를 목표를 향해 채널링하면서 이탈을 방지하는 구조.*

### OpenAI: "Humans Steer. Agents Execute."

OpenAI 하네스 팀은 5개월간 극단적 실험을 수행했습니다. **사람이 직접 쓴 코드가 0줄**인 프로덕션 베타 제품을 만든 것입니다.

- 7명 엔지니어, Codex 에이전트로 **~100만 줄** 코드 생산
- ~1,500개 병합 PR, 엔지니어당 하루 평균 3.5 PR
- 수작업 대비 **10배 빠른** 것으로 추정

핵심 설계 패턴:

1. **Progressive Disclosure** — AGENTS.md를 ~100줄 이하 목차로 유지. 거대 지시 파일은 에이전트를 오히려 방해함. "에이전트가 실행 중에 접근할 수 없는 것은 존재하지 않는 것과 같다."
2. **Layered Architecture + 기계적 강제** — `Types → Config → Repo → Service → Runtime → UI`. 위반은 문서화가 아니라 **물리적으로 불가능**하게 만듦. 커스텀 린터(그 자체도 Codex가 작성)가 불법 임포트를 차단.
3. **Repo = Single Source of Truth** — 에이전트 관점에서 repo에 없으면 존재하지 않음. 설계 결정, 실행 계획, 기술 부채 모두 버전 관리되는 마크다운에.
4. **피드백 루프 = QA 대체** — DOM 스냅샷, 시각적 회귀 스크린샷, LogQL/PromQL 쿼리. 주관적 판단("이거 맞아 보이는데?")을 기계적 검증("이거 통과하나?")으로 대체.
5. **기술 부채 Garbage Collection** — 규칙을 한 번 인코딩하면 에이전트가 주기적으로 스캔해서 리팩토링 PR을 자동 생성.

**핵심 발견: 병목은 모델 능력이 아니라 "환경의 가독성(environment legibility)"이다.**

전문가 지식이 코드베이스 표준으로 인코딩되면, 한 엔지니어의 전문성이 **모든 에이전트에게 즉시 전파**됩니다. React 전문가가 합류하자 모든 에이전트의 훅 분해 패턴이 개선되었다는 것.

**출처:**
- [Anthropic: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic: Harness Design for Long-Running Application Development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [OpenAI: Harness Engineering](https://openai.com/index/harness-engineering/)
- [@odysseus0z: Harness Engineering Is Cybernetics](https://x.com/odysseus0z/status/2030416758138634583)
- [Martin Fowler: Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)
- [LangChain: Improving Deep Agents with Harness Engineering](https://blog.langchain.com/improving-deep-agents-with-harness-engineering/)

---

## 2. 기존 하네스들은 뭘 하는가?

### 2.1 "코드를 더 많이, 더 잘 쓰기" 하네스

현재 거의 모든 유명 하네스는 **코드 생산성**을 위한 것입니다.

| 프로젝트 | 피드백 신호 | 자기 개선 대상 |
|----------|------------|--------------|
| **Anthropic Quickstart** | 테스트 pass/fail + git | 태스크 코드 |
| **SWE-bench / SWE-agent** | 패치 적용 + 테스트 통과 | 태스크 코드 |
| **karpathy/autoresearch** | val_bpb (5분 고정 예산) | 학습 코드 |
| **Darwin Gödel Machine** | SWE-bench / Polyglot 점수 | 에이전트 자체 소스 코드 |
| **AlphaEvolve** | 자동화된 평가자 점수 | 알고리즘 구현 |
| **LangChain DeepAgents** | Terminal Bench 점수 | 하네스 설정 |

공통점: **측정 대상이 모두 코드입니다.** 테스트가 통과했나? 벤치마크 점수가 올랐나? 패치가 적용됐나?

### 2.2 이 하네스들의 공통 패턴

Anthropic의 두 블로그 글에서 드러난 핵심 설계 패턴:

**1) Initializer + Coding Agent 분리 (다중 세션 연속성)**
- 첫 세션에서 200+ 항목의 feature list를 생성 (모두 `failing` 상태)
- 이후 세션마다 하나씩 구현 → 검증 → 커밋 → 진행 파일 업데이트
- "교대 근무 인수인계 문제" 해결: 새 에이전트 인스턴스는 이전 작업의 기억이 없음

**2) Planner / Generator / Evaluator 트라이어드 (GAN 영감)**
- Planner: 1-4문장 프롬프트 → 상세 제품 스펙
- Generator: 점진적 구현 (React/Vite/FastAPI/SQLite)
- Evaluator: Playwright로 실행 중인 앱을 실제 사용자처럼 테스트
- 핵심 인사이트: *"독립 평가자를 회의적으로 튜닝하는 게, 생성자에게 자기비판을 가르치는 것보다 훨씬 쉽다"*

**3) Sprint Contract 패턴**
- 구현 전에 생성자와 평가자가 "완료"의 정의를 합의
- 고수준 사용자 스토리와 구현 가능한 명세 사이의 간극을 연결

**결과 예시 (Anthropic):**
- 단일 에이전트: 20분, $9 — 핵심 게임플레이가 작동 안 함
- 하네스 사용: 6시간, $200 — 16개 기능, 10 스프린트, 실제 플레이 가능한 게임
- 20배 비싸지만, 단일 에이전트 결과물은 *쓸 수 없는 것*이었고 하네스 결과물은 *실제로 작동하는 것*

---

## 3. 근데 Long-Running Agent가 꼭 코드만 만들어야 하나?

**여기서 Dormammu의 주장이 시작됩니다.**

모든 하네스가 코드를 측정합니다. 테스트 통과, 벤치마크 점수, 컴파일 성공. 하지만 long-running agent가 생산할 수 있는 것은 코드만이 아닙니다.

**생산의 형태는 다양할 수 있습니다:**

| 생산물 | 피드백 신호 | 예시 하네스 |
|--------|-----------|------------|
| 코드 | 테스트 pass/fail | SWE-bench, Anthropic Quickstart |
| 학습된 모델 | val_bpb | karpathy/autoresearch |
| 알고리즘 | 평가자 점수 | AlphaEvolve |
| **시뮬레이션된 세계** | **emergence, narrative, diversity, novelty** | **Dormammu** |

Dormammu는 long-running agent 하네스를 **컨텐츠 생산**에 적용한 것입니다. 구체적으로는, "만약에?"라는 질문에서 시작해서 **살아 있는 세계를 시뮬레이션**하는 것.

> 핵심 주장: **하네스의 원리는 범용적이다.** 피드백 신호가 정량적이기만 하면, 그 생산물이 코드든 시뮬레이션이든 알고리즘이든 같은 구조가 작동한다. Dormammu는 이 원리를 시뮬레이션 도메인에 적용한 최초의 하네스다.

---

## 4. 왜 DFS 탐색인가?

### 4.1 단순 프롬프팅의 한계

Claude Code에게 직접 물어봅시다:

> *"에르빈이 아르민 대신 살았다면 결말은 어떻게 달라졌을까?"*

Claude는 훌륭한 답변을 줄 것입니다. 하지만 그것은 **하나의 선형 서사**입니다. 하나의 가능성. 모델이 가장 그럴듯하다고 판단한 하나의 경로.

문제:
- **탐색 없음** — 모델은 첫 번째로 떠올린 가설을 끝까지 추적합니다
- **비교 불가** — "에르빈이 거인을 받는 경우"와 "거부하는 경우"를 나란히 놓고 볼 수 없습니다
- **품질 측정 없음** — "이 서사가 흥미로운가?"를 물어볼 수 없습니다
- **반복 불가** — 같은 질문에 같은 답을 얻을 수 없습니다 (온도, 문맥에 따라 달라짐)

### 4.2 DFS가 해결하는 것

DFS 시나리오 트리는 **가능성 공간을 체계적으로 탐색**합니다.

```
"에르빈이 살았다면?"
        │
        ├─ 가설 A: 에르빈이 초대형 거인을 물려받음
        │    ├─ A-1: 지하실 진실 발견 → composite: 0.87
        │    │    ├─ A-1-1: 지크와 비밀 협상 → 0.93 ★
        │    │    └─ A-1-2: 공개 선전포고 → 0.71
        │    └─ A-2: 진실 거부 → 0.42 (가지치기)
        │
        ├─ 가설 B: 에르빈이 거인을 거부
        │    └─ ...
        │
        └─ 가설 C: 리바이가 다른 선택
             └─ ...
```

각 노드에서:
1. **3개의 가설을 생성** — 모델이 첫 번째 답만 추적하지 않음
2. **각 가설을 시뮬레이션** — Big-5 성격의 에이전트들이 실제로 살아감
3. **4차원 점수를 매김** — emergence, narrative, diversity, novelty
4. **확장 또는 가지치기** — composite > 0.3이면 더 깊이, ≤ 0.3이면 잘라냄

이것은 Tree of Thought(ToT)와 같은 계보의 접근입니다. ToT가 BFS/DFS로 추론 공간을 탐색하듯, Dormammu는 DFS로 **서사 공간**을 탐색합니다. 단, ToT와 달리 각 노드가 단순한 텍스트 생성이 아니라 **에이전트 기반 시뮬레이션**입니다.

### 4.3 왜 DFS인가? (BFS가 아니라)

| | DFS | BFS |
|---|---|---|
| **탐색 방식** | 하나의 경로를 끝까지 추적한 뒤 백트래킹 | 모든 경로를 한 단계씩 균등하게 |
| **비용** | 유망한 경로를 깊이 파는 데 집중 | 넓게 퍼져서 비용 폭발 |
| **서사적 장점** | **하나의 완결된 이야기**를 먼저 얻음 | 모든 이야기가 반쯤만 진행됨 |
| **조기 종료** | 가능 — 최고 경로를 찾으면 멈출 수 있음 | 어려움 — 모든 게 미완성 |

시뮬레이션에서 DFS가 BFS보다 나은 이유: **서사는 깊이에서 온다**. "에르빈이 거인을 물려받고 → 지하실 진실을 발견하고 → 지크와 협상하고 → 최후의 연설을 하는" 10단계 경로가 흥미롭습니다. 3단계에서 멈춘 10개의 경로는 흥미롭지 않습니다.

그리고 가지치기(pruning)가 핵심입니다. composite ≤ 0.3인 분기는 잘라냅니다. BFS는 이 가지치기의 이점을 제대로 활용할 수 없습니다 — 깊이가 얕아서 점수가 의미 있는 수준에 도달하기 전에 이미 비용이 폭발합니다.

---

## 5. 왜 이 하네스여야 하는가?

### 5.1 "그냥 클로드한테 물어보면 되잖아"에 대한 답

맞습니다. 클로드한테 물어보면 좋은 답을 줍니다. 하지만:

| | Claude에게 직접 질문 | Dormammu |
|---|---|---|
| **출력** | 하나의 선형 서사 (2-3 페이지) | 100개 노드의 분기 트리, 최고 경로 composite 0.93 |
| **캐릭터** | 설명 텍스트 | Big-5 성격 + 기억 + 목표 + 관계를 가진 에이전트 |
| **탐색** | 모델의 첫 번째 직관 | 체계적 DFS — 3개 가설 × N 깊이 |
| **품질 측정** | 없음 ("좋아 보이는데?") | 4차원 정량 점수 |
| **비교** | 불가능 | 형제 분기 간 나란히 비교 |
| **재현성** | 온도/문맥에 따라 달라짐 | 고정 파라미터 벤치마크 |
| **자기 개선** | 없음 | evolve 루프 — 엔진이 자기 코드를 개선 |

핵심 차이: Claude의 답변은 **1회성 추론**입니다. Dormammu의 출력은 **체계적 탐색의 결과**입니다.

### 5.2 "비슷한 시뮬레이션 도구 많잖아"에 대한 답

Stanford Generative Agents, AI Dungeon, NovelAI 같은 프로젝트들이 있습니다. 차이점:

| | Generative Agents | AI Dungeon / NovelAI | Dormammu |
|---|---|---|---|
| **구조** | 단일 타임라인 | 선형 인터랙티브 서사 | **DFS 분기 트리** |
| **품질 신호** | 없음 (관찰만) | 사용자 선택 | **4차원 자동 점수** |
| **자기 개선** | 없음 | 없음 | **evolve 루프** |
| **목적** | 연구 논문 | 엔터테인먼트 | **카운터팩추얼 탐색 + 하네스** |

Dormammu가 독특한 이유:

1. **분기한다** — 하나의 타임라인이 아니라 가능성 트리를 만듭니다
2. **점수를 매긴다** — "흥미로운가?"를 숫자로 답합니다
3. **가지치기한다** — 흥미롭지 않은 경로를 자동으로 버립니다
4. **자기 개선한다** — 시뮬레이션 엔진 코드를 스스로 고칩니다

이 네 가지를 동시에 하는 시뮬레이션 도구는 Dormammu뿐입니다.

### 5.3 하네스 관점에서의 포지셔닝

Dormammu는 코딩 하네스(Anthropic Quickstart, SWE-agent)와 같은 **설계 원리**를 시뮬레이션에 적용합니다:

| 코딩 하네스 패턴 | Dormammu 대응 |
|-----------------|--------------|
| Feature list (pass/fail) | Quality scores (4차원) |
| 단위 테스트 | Benchmark simulation (고정 파라미터) |
| CI/CD 파이프라인 | Evolve loop (benchmark → diagnose → improve) |
| git commit on success | Commit on score improvement |
| git revert on failure | Rollback on score drop |
| Evaluator agent (Playwright) | HypothesisEvaluator (4차원 점수) |
| Sprint contract | Score threshold (composite > 0.3) |

**같은 원리, 다른 도메인.** 테스트 대신 시뮬레이션 품질. 코드 대신 세계.

### 5.4 사이버네틱스로 보는 Dormammu

@odysseus0z의 프레임을 빌리면, 모든 하네스의 핵심 질문은 이것입니다:

> *"어느 레이어에서 피드백 루프를 닫으려 하는가? 그 레이어의 센서와 액추에이터는 무엇인가?"*

기존 하네스들이 닫는 루프:

| 하네스 | 센서 (측정) | 액추에이터 (실행) | 닫는 루프 |
|--------|-----------|-----------------|----------|
| 컴파일러 | 구문 분석 | 에러 메시지 | 문법 |
| 테스트 스위트 | assertion | pass/fail | 행동 |
| SWE-agent | 패치 + 테스트 | 코드 수정 | 버그 수정 |
| Anthropic Quickstart | feature list pass/fail | 에이전트 코딩 | 기능 완성 |
| karpathy/autoresearch | val_bpb | train.py 수정 | ML 성능 |

**Dormammu가 닫는 루프:**

| 센서 | 액추에이터 | 닫는 루프 |
|------|-----------|----------|
| HypothesisEvaluator (4차원 점수) | DFS expand/prune | **"이 세계가 흥미로운가?"** |
| Benchmark (고정 파라미터 시뮬레이션) | evolve (소스 코드 수정) | **"시뮬레이션 엔진이 더 나아졌는가?"** |

Dormammu는 두 겹의 사이버네틱 루프를 가집니다:
1. **내부 루프 (시뮬레이션 시간)** — 각 분기를 점수로 측정하고 확장/가지치기 결정. 센서: 4차원 점수. 액추에이터: DFS 탐색.
2. **외부 루프 (개발 시간)** — 시뮬레이션 엔진 코드 자체를 개선. 센서: 벤치마크 composite 변화. 액추에이터: AI가 소스 코드를 수정.

**이전까지 "이 시뮬레이션이 흥미로운가?"라는 질문에 피드백 루프를 닫을 수 있는 도구는 없었습니다.** 사람이 읽고 판단하는 게 유일한 방법이었습니다. Dormammu는 이 레이어에서 처음으로 센서(4차원 점수)와 액추에이터(DFS + evolve)를 갖춘 사이버네틱 제어 시스템입니다.

---

## 6. 핵심 메시지 요약

### README에 녹여넣을 포인트

1. **Long-running agent의 생산물은 코드만이 아니다.**
   - 하네스 엔지니어링의 원리(피드백 루프, 자기 개선, 정량적 측정)는 범용적
   - Dormammu는 이 원리를 "시뮬레이션된 세계"에 적용한 하네스
   - 코드를 더 많이 쓰는 게 아니라, **세계를 더 흥미롭게 만드는** 에이전트

2. **단순 프롬프팅 vs 체계적 탐색**
   - "에르빈이 살았다면?"에 대한 Claude의 답 = 하나의 직관
   - Dormammu의 답 = 100개 노드, 4차원 점수, 최고 경로 0.93
   - 차이는 양이 아니라 **구조** — 비교 가능하고, 측정 가능하고, 재현 가능

3. **왜 DFS인가**
   - 서사는 깊이에서 온다 — 10단계 완결된 이야기 > 3단계짜리 10개
   - 가지치기가 핵심 — 흥미롭지 않은 가능성을 조기에 제거
   - 비용 효율 — BFS는 깊이 전에 비용이 폭발

4. **왜 이 하네스인가**
   - 분기 + 점수 + 가지치기 + 자기 개선을 동시에 하는 시뮬레이션 도구는 없음
   - 코딩 하네스의 검증된 패턴(Anthropic, Karpathy)을 시뮬레이션에 이식
   - 피드백 신호가 정량적이면, 하네스가 작동한다

---

## 참고 문헌

### Anthropic 하네스 엔지니어링
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — Initializer + Coding Agent 패턴, feature list, session continuity
- [Harness Design for Long-Running Application Development](https://www.anthropic.com/engineering/harness-design-long-running-apps) — Planner/Generator/Evaluator 트라이어드, sprint contracts, GAN-inspired architecture

### OpenAI & 하네스 엔지니어링 일반
- [OpenAI: Harness Engineering](https://openai.com/index/harness-engineering/) — 7명 엔지니어, 100만줄, 코드 직접 작성 0줄, "Humans steer. Agents execute."
- [@odysseus0z: Harness Engineering Is Cybernetics](https://x.com/odysseus0z/status/2030416758138634583) — 하네스 = 사이버네틱스의 아키텍처 레이어 적용
- [Martin Fowler: Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)
- [LangChain: The Anatomy of an Agent Harness](https://blog.langchain.com/the-anatomy-of-an-agent-harness/)
- [LangChain: Improving Deep Agents with Harness Engineering](https://blog.langchain.com/improving-deep-agents-with-harness-engineering/) — 하네스만 바꿔서 52.8% → 66.5%
- [HumanLayer: Skill Issue — Harness Engineering for Coding Agents](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)

### 자기 개선 에이전트
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 700 experiments / 2 days, val_bpb metric, 5-minute fixed budget
- [Darwin Gödel Machine (Sakana AI)](https://arxiv.org/abs/2505.22954) — SWE-bench 20% → 50%, evolutionary archive
- [AlphaEvolve (Google DeepMind)](https://arxiv.org/abs/2506.13131) — Dual-model evolutionary loop, 0.7% Google compute recovered

### 트리 탐색 에이전트
- [Tree of Thought (Yao et al.)](https://arxiv.org/abs/2305.10601) — BFS/DFS for reasoning space exploration
- [Reflective MCTS (R-MCTS)](https://arxiv.org/html/2410.02052v1) — Contrastive reflection + multi-agent debate

### 시뮬레이션 에이전트
- [Stanford Generative Agents](https://arxiv.org/abs/2304.03442) — Memory streams, reflection, planning
- [Anthropic Autonomous Coding Quickstart](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)
