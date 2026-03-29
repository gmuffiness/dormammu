# RimBot & AI Dungeon 심층 리서치

> Dormammu 참조 문서
> 작성일: 2026-03-22

---

## 목차

1. [RimBot 분석](#1-rimbot-분석)
   - 1.1 프로젝트 개요
   - 1.2 아키텍처
   - 1.3 에이전트 의사결정 루프
   - 1.4 월드 스테이트 표현 방식
   - 1.5 메모리 및 컨텍스트 관리
   - 1.6 Dormammu 관점의 시사점
2. [AI Dungeon 분석](#2-ai-dungeon-분석)
   - 2.1 프로젝트 개요
   - 2.2 내러티브 생성 메커니즘
   - 2.3 월드 스테이트 관리
   - 2.4 컨텍스트 구성 아키텍처
   - 2.5 메모리 시스템
   - 2.6 일관성 유지 솔루션 (SCORE)
   - 2.7 실패 패턴과 교훈
3. [Dormammu 적용 시사점 종합](#3-dormammu-적용-시사점-종합)

---

## 1. RimBot 분석

**소스**: https://github.com/kolbytn/RimBot
**언어**: C# (.NET Framework 4.7.2)
**최초 커밋**: 2026-02-07 / 마지막 업데이트: 2026-02-11
**LLM 지원**: Anthropic (Claude), OpenAI (GPT), Google (Gemini)

### 1.1 프로젝트 개요

RimBot은 RimWorld 콜로니스트에게 자율적인 LLM 기반 두뇌를 부여하는 게임 모드다. 각 콜로니스트는 자신의 주변을 **스크린샷으로 관찰**하고, LLM으로 추론하며, **도구 호출(tool-use)** 을 통해 게임 세계에 실제로 작용한다. 건물 건축, 작업 우선순위 조정, 연구 설정, 동물 관리까지 21개 도구를 사용한다.

핵심적인 특징은 게임 엔진의 **시각 정보(스크린샷)** 를 LLM의 입력으로 직접 사용한다는 점이다. 텍스트 기반 상태 덤프가 아니라 실제 렌더링된 이미지를 통해 에이전트가 공간을 인지한다.

### 1.2 아키텍처

```
RimBot/
  Main.cs                  엔트리 포인트, Harmony 패치, 틱 루프
  Brain.cs                 콜로니스트별 LLM 대화 & 에이전트 루프
  BrainManager.cs          Brain 생명주기, 콜로니스트 동기화, 스케줄링
  AgentRunner.cs           도구 호출 루프 (최대 10회 반복)
  ScreenshotCapture.cs     오프스크린 렌더링 파이프라인
  Models/
    ILanguageModel.cs      프로바이더 인터페이스
    AnthropicModel.cs      Claude API 구현
    OpenAIModel.cs         GPT API 구현
    GoogleModel.cs         Gemini API 구현
  Tools/
    GetScreenshotTool.cs   시각 관찰 도구
    InspectCellTool.cs     셀 상세 검사
    ScanAreaTool.cs        범위 스캔
    ArchitectBuildTool.cs  건물 건축 (카테고리별 10개)
    ... (총 21개 도구)
```

**스레딩 모델**: LLM 네트워크 호출은 `Task.Run`으로 백그라운드 스레드에서 실행. 모든 Unity/RimWorld API 접근(도구 실행, UI 업데이트)은 메인 스레드에서만 가능. `BrainManager.EnqueueMainThread()`가 `ConcurrentQueue<Action>`을 유지하며, `TickManagerPatch`가 매 틱마다 드레인.

### 1.3 에이전트 의사결정 루프

`AgentRunner.cs`가 구현하는 핵심 루프:

```csharp
// AgentRunner.cs - 핵심 루프 (최대 10회 반복)
for (int i = 0; i < MaxIterations; i++)
{
    // 1. LLM 호출 (백그라운드 스레드)
    response = await llm.SendToolRequest(conversation, tools, model, apiKey, maxTokens, thinkingLevel);

    // 2. max_tokens 도달 + 도구 호출 없음 → 폐기 후 재시도
    if (response.StopReason == StopReason.MaxTokens && !hasToolCalls)
        continue;

    // 3. assistant 메시지를 대화에 추가
    conversation.Add(new ChatMessage("assistant", assistantParts));

    // 4. 도구 호출 없으면 종료
    if (response.StopReason != StopReason.ToolUse || !hasToolCalls)
        return result;

    // 5. 메인 스레드에서 도구 실행 (TaskCompletionSource 브릿지)
    toolResults = await ExecuteToolsOnMainThread(response.ToolCalls, toolContext);

    // 6. 도구 결과를 user 메시지로 추가하고 반복
    conversation.Add(new ChatMessage("user", resultParts));
}
```

한 사이클에서 최대 10번의 LLM 호출이 발생하며, 사이클 간 **30초 쿨다운**이 있다. 에이전트는 idle/wandering 상태일 때 즉시 트리거되고, 바쁜 콜로니스트는 30초 대기 후 재시도한다.

### 1.4 월드 스테이트 표현 방식

RimBot의 가장 독특한 설계 선택은 **시각 기반 월드 인지**다.

#### 스크린샷 파이프라인

`ScreenshotCapture.cs`는 오프스크린 렌더링 기법을 사용한다:

```csharp
// GetScreenshotTool.cs - 도구 정의
public ToolDefinition GetDefinition()
{
    return new ToolDefinition
    {
        Name = "get_screenshot",
        Description = "Capture a screenshot of the area around you. Returns a top-down view image. " +
            "The size parameter controls how many tiles are visible in each direction from center " +
            "(e.g. size=24 shows a 48x48 tile area). Your position is at the center of the image.",
        ParametersJson = "{\"type\":\"object\",\"properties\":{\"size\":{\"type\":\"integer\"," +
            "\"description\":\"Tiles visible in each direction from center (8=close 16x16, 24=standard 48x48, 48=wide 96x96)\"," +
            "\"minimum\":8,\"maximum\":48}},\"required\":[]}"
    };
}
```

오프스크린 렌더링의 핵심 문제: `Camera.Render()`는 맵 섹션 메시가 생성되지 않으면 검은 이미지를 반환한다. `ScreenshotCapture.cs`는 ViewRect를 스푸핑하여 RimWorld가 오프스크린 영역의 모든 섹션을 재생성하도록 강제한다.

#### 좌표 시스템

LLM에게는 자신의 위치를 `(0,0)`으로 하는 상대 좌표계를 제공한다: "+X=동쪽(오른쪽), +Z=북쪽(위)". 이 상대 좌표 방식은 에이전트가 절대 좌표를 외울 필요 없이 즉각적인 공간 추론이 가능하게 한다.

#### 보조 정보 도구

스크린샷만으로는 불충분한 정보를 위한 도구들:

| 도구 | 용도 |
|------|------|
| `inspect_cell` | 특정 셀의 지형, 건물, 아이템, 폰 상세 정보 |
| `scan_area` | 반경 내 모든 오브젝트를 카테고리별로 목록화 |
| `find_on_map` | 이름으로 맵 전체 검색 |
| `get_pawn_status` | 콜로니스트의 체력, 필요, 스킬, 장비 |

### 1.5 메모리 및 컨텍스트 관리

#### 대화 이력 유지

RimBot은 **세션 간 지속 대화(persistent conversation)** 를 유지한다. 각 Brain 인스턴스가 `agentConversation` 리스트를 보존하며, 매 사이클에 새 user 메시지를 추가한다:

```csharp
// Brain.cs - 사이클 재개 시 컨텍스트 업데이트
agentConversation.Add(new ChatMessage("user",
    "Continue. " + elapsedSeconds + " seconds have passed. You are currently " +
    currentActivity + ". Take a screenshot to see your surroundings and decide what to do next."));
```

#### 대화 트리밍 전략

```csharp
// Brain.cs - TrimConversation()
private const int ConversationTrimThreshold = 40;  // 40개 메시지 초과 시 트리밍
private const int ConversationTrimTarget = 24;       // 24개로 축소

private void TrimConversation()
{
    if (agentConversation == null || agentConversation.Count <= ConversationTrimThreshold)
        return;

    int keepFromEnd = ConversationTrimTarget - 2;
    int startIdx = agentConversation.Count - keepFromEnd;

    // 깔끔한 경계 찾기: tool_use/tool_result 없는 순수 assistant 메시지
    while (startIdx < agentConversation.Count - 2)
    {
        var msg = agentConversation[startIdx];
        if (msg.HasToolResult || msg.HasToolUse || msg.Role != "assistant")
        {
            startIdx++;
            continue;
        }
        break;
    }

    var trimmed = new List<ChatMessage>();
    trimmed.Add(agentConversation[0]); // system 프롬프트 (항상 보존)
    trimmed.Add(agentConversation[1]); // 첫 번째 user 메시지 (항상 보존)
    // 나머지: 최근 N개만 유지
    for (int i = startIdx; i < agentConversation.Count; i++)
        trimmed.Add(agentConversation[i]);

    agentConversation = trimmed;
}
```

핵심 설계 원칙:
- **system 프롬프트는 항상 보존** (인덱스 0)
- **첫 번째 user 메시지는 항상 보존** (인덱스 1) — 초기 상황 설명
- 중간 이력은 일정 임계값 초과 시 최근 N개로 슬라이딩 윈도우 적용
- 트리밍 경계는 tool_use/tool_result를 피해 대화 구조 무결성 유지

#### 대화 히스토리 기록

최대 50개 `HistoryEntry`를 유지하며, 각 항목에 게임 시간, LLM 응답 텍스트, thinking 텍스트, 스크린샷 썸네일, 도구 호출/결과, 토큰 사용량을 기록한다. 이 히스토리는 UI에서 실시간으로 열람 가능하며 디버깅과 관찰에 사용된다.

#### Extended Thinking 지원

각 프로바이더별 네이티브 추론 메커니즘을 지원한다:
- **Anthropic**: `interleaved-thinking` 베타 헤더로 추론 토큰 예산 설정 (0~8192)
- **OpenAI**: Responses API의 `reasoning.summary`
- **Google**: `thinkingConfig`

### 1.6 Dormammu 관점의 시사점

| 측면 | RimBot의 접근 | Dormammu 적용 가능성 |
|------|--------------|----------------|
| **월드 인지** | 스크린샷(시각) + 도구 조합 | 시뮬레이션 렌더링 이미지를 에이전트 입력으로 사용 |
| **상태 표현** | 이미지 + 상대 좌표 | 텍스트 상태 덤프 대신 렌더링 이미지 활용 고려 |
| **컨텍스트 관리** | 슬라이딩 윈도우 + system/초기메시지 고정 | 동일 패턴 직접 적용 가능 |
| **멀티 에이전트** | 콜로니스트별 독립 Brain | Dormammu의 캐릭터별 독립 에이전트 아키텍처와 일치 |
| **스레딩** | 백그라운드 LLM + 메인스레드 도구 실행 | 시뮬레이션 루프와 LLM 호출 분리 패턴 참조 |
| **도구 설계** | JSON Schema 기반 21개 도구 | Dormammu 시나리오 도구 설계의 레퍼런스 |
| **쿨다운** | 30초 에이전트 쿨다운 | 시뮬레이션 스텝과 LLM 호출 빈도 조율에 참조 |

**가장 직접적인 인사이트**: RimBot이 증명한 것은 **게임 엔진의 시각 출력(이미지)을 LLM의 직접 입력으로 사용하는 것이 실용적으로 작동한다**는 사실이다. 텍스트 상태 직렬화의 복잡성을 우회하면서 공간 정보를 자연스럽게 전달한다. Dormammu의 시뮬레이션 렌더러가 있다면 동일한 접근이 유효하다.

---

## 2. AI Dungeon 분석

**회사**: Latitude (https://latitude.io/)
**론칭**: 2019년 3월 (Nick Walton, BYU 딥러닝 연구실)
**기술 진화**: GPT-2 → GPT-2 1.5B → GPT-3 Dragon → 자체 모델

### 2.1 프로젝트 개요

AI Dungeon은 플레이어의 자유 텍스트 입력에 반응하여 절차적으로 동적인 스토리를 생성하는 텍스트 어드벤처 게임이다. LLM의 상업적 활용을 개척한 최초의 제품 중 하나로, 현재까지 수백만 명의 사용자를 보유하고 있다. Latitude가 운영하며 subscription 기반 서비스다.

핵심 기술 문제: **LLM의 제한된 컨텍스트 윈도우** 내에서 어떻게 일관된 장기 내러티브를 유지하는가.

### 2.2 내러티브 생성 메커니즘

AI Dungeon의 내러티브 생성은 순수한 LLM 자유 생성이 아니라, **구조화된 컨텍스트 조립** 위에서 이루어진다. 플레이어의 액션을 받으면 시스템이 여러 소스에서 컨텍스트를 조립하여 LLM에 전달한다.

#### 초기 모델 한계

GPT-2의 1024 토큰 컨텍스트 윈도우는 스토리가 길어질수록 초기 사건을 잘라냈다. 초기 완화책은 최근 8개 입력-응답 쌍만 유지하는 것이었으나, 장기 어드벤처에서 내러티브 드리프트가 발생했다.

### 2.3 월드 스테이트 관리

#### World Info / Story Cards 시스템

AI Dungeon은 플레이어가 명시적으로 정의하거나 시스템이 자동 생성하는 "Story Cards"를 통해 월드 스테이트를 관리한다. 각 카드는 **트리거 키워드**를 가지며, 최근 액션에서 해당 키워드가 등장할 때 컨텍스트에 동적으로 포함된다:

- 최소 평가 윈도우: 4개 액션
- 500토큰 이상 여유 시: 9개 액션으로 확장 (여유 토큰/100)
- 가장 최근에, 그리고 자주 트리거된 카드 우선 포함

이 방식은 **관련성 기반 선택적 로딩(relevance-based selective loading)** 이다. 모든 월드 정보를 한 번에 넣지 않고, 현재 스토리 흐름과 관련 있는 것만 꺼내 넣는다.

#### Plot Essentials (핵심 설정)

플레이어가 수동으로 지정하는 항구적 정보. 캐릭터의 클래스, 스킬, 인벤토리, 현재 퀘스트 등 AI가 절대 잊으면 안 되는 정보를 저장한다. 컨텍스트 조립 시 최우선 순위로 항상 포함된다.

### 2.4 컨텍스트 구성 아키텍처

AI Dungeon의 컨텍스트는 명확한 우선순위 규칙에 따라 여러 컴포넌트로 조립된다.

**소스**: https://help.aidungeon.com/faq/what-goes-into-the-context-sent-to-the-ai

#### 컴포넌트 분류

**필수 요소** (항상 포함, 70% 임계값 내에서 우선 보장):
- Instructions (시스템 프롬프트)
- Plot Essentials (핵심 설정)
- Story Summary (전체 요약)
- Author's Note (작가 주석)
- Front Memory (스크립트용)
- Last Action (현재 액션, 항상 전체 포함)

**동적 요소** (나머지 토큰을 비율로 배분):
- Story Cards: 나머지의 ~25%
- Memory Bank: 나머지의 ~25%
- Story History: 나머지의 ~50% (Memory Bank 비활성화 시 ~75%)

#### 컨텍스트 조립 순서

```
1. Instructions          ← 시스템 프롬프트
2. Plot Essentials       ← 항구적 핵심 설정
3. Story Cards           ← 관련성 기반 동적 로딩
4. Story Summary         ← 전체 스토리 압축 요약
5. Memory Bank           ← RAG 기반 관련 기억 검색
6. History               ← 최근 스토리 이력
7. Author's Note         ← 작가 스타일 지침
8. Last Action           ← 현재 플레이어 액션
9. Front Memory          ← 스크립트 주입 포인트
```

이 순서는 **일반 → 구체** 방향으로 진행하며, 가장 중요한 컨텍스트(시스템 설정)가 앞에, 현재 액션이 마지막에 위치한다.

### 2.5 메모리 시스템

**소스**: https://help.aidungeon.com/faq/the-memory-system

AI Dungeon의 메모리 시스템은 두 레이어로 구성된다.

#### 레이어 1: Auto Summarization (자동 요약)

- **트리거**: 매 6개 액션마다 직전 6개 액션+응답을 1개 Memory로 압축
- **타임라인**: 12번째 액션 → 액션 1-6이 첫 Memory, 18번째 액션 → 액션 7-12가 두 번째 Memory
- **Story Summary**: 매 15개 액션마다 전체 스토리에 대한 고수준 요약 생성, 너무 길어지면 자동 재압축
- **목적**: 최근 액션은 비압축으로 유지(편집 유연성 확보), 오래된 액션은 정보 밀도 높게 압축

#### 레이어 2: Memory Bank (RAG 기반 검색)

```
[새 액션 입력]
     ↓
[쿼리 벡터 생성 (embedding model)]
     ↓
[저장된 Memory 벡터들과 코사인 유사도 계산]
     ↓
[관련성 높은 Memory 선택]
     ↓
[컨텍스트에 포함]
```

- 각 Memory를 수학적 벡터로 변환하여 저장
- 새 액션 시 쿼리 벡터 생성 후 관련성 점수 계산
- 가장 관련성 높은 Memory들을 컨텍스트 토큰의 ~25%로 주입
- 용량 초과 시 가장 덜 사용된 Memory는 "Forgotten Memories"로 제거

**티어별 Memory Bank 용량:**
| 티어 | 용량 |
|------|------|
| Free | 25 memories |
| Champion | 100 memories |
| Legend | 200 memories |
| Mythic | 400 memories |

### 2.6 일관성 유지 솔루션 — SCORE 프레임워크

**논문**: SCORE: Story Coherence and Retrieval Enhancement for AI Narratives
**arXiv**: https://arxiv.org/abs/2503.23512
**저자**: Qiang Yi (UC Berkeley), Yangfan He (U Minnesota), Jianhui Wang (UESTC) 외 (학술 연구, Latitude 소속 아님)

SCORE는 AI 내러티브의 일관성 문제를 해결하는 RAG 기반 프레임워크다. AI Dungeon에 직접 탑재된 것이 아니라 독립적인 학술 연구지만, AI Dungeon 같은 시스템의 문제를 정면으로 다루며 Dormammu에 매우 관련성 높은 기술적 접근을 제시한다.

#### 세 가지 핵심 컴포넌트

**1. Dynamic State Tracking (동적 상태 추적)**

심볼릭 로직으로 내러티브 요소의 상태를 추적한다:

```
아이템 상태: { active, lost, destroyed }

불가능한 상태 전이 감지:
Si(tk) = active AND Si(tk-1) ∈ {lost, destroyed}
→ 연속성 오류로 플래그
```

한 번 파괴된 아이템이 다시 나타나는 것, 이미 죽은 캐릭터가 등장하는 것 등의 연속성 오류를 자동 감지한다.

**2. Context-Aware Summarization (컨텍스트 인식 요약)**

에피소드별 계층적 요약 생성:
- 캐릭터 액션 `Ac(t)`
- 핵심 아이템 인터랙션 `Ii(t)`
- 플롯 포인트
- 감정적 진행

이 요약들이 이후 검색의 인덱스가 된다.

**3. Hybrid Retrieval (하이브리드 검색)**

두 가지 유사도를 결합:
- **TF-IDF**: 키워드 매칭 (표면적 관련성)
- **코사인 유사도 (FAISS)**: 시맨틱 임베딩 (의미론적 관련성)
- **감정 분석**: 감정 점수 `σ(e)` (0~1), 큰 감정 불일치 방지

#### 정량적 성능

GPT-4 + SCORE vs 베이스라인 GPT 모델 비교:

| 지표 | 개선 |
|------|------|
| 내러티브 일관성 (NCI-2.0) | +23.6% |
| 감정적 일관성 (EASM) | 89.7% |
| 환각 감소 | -41.8% |
| Consistency | 85.61% (↑2.4) |
| Coherence | 86.9% (↑2.58) |
| Item Status 정확도 | 98% |
| Complex QA | 89.45% (↑7.11) |

#### SCORE 파이프라인

```
[에피소드 입력]
      ↓
1. Extract    핵심 아이템 상태 + 캐릭터 액션 추출
      ↓
2. Summarize  에피소드 계층적 요약 생성
      ↓
3. Embed      요약을 FAISS 벡터 공간에 임베딩
      ↓
4. Retrieve   코사인 유사도 + 감정 정렬로 관련 에피소드 검색
      ↓
5. Validate   검색된 컨텍스트 대비 현재 에피소드 일관성 검증
      ↓
6. Generate   캐릭터 아크, 플롯 로직, 감정적 일관성을 반영한 출력 생성
```

### 2.7 실패 패턴과 교훈

AI Dungeon의 역사에서 추출한 핵심 실패 패턴과 해결책:

#### 실패 1: "AI가 모든 것을 잊는다"

**원인**: 컨텍스트 윈도우 초과로 초기 설정 정보 제거
**증상**: 캐릭터가 이전 결정을 잊음, 이미 죽은 NPC 재등장, 설정 불일치
**해결**: 계층적 압축(요약) + RAG(Memory Bank)의 이중 접근

핵심 교훈: **단순 컨텍스트 잘라내기는 작동하지 않는다.** 압축(요약)과 선택적 검색(RAG)을 결합해야 한다.

#### 실패 2: 선택이 의미를 잃는다

**원인**: 플레이어의 과거 선택이 컨텍스트에서 사라지면 이후 스토리에 영향 없음
**증상**: "당신의 선택이 중요합니다"라는 약속이 무너짐
**해결**: Plot Essentials로 핵심 선택을 수동/자동으로 고정

핵심 교훈: **일부 정보는 절대 잘라내면 안 된다.** 필수 요소와 동적 요소를 분리하는 컨텍스트 아키텍처가 필요하다.

#### 실패 3: 내러티브 드리프트

**원인**: LLM이 매 응답마다 새로운 방향으로 이야기를 틀어버림
**증상**: 장르 변경, 캐릭터 성격 변화, 설정 모순
**해결**: Author's Note(작가 주석)로 스타일과 방향 상시 주입, SCORE의 Dynamic State Tracking

핵심 교훈: **스타일과 방향 지침은 매 호출마다 지속적으로 주입**되어야 한다. 한 번 초기 프롬프트에만 넣으면 희석된다.

#### 실패 4: 토큰 비용 vs. 컨텍스트 품질 트레이드오프

**원인**: 더 긴 컨텍스트 = 더 높은 비용
**해결**: 티어별 Memory Bank 용량 차등화 (25~400 memories), 동적 요소의 토큰 배분 비율 조정

핵심 교훈: **컨텍스트 품질은 비용과 직결된다.** 무료 vs. 유료 사용자 경험 차이를 컨텍스트 용량으로 차별화하는 것이 가능하다.

---

## 3. Dormammu 적용 시사점 종합

RimBot과 AI Dungeon을 Dormammu의 맥락에서 비교하면 다음과 같은 패턴이 수렴한다.

### 3.1 월드 스테이트 표현 전략

| 접근 | RimBot | AI Dungeon | Dormammu 적용 |
|------|--------|-----------|---------|
| 시각 정보 | 스크린샷 (이미지) | 텍스트 서술 | 시뮬레이션 렌더링 이미지 |
| 구조화 데이터 | 도구 쿼리 결과 (JSON) | Story Cards, Plot Essentials | 시나리오 상태 스냅샷 |
| 자연어 요약 | 시스템 프롬프트에 포함 | Auto Summarization | 에피소드 자동 압축 |

**Dormammu 권장**: 텍스트 상태 직렬화 + RAG 기반 이력 검색의 조합. 시각 렌더러가 있다면 RimBot 방식 적용.

### 3.2 컨텍스트 관리 아키텍처 (즉시 적용 가능)

AI Dungeon의 컨텍스트 구조를 Dormammu에 직접 매핑:

```
[Dormammu 컨텍스트 조립 제안]

필수 요소 (항상 포함):
  - 시나리오 기본 설정 (세계관, 룰)
  - 캐릭터 핵심 속성 (이름, 특성, 현재 목표)
  - 현재 시뮬레이션 스텝

동적 요소:
  - 관련 월드 카드 (트리거 기반, ~25% 토큰)
  - Memory Bank 검색 결과 (RAG, ~25% 토큰)
  - 최근 이벤트 이력 (~50% 토큰)
```

### 3.3 메모리 레이어 설계

```
레이어 1: 구조화 상태 (항상 포함)
  → 캐릭터 속성, 현재 퀘스트, 핵심 설정
  → AI Dungeon의 Plot Essentials 개념

레이어 2: 압축 이력 (Auto Summarization)
  → N 스텝마다 이전 이력을 자동 압축
  → 최근 스텝은 비압축, 오래된 스텝은 고밀도 압축

레이어 3: 검색 가능 기억 (Memory Bank / RAG)
  → 이벤트를 벡터화하여 저장
  → 현재 상황과 관련성 높은 기억을 동적 검색
  → FAISS + 코사인 유사도 (SCORE 방식 참조)
```

### 3.4 일관성 보장 메커니즘

SCORE가 제시하는 구체적 기법들은 Dormammu의 시뮬레이션 품질 측정에 직접 사용 가능:

1. **상태 전이 검증**: 불가능한 상태 변화(죽은 캐릭터 부활 등)를 자동 감지
2. **에피소드 요약 인덱싱**: 매 N 스텝마다 요약 생성 및 벡터 인덱스 추가
3. **하이브리드 검색**: 키워드 + 시맨틱 임베딩 조합으로 관련 이력 검색
4. **감정/톤 일관성**: 이전 에피소드와 현재 응답의 감정 벡터 비교

### 3.5 핵심 설계 원칙 요약

1. **필수/동적 분리**: 절대 잊으면 안 되는 정보와 동적으로 선택하는 정보를 명확히 분리
2. **계층적 압축**: 시간이 지날수록 더 압축 (최근 = 상세, 오래된 = 요약)
3. **RAG로 관련성 보장**: 모든 이력을 컨텍스트에 우겨넣지 않고, 현재 상황에 관련 있는 것만 검색
4. **상태 추적 레이어**: LLM 외부에서 심볼릭하게 상태를 추적하여 일관성 검증
5. **비용-품질 트레이드오프 관리**: 토큰 배분 비율로 우선순위 조정

---

## 참고 자료

| 자료 | URL |
|------|-----|
| RimBot GitHub | https://github.com/kolbytn/RimBot |
| AI Dungeon 공식 | https://aidungeon.com |
| Latitude 블로그 | https://latitude.io/ |
| AI Dungeon 컨텍스트 구성 FAQ | https://help.aidungeon.com/faq/what-goes-into-the-context-sent-to-the-ai |
| AI Dungeon 메모리 시스템 FAQ | https://help.aidungeon.com/faq/the-memory-system |
| AI Dungeon 망각 원인 FAQ | https://help.aidungeon.com/faq/why-does-the-ai-forget-or-mix-things-up |
| SCORE 논문 (arXiv) | https://arxiv.org/abs/2503.23512 |
| Wikipedia: AI Dungeon | https://en.wikipedia.org/wiki/AI_Dungeon |
