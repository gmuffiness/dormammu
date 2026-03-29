# Emergent Garden Reference — emergent-world / Dormammu를 위한 레퍼런스

> 공개적으로 확인 가능한 자료와 이 워크스페이스의 로컬 문서를 바탕으로,
> Emergent Garden가 emergent-world / Dormammu에 주는 시사점을 정리한 메모.

---

## 1. 이 문서의 목적

이 문서는 **Emergent Garden 자체의 완전한 소개서**라기보다,
현재 확인 가능한 범위 안에서 다음을 정리하기 위한 레퍼런스다.

- Emergent Garden라는 이름이 어떤 맥락에서 등장하는가
- MINDcraft와 어떤 식으로 연결되는가
- emergent-world / Dormammu 관점에서 무엇을 배울 수 있는가

즉, **"정확히 확인되는 사실"**과 **"그로부터 끌어낼 수 있는 설계 시사점"**을 분리해서 본다.

---

## 2. 현재 공개 자료에서 확인되는 핵심

### 2.1 MINDcraft와 강하게 연결되어 있다

현재 공개 자료에서 Emergent Garden라는 이름은 가장 분명하게 **MINDcraft / MineCollab** 맥락에서 등장한다.

- MINDcraft GitHub는 이 프로젝트를 **"Minecraft AI with LLMs+Mineflayer"**라고 소개한다
- MINDcraft paper website는 MINDcraft를 **오픈월드 Minecraft에서 LLM 에이전트를 제어하기 위한 확장 가능한 플랫폼**으로 설명한다
- 같은 paper website에서 **Max Robinson의 소속(affiliation)이 Emergent Garden**으로 표기된다

즉, 현재 외부 자료 기준으로 Emergent Garden는
**MINDcraft 생태계와 연결된 창작/연구 주체 이름**으로 이해하는 것이 가장 안전하다.

### 2.2 핵심 관심사는 "embodied multi-agent world"에 가깝다

MINDcraft 관련 공개 자료를 보면 초점은 단순 챗봇이 아니라,
에이전트가 **게임 세계 안에서 몸을 가진 채 행동하고 협업하는 문제**에 맞춰져 있다.

- 자원 수집, 제작, 건설 같은 실제 게임 내 과업 수행
- 단일 에이전트가 아니라 여러 에이전트의 **협업**
- 자연어 기반 계획/커뮤니케이션이 성능 병목이 되는 문제

이는 emergent-world가 관심을 가지는
**"살아 있는 세계 + 자율 에이전트 + 관찰 가능한 행동"**과 상당히 맞닿아 있다.

### 2.3 "연구"와 "창작"의 경계에 있는 프로젝트로 보인다

공개적으로 확인되는 결과물은 GitHub 오픈소스, 논문 웹사이트, 데모/영상 맥락에 걸쳐 있다.
따라서 Emergent Garden는 전통적인 제품 회사라기보다,
**창작 실험 + 연구 프로토타입 + 공개 콘텐츠**가 맞물린 형태로 이해하는 편이 적절하다.

> 이 문장은 공개 산출물의 성격을 보고 내린 **해석**이며,
> 법인/조직 형태 자체를 단정하는 뜻은 아니다.

---

## 3. emergent-world / Dormammu 관점에서 왜 중요한가

### 3.1 "살아 있는 세계"를 말로만 다루지 않는다

MINDcraft는 세계를 텍스트로만 상상하지 않고,
**Minecraft라는 실제 규칙과 제약이 있는 샌드박스 세계** 안에서 에이전트를 굴린다.

이 점이 중요한 이유:

- 행동이 추상적 설명이 아니라 **환경과 상호작용한 결과**가 된다
- 실패/지연/우회 경로가 자연스럽게 드러난다
- 에이전트의 "살아 있음"이 대화 품질이 아니라 **세계 안의 지속적 행위**로 평가된다

emergent-world / Dormammu에도 이런 관점은 유효하다.
세계는 단순한 배경이 아니라, 에이전트를 **검증 가능하게 만드는 마찰면**이어야 한다.

### 3.2 멀티 에이전트는 곧 커뮤니케이션 문제다

MINDcraft / MineCollab 논문 사이트는
현재 SOTA 에이전트들이 협업할 때 핵심 병목이 **효율적인 자연어 커뮤니케이션**이라고 설명한다.
상세한 계획을 서로 전달해야 할 때 성능이 최대 **15%까지 감소**했다고 한다.

이건 emergent-world에도 직접적인 시사점을 준다.

- 에이전트 수를 늘리는 것만으로 세계가 풍부해지지 않는다
- 사회적 상호작용은 **표현 비용**과 **조정 비용**을 함께 만든다
- "말을 많이 하는 에이전트"보다 **짧고 구조화된 협업 규칙**이 더 중요할 수 있다

