# 다음 세션 가이드 — Dormammu 진화 대시보드 테스트

> 이 문서는 다음 Claude Code 세션에서 Dormammu 자율 개선 루프를 실행하고,
> 진화 대시보드(세대별 품질 추이)를 확인하기 위한 단계별 안내입니다.

---

## 사전 준비

1. Claude Code를 `apps/emergent-world/` 디렉토리에서 실행
2. `.env` 파일에 `OPENAI_API_KEY`가 설정되어 있는지 확인

---

## Step 1: 환경 세팅

Claude Code에 입력:

```
/dormammu-setup
```

이 명령이 자동으로:
- Python 환경 확인
- 의존성 설치
- .env 검증
- 테스트 실행 (27개 통과 확인)
- 베이스라인 벤치마크 실행

---

## Step 2: 시뮬레이션 목표 설정

Claude Code에 입력:

```
/dormammu-goal "앞으로 100년, 인류에게는 어떤 미래가 올 것인가?"
```

또는 다른 주제:
```
/dormammu-goal "진격의 거인 — 에렌이 땅울림을 하지 않았다면 100년 후"
/dormammu-goal "AI가 인간의 일자리를 완전히 대체한 세계 50년"
/dormammu-goal "기후변화로 해수면이 5m 상승한 도시의 100년"
```

---

## Step 3: 자율 개선 루프 실행

Claude Code에 입력:

```
/dormammu-evolve
```

옵션:
- `--hours 1` — 1시간 동안 자율 개선 (테스트용)
- `--hours 5` — 5시간 풀 세션
- `--cycles 3` — 정확히 3 사이클만 실행

**테스트 목적이라면 짧게:**
```
/dormammu-evolve --cycles 3
```

이 명령이 자동으로 반복하는 루프:
```
1. ese benchmark → 현재 품질 점수 측정
2. ese diagnose → 최약점 발견 (예: diversity 0.31)
3. 코드 수정 (해당 모듈의 프롬프트/로직 개선)
4. pytest → 테스트 통과 확인
5. ese benchmark → 점수 비교
6. 개선됐으면 커밋, 아니면 롤백
7. 다음 약점으로 이동
```

---

## Step 4: 결과 확인

### 4-1. 터미널에서 점수 추이 확인

```
/dormammu-status
```

세대별 점수 변화를 보여줌:
```
Gen 1: ████░░░░░░ 0.47
Gen 2: █████░░░░░ 0.55
Gen 3: ███████░░░ 0.68
```

### 4-2. 2D 시각화로 시뮬레이션 관찰

터미널 2개가 필요합니다:

**터미널 1 — 백엔드:**
```bash
cd apps/emergent-world
ese serve
```

**터미널 2 — 프론트엔드:**
```bash
cd apps/emergent-world/frontend
npm run dev
```

브라우저에서 `http://localhost:5173` 접속:
- 대시보드에서 시뮬레이션 카드 클릭
- 2D 맵에서 에이전트 이동/대화 관찰
- 타임라인 슬라이더로 리플레이
- 재생 버튼으로 자동 진행

### 4-3. 벤치마크 히스토리 파일 확인

```bash
cat data/benchmarks/history.jsonl
```

각 줄이 한 세대의 점수:
```json
{"timestamp": "...", "git_hash": "...", "scores": {"avg_composite": 0.47}}
{"timestamp": "...", "git_hash": "...", "scores": {"avg_composite": 0.55}}
```

### 4-4. 진화 리포트 확인

```bash
ls .ese/reports/
cat .ese/reports/evolution_*.md
```

---

## Step 5: Before/After 비교 (데모용)

두 시뮬레이션을 나란히 비교하려면:

```
# Gen 1 시뮬레이션 실행
ese run "인류의 미래 100년" --max-depth 1 --cost-limit 0.5

# (evolve 후) 같은 주제로 다시 실행
ese run "인류의 미래 100년" --max-depth 1 --cost-limit 0.5

# 두 결과를 프론트엔드에서 각각 관찰
ese serve
```

대시보드에 두 시뮬레이션이 모두 표시되므로, 각각 클릭해서 에이전트 행동의 질적 차이를 비교할 수 있습니다.

---

## 문제 발생 시

| 문제 | 해결 |
|------|------|
| `/dormammu-setup` 명령 안 됨 | Claude Code 재시작 (슬래시 커맨드 로딩 필요) |
| OpenAI API 에러 | `.env` 파일의 `OPENAI_API_KEY` 확인 |
| 테스트 실패 | `pytest tests/ -v`로 어떤 테스트가 실패하는지 확인 |
| 프론트엔드 안 됨 | `dormammu serve`가 먼저 실행 중인지 확인 (백엔드 필요) |
| DB 에러 | `rm data/simulations/ese.db*` 후 재실행 |

---

## 한 줄 요약

```
/dormammu-setup → /dormammu-goal "주제" → /dormammu-evolve --cycles 3 → /dormammu-status
```

이 4단계면 진화 대시보드를 테스트할 수 있습니다.
