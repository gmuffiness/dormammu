# Claude Code 플러그인 패턴 분석: OMC vs Ouroboros

> 도르마무를 Claude Code 네이티브 하네스로 전환하기 위한 레퍼런스 문서.
> 두 프로젝트(oh-my-claudecode, ouroboros)가 Claude Code 세션 안에서 LLM 호출을 어떻게 처리하는지 분석.

---

## 핵심 발견: "LLM API 호출이 없다"

두 프로젝트 모두 **Anthropic API를 직접 호출하지 않는다**. Claude Code 세션 자체가 LLM이므로, 플러그인은 **오케스트레이션(지시/조합/라우팅)**만 담당하고 실제 LLM 추론은 호스트 세션이 처리한다.

```
기존 도르마무:
  Python → openai.AsyncOpenAI → GPT-4o API → 응답 파싱

OMC / Ouroboros 패턴:
  Skill(마크다운) → Claude Code 세션이 읽고 실행
  → Agent(서브에이전트) 위임 → 서브에이전트가 도구 사용하며 작업
  → 결과 반환 → 부모가 종합
```

---

## 1. oh-my-claudecode (OMC)

### 아키텍처

```
Claude Code Session
├── CLAUDE.md (시스템 프롬프트 주입)
├── Skills (skills/{name}/SKILL.md)
│   → 마크다운 파일 = 실행 지시서
│   → Claude가 읽고 단계별로 따름
├── Agents (agents/{name}.md)
│   → Task(subagent_type="oh-my-claudecode:executor") 로 위임
│   → 서브에이전트는 부모의 도구(Read, Write, Bash 등) 상속
├── MCP Server (bridge/mcp-server.cjs)
│   → in-process MCP로 18+ 커스텀 도구 제공
│   → LSP, AST grep, Python REPL, 상태 관리 등
├── Hooks (31개)
│   → UserPromptSubmit: 키워드 감지 → 스킬 활성화
│   → Stop: ralph 모드에서 검증 전 중지 방지
│   → PostToolUse: 에러 복구, 규칙 주입
└── State (.omc/)
    → .omc/state/{mode}-state.json
    → .omc/plans/, .omc/notepad.md
```

### LLM 호출 패턴

**직접 API 호출 없음.** 모든 "LLM 작업"은 Claude Code 네이티브 도구로 수행:

| 작업 | 도르마무 현재 방식 | OMC 방식 |
|------|-------------------|----------|
| 텍스트 생성 | `openai.chat.completions.create()` | Claude 세션이 직접 생성 (도구 불필요) |
| JSON 파싱 | API response → `json.loads()` | Claude가 JSON을 직접 생성/파싱 |
| 병렬 작업 | `asyncio.gather()` | `Agent(run_in_background=true)` 여러 개 동시 실행 |
| 전문가 위임 | 프롬프트 변경 | `Agent(subagent_type="executor")` — 별도 컨텍스트 |
| 상태 추적 | SQLite DB | `.omc/state/` JSON 파일 |

### 핵심 패턴: Skill = 마크다운 실행 지시서

```markdown
# /oh-my-claudecode:autopilot

## Phase 0: Expansion
1. Agent(analyst) — 요구사항 추출
2. Agent(architect) — 기술 스펙 설계
3. 결과를 .omc/autopilot/spec.md에 저장

## Phase 1: Planning
1. Agent(architect) — 실행 계획 수립
2. Agent(critic) — 계획 검증
3. 결과를 .omc/plans/autopilot-impl.md에 저장

## Phase 2: Execution
1. ralph + ultrawork 활성화
2. 병렬 executor 에이전트 실행
...
```

Claude Code가 이 마크다운을 읽으면, **각 단계를 순서대로 실행**한다. Agent 도구로 서브에이전트를 위임하고, 파일에 상태를 저장하고, 다음 단계로 진행.

---

## 2. Ouroboros

