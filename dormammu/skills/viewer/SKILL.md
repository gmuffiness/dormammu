---
name: viewer
description: "Dormammu Viewer — 시뮬레이션 결과 뷰어"
---

# Dormammu Viewer

시뮬레이션 결과 뷰어를 로컬에서 엽니다.

## 실행 절차

1. 이미 3000번 포트에서 서버가 실행 중인지 확인한다.
   - 실행 중이면 브라우저만 연다.
   - 실행 중이 아니면 서버를 백그라운드로 시작한다.
2. 인자가 있으면 해당 시뮬레이션 페이지를, 없으면 홈 페이지를 연다.

## 명령어

```bash
# 포트 확인 & 서버 시작
if lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "이미 포트 3000에서 서버 실행 중"
else
  python viewer/serve.py .dormammu/output &
  sleep 1
  echo "뷰어 서버 시작됨"
fi

# 브라우저 열기
if [ -n "$ARGUMENTS" ]; then
  open "http://localhost:3000/sim/$ARGUMENTS"
else
  open http://localhost:3000/
fi
```

## 인자

- `$ARGUMENTS`: 특정 시뮬레이션 ID (예: `f47eff22`)
  - 지정 시 `http://localhost:3000/sim/<sim-id>` 페이지를 연다
  - 미지정 시 홈 페이지(전체 시뮬레이션 목록)를 연다

## URL 구조

- `http://localhost:3000/` — 홈 (모든 시뮬레이션 목록)
- `http://localhost:3000/sim/<sim-id>` — 특정 시뮬레이션 대시보드
