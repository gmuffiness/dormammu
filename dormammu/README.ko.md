<p align="right">
  <a href="./README.md">English</a> | <strong>한국어</strong>
</p>

<p align="center">
  <br/>
  <strong>D O R M A M M U</strong>
  <br/><br/>
  <sub>거래하러 왔다... 현실과.</sub>
</p>

# Dormammu — What-If 소설 시뮬레이션 하네스

> **"만약 ~했다면?"** 이라는 질문 하나로 시작하여, DFS 시나리오 트리를 탐색하며 What-If 소설을 생성합니다.

Dormammu는 Python CLI 도구가 아닙니다. **Claude Code / Codex 같은 에이전트 세션 안에서 동작하는 하네스**입니다.

## 작동 방식

```
"진격의 거인에서 아르민 대신 엘빈을 살렸다면?"
  ↓
Phase 1: 배경 리서치 → 01-background-research.md
Phase 2: 세계관 규칙 → 02-world-rules.md
Phase 3: 캐릭터 생성 → characters/*.md (OOC 탐지 규칙 포함)
Phase 4: 시나리오 트리 초기화
Phase 5: DFS 탐색 → N001/N002/node.md ... (expand/prune)
Phase 6: 최우수 경로 소설화 → 05-deepen-best-path.md
Phase 7: 메타데이터 리포트 → 07-best-path-metadata.md
```

## 빠른 시작

Claude Code 세션에서:

```
/dormammu:imagine                    # 시나리오 설정 (대화형)
/dormammu:simulate "주제"            # 시뮬레이션 실행
/dormammu:status                     # 진행 상황 확인
/dormammu:deepen                     # 최우수 경로 소설화
/dormammu:help                       # 전체 가이드
```

결과 뷰어:
```bash
python viewer/serve.py .dormammu/output/<sim-id>
# → http://localhost:3000
```

## 설계 원칙

1. **에이전트 네이티브** — API 키 없이, 에이전트 세션 안에서 스킬+서브에이전트로 완결
2. **프롬프트가 코드** — 시뮬레이션 로직이 마크다운 프롬프트 파일에 정의됨
3. **상태는 파일** — DB 대신 tree-index.json + node.md + run-state.json
4. **산출물은 문서** — 사람이 직접 읽을 수 있는 마크다운 트리

## 라이선스

MIT