### 아키텍처

```
3개의 실행 컨텍스트:

Context A: Claude Code Host Session
├── Skills (skills/{name}/SKILL.md)
│   → YAML frontmatter에 MCP 도구 매핑
│   → /ouroboros:interview → mcp_tool: ouroboros_interview
├── Agents (agents/*.md)
│   → 역할 설명 마크다운 (시스템 프롬프트로 주입)
│   → 9개: interviewer, ontologist, evaluator, hacker, simplifier 등
└── MCP 도구 호출 → Context B로 전달

Context B: MCP Server (Python, FastMCP)
├── uvx --from ouroboros-ai ouroboros mcp serve
├── Tool Handlers (20+ MCP 도구)
│   → InterviewHandler, ExecuteSeedHandler, EvaluateHandler 등
├── JobManager — 비동기 백그라운드 작업
├── EventStore (SQLite) — 이벤트 소싱 기반 상태
└── 실행 시 → Context C 자식 프로세스 생성

Context C: Orchestrator Runtime (자식 에이전트 세션)
├── ClaudeAgentAdapter — Claude Code 세션 생성
├── OrchestratorRunner — Seed 기반 실행
├── LLMAdapter.complete() — 라우팅/평가용 LLM 호출
└── PAL Router — Frugal/Standard/Frontier 모델 선택
```

### LLM 호출 패턴

Ouroboros는 **하이브리드 접근**:

| 컨텍스트 | LLM 호출 방식 |
|----------|--------------|
| Context A (호스트) | Claude Code 네이티브 (API 호출 없음) |
| Context B (MCP 서버) | `LLMAdapter.complete()` — 인터뷰 질문 생성 시 |
| Context C (자식 세션) | `ClaudeAgentAdapter` — 자식 Claude Code 세션 스트리밍 |

### 핵심 패턴: Event Sourcing + MCP

```python
# 모든 상태 변경이 불변 이벤트
"interview.session.created"
"interview.answer.recorded"
"seed.generated"
"execution.started"
"execution.ac.completed"
"evaluation.stage_passed"

# 상태 = 이벤트 재생으로 복원
# 크래시 후 재개, 감사 추적, 드리프트 감지 가능
```

### 핵심 패턴: Specification-First (Seed)

```yaml
# Seed = 불변 실행 명세
id: "abc123"
goal: "REST API 구축"
constraints: ["Python 3.10+", "FastAPI"]
acceptance_criteria:
  - "GET /users 엔드포인트 작동"
  - "JWT 인증 구현"
ontology:
  user: { definition: "시스템 사용자", aspects: [...] }
ambiguity_score: 0.15  # 0.2 이하면 실행 가능
```

---

## 3. 비교 요약

| 차원 | OMC | Ouroboros | 도르마무 현재 |
|------|-----|-----------|-------------|
| **LLM 호출** | 없음 (호스트 세션) | 하이브리드 (호스트 + MCP 내부) | 직접 API 호출 (OpenAI) |
| **에이전트 정의** | 마크다운 프롬프트 파일 | 마크다운 역할 설명 | Python 클래스 |
| **스킬 정의** | SKILL.md (마크다운) | SKILL.md (YAML frontmatter) | Click CLI 커맨드 |
| **상태 관리** | JSON 파일 (.omc/) | Event Sourcing (SQLite) | SQLite (직접) |
| **병렬 실행** | Agent(background) + tmux | Level-based AC tree + subagent | asyncio DFS |
| **평가** | verifier 에이전트 위임 | 3단계 게이트 (Mechanical→Semantic→Consensus) | LLM 기반 6차원 점수 |
| **피드백 루프** | ralph (검증까지 반복) | Evolution (Seed 변이 → 재실행) | DFS expand/prune |
| **MCP** | in-process (TypeScript) | 별도 프로세스 (Python FastMCP) | 없음 |

---

## 4. 도르마무 전환 설계 방향

