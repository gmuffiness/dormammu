# Dormammu Viewer

시뮬레이션 결과를 브라우저에서 탐색하는 간단한 뷰어입니다.

## 방법 A — Python 서버 (추천)

```bash
# 프로젝트 루트에서
python viewer/serve.py .dormammu/output/<sim-id>
# 브라우저에서 http://localhost:3000 열기
```

## 방법 B — 파일 드롭

`viewer/index.html`을 브라우저에서 직접 열고, 우측 상단 **파일 드롭** 버튼을 눌러 `tree-index.json`과 `node.md` 파일들을 드롭하세요.