### 3.3 관찰 가능한 복잡성은 환경 + 기억 + 목표의 결합에서 나온다

Mindcraft 계열 작업이 흥미로운 이유는,
에이전트가 단순 반응기가 아니라 **목표를 가지고 세계를 헤집고 다닌다**는 점이다.
이때 재미는 "답변"이 아니라 **과정**에서 나온다.

emergent-world / Dormammu가 배울 수 있는 포인트:

- 세계는 충분히 **조작 가능**해야 한다
- 에이전트는 장기 목표를 향해 움직여야 한다
- 로그/리플레이가 가능해야 관찰의 재미가 생긴다
- 개별 행동보다 **행동의 누적 궤적**이 중요하다

---

## 4. Emergent Garden에서 읽히는 창작 방향성

아래는 공개 자료와 로컬 메모를 바탕으로 정리한 **추론**이다.

### 4.1 핵심 매력은 "emergent complexity"

이 워크스페이스의 `docs/message-to-emergent-garden.md`는
Emergent Garden의 최근 영상에서 **"생태계가 스스로 성장하고 진화하는 게임"** 이야기가 인상적이었다고 적고 있다.
또한 단순한 규칙에서 살아 있는 복잡성이 생기는 지점을 핵심 매력으로 꼽는다.

이 로컬 문서까지 함께 보면, Emergent Garden는 단순히 "AI가 게임 잘하기"보다
**간단한 규칙/에이전트/환경 상호작용으로 살아 있는 세계가 생겨나는 현상**에 더 큰 흥미를 두는 것으로 읽힌다.

### 4.2 게임은 목표가 아니라 실험장일 가능성이 크다

공개된 대표 산출물인 MINDcraft를 보면,
Minecraft는 완성된 게임 제품이라기보다 **복잡한 세계를 빠르게 실험할 수 있는 샌드박스**로 기능한다.

이 관점은 emergent-world에도 중요하다.

- 처음부터 완성형 세계를 만들 필요는 없다
- 이미 충분히 복잡한 환경을 **실험장**으로 써도 된다
- 핵심은 비주얼보다 **행동, 상호작용, 누적성**이다

---

## 5. emergent-world / Dormammu에 적용할 수 있는 구체적 교훈

| Emergent Garden / MINDcraft에서 보이는 점 | emergent-world / Dormammu 적용 아이디어 |
|---|---|
| 실제 샌드박스 환경 안에서 에이전트를 굴림 | 텍스트 시뮬레이션이라도 환경 제약을 명시적으로 모델링 |
| 멀티 에이전트 협업이 주요 주제 | 사회적 상호작용 규칙, 통신 비용, 역할 분담 설계 |
| 행동 과정 자체가 중요한 관찰 대상 | 로그, 리플레이, timeline 뷰를 초기부터 중요 자산으로 취급 |
| 오픈소스/연구/콘텐츠가 연결된 형태 | Dormammu도 문서·데모·실험 결과를 함께 축적하는 구조 고려 |
| 긴 목표 수행에서 에이전트의 한계가 드러남 | 장기 목표를 작은 루프와 체크포인트로 쪼개는 설계 필요 |

---

## 6. 지금 단계에서 내릴 수 있는 실용적 결론

Emergent Garden를 emergent-world / Dormammu 관점에서 볼 때,
가장 중요한 건 "누가 정확히 어떤 조직을 운영하느냐"보다 아래 질문이다.

1. **에이전트가 세계 안에서 어떻게 살아 움직이게 되는가?**
2. **복잡성은 프롬프트가 아니라 환경과 상호작용에서 어떻게 솟아나는가?**
3. **멀티 에이전트 협업은 어디서 깨지고, 어떻게 보완할 수 있는가?**
4. **관찰 가치가 있는 세계를 만들려면 로그/리플레이/시각화는 어떤 역할을 해야 하는가?**

이 질문들에 대해 Emergent Garden / MINDcraft는
완성된 정답이라기보다 **매우 좋은 선행 실험**으로 볼 수 있다.

---

## 7. 현재 기준 한 줄 요약

> Emergent Garden는 공개적으로는 MINDcraft와 가장 강하게 연결되어 보이며,
> emergent-world / Dormammu 입장에서는 **embodied multi-agent living world 실험의 중요한 레퍼런스**다.

---

## 8. Sources

### External
- MINDcraft GitHub: https://github.com/kolbytn/mindcraft
- MINDcraft / MineCollab paper website: https://mindcraft-minecollab.github.io/

### Local workspace
- `docs/message-to-emergent-garden.md`
- `apps/emergent-world/docs/westworld-reference.md`