### 방향 A: OMC 스타일 (순수 마크다운 오케스트레이션)

```
/dormammu:simulate "진격의 거인 What-If"
  → SKILL.md 읽기
  → Phase 1: Agent(researcher) — 토픽 리서치
  → Phase 2: Agent(persona-gen) — 캐릭터 생성
  → Phase 3: DFS 시뮬레이션 루프
     → 각 턴: Claude가 직접 내러티브 생성
     → 평가: Agent(evaluator) — 6차원 점수
     → 확장/가지치기 결정
  → Phase 4: 결과를 DB에 저장
```

**장점**: 단순, API 키 불필요, Claude Code 도구 전체 활용
**단점**: 토큰 소비 높음 (모든 LLM 작업이 호스트 세션 토큰), 병렬 제어 제한

### 방향 B: Ouroboros 스타일 (MCP 서버 + 자식 세션)

```
/dormammu:simulate "진격의 거인 What-If"
  → MCP 도구 호출: ouroboros_execute_seed
  → MCP 서버가 백그라운드 작업 시작
  → Seed 기반으로 자식 Claude 세션 생성
  → 자식 세션이 실행, 이벤트 발행
  → 호스트 세션은 job_status로 모니터링
```

**장점**: 백그라운드 실행, 이벤트 소싱, 크래시 복구
**단점**: 복잡도 높음, MCP 서버 구현 필요

### 방향 C: 하이브리드 (추천)

```
도르마무를 Claude Code 스킬로 래핑하되,
핵심 시뮬레이션 엔진은 Python으로 유지.

/dormammu:simulate "진격의 거인 What-If"
  → SKILL.md가 실행 절차 정의
  → Claude가 Python 스크립트를 Bash로 실행
  → LLM이 필요한 부분만 Claude 세션으로 위임:
     → Agent(subagent) 로 내러티브 생성
     → Agent(subagent) 로 평가
  → 결과를 다시 Python 엔진에 전달
  → Python이 DFS 트리/DB/상태 관리
```

**장점**: 기존 엔진(DFS, ScenarioTree, WorldState) 재활용 가능,
LLM 호출만 Claude Code 네이티브로 교체, API 키 불필요
**단점**: Python↔Claude Code 간 데이터 교환 설계 필요

---

## 5. 핵심 교훈

### "프롬프트가 코드다"

OMC와 Ouroboros 모두 **에이전트 = 마크다운 프롬프트 파일**. Python/TypeScript 클래스가 아니라 `.md` 파일이 에이전트의 행동을 정의한다. Claude Code가 이 파일을 읽으면 해당 역할로 동작한다.

### "상태는 파일이다"

복잡한 DB 대신 `.omc/state/` 또는 이벤트 로그로 상태 관리. Claude Code 세션이 파일을 읽고 쓰는 것이 가장 자연스러운 상태 관리 방식.

### "API 호출 = 에이전트 위임"

`openai.chat.completions.create(system_prompt, user_prompt)` 대신 `Agent(prompt=system_prompt + user_prompt)`로 동일한 결과를 얻을 수 있다. 서브에이전트는 별도 컨텍스트 윈도우에서 실행되므로 컨텍스트 오염도 없다.

### "MCP는 선택사항"

OMC는 MCP 없이도 핵심 기능이 동작한다 (스킬 + 에이전트 + 훅). Ouroboros는 MCP를 백그라운드 실행의 브릿지로 사용. 도르마무도 우선 MCP 없이 시작하고, 백그라운드 실행이 필요해지면 추가하는 것이 합리적.

---

## 참고 자료

- oh-my-claudecode: https://github.com/yeachan-heo/oh-my-claudecode
- ouroboros: https://github.com/Q00/ouroboros
- Anthropic "Effective Harnesses for Long-Running Agents" (2025.11)
- Anthropic "Harness Design for Long-Running Apps" (2026.03)
