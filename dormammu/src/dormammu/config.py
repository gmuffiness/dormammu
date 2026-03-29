"""Configuration and data models for Dormammu.

Loads settings from environment variables and/or a .env file.
Data models (WhatIfScenario, Persona schema, etc.) are used by
Claude Code skills to structure simulation data.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Load .env from project root (two levels up from this file: src/dormammu/ -> root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Config(BaseSettings):
    """Dormammu runtime configuration."""

    # Language
    language: str = Field(default="ko", description="Simulation output language (e.g. 'en', 'ko', 'ja')")

    # Output
    output_dir: Path = Field(
        default=_PROJECT_ROOT / ".dormammu" / "output",
        description="Directory for markdown output artifacts",
    )

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
        "populate_by_name": True,
    }


# Module-level singleton
config = Config()


class SourceInfo(BaseModel):
    """출처 정보. 픽션은 원작, 역사는 사건/인물, 사변은 사고실험의 배경."""
    title: str
    media_type: str = "unknown"  # manga, novel, anime, game, movie, historical_event, biography, business_case, thought_experiment, etc.


class TimeRange(BaseModel):
    """시뮬레이션 시간 범위."""
    value: int = 10
    unit: str = "years"
    label: str = "중기"


class ImageGenConfig(BaseModel):
    """이미지 생성 설정."""
    enabled: bool = False
    """이미지 생성 활성화 여부"""
    provider: str = "gemini"
    """이미지 생성 제공자 — gemini | openai | skip"""
    model: str = "gemini-3.1-flash-image-preview"
    """이미지 생성 모델"""
    quality: str = "standard"
    """품질 — standard | high"""


class EvaluationWeights(BaseModel):
    """6차원 평가 메트릭 가중치."""
    character_fidelity: float = 0.20
    audience_resonance: float = 0.15
    emergence: float = 0.15
    narrative_flow: float = 0.15
    plausibility: float = 0.15
    foreshadowing: float = 0.20


class WhatIfScenario(BaseModel):
    """What-If 소설 시나리오 설정.

    /dormammu:imagine에서 수집한 8가지 입력을 구조화한 모델.
    .dormammu/scenario.json으로 직렬화/역직렬화됩니다.
    """
    # 필수 입력
    topic: str
    """대주제 — What-If 질문"""
    topic_type: str = "fiction"
    """토픽 유형 — fiction | history | speculative"""
    protagonists: list[str] = []
    """주인공 지정 — 시점 중심 캐릭터 목록"""

    # 선택 입력
    tone: str = "original"
    """톤/분위기 — original | dark | light | realistic"""
    time_range: TimeRange = TimeRange()
    """시간 범위"""
    constraints: list[str] = []
    """고정 조건/제약"""
    curiosity_points: list[str] = []
    """궁금한 포인트 — 우선 탐색 대상"""
    exploration_style: str = "balance"
    """탐색 스타일 — wide | deep | balance"""
    image_generation: ImageGenConfig = ImageGenConfig()
    """이미지 생성 설정 — deepen 시 사용"""

    # 분석 결과
    source: SourceInfo = SourceInfo(title="unknown")
    """출처 정보"""
    scale: str = "micro"
    """스케일 — macro | micro"""
    world_rules: list[str] = []
    """세계관 규칙"""
    evaluation_weights: EvaluationWeights = EvaluationWeights()
    """평가 메트릭 가중치"""

    created_at: str = ""
    """생성 시간 (ISO format)"""

    def get_exploration_params(self) -> dict:
        """탐색 스타일에 따른 DFS 파라미터 반환."""
        params = {
            "wide": {"max_depth": 3, "branches_per_node": 5},
            "deep": {"max_depth": 6, "branches_per_node": 2},
            "balance": {"max_depth": 4, "branches_per_node": 3},
        }
        return params.get(self.exploration_style, params["balance"])

    @classmethod
    def load(cls, path: Path | None = None) -> "WhatIfScenario | None":
        """Load scenario from .dormammu/scenario.json."""
        p = path or _PROJECT_ROOT / ".dormammu" / "scenario.json"
        if not p.exists():
            return None
        return cls.model_validate_json(p.read_text())

    def save(self, path: Path | None = None) -> Path:
        """Save scenario to .dormammu/scenario.json."""
        from datetime import datetime, timezone
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        p = path or _PROJECT_ROOT / ".dormammu" / "scenario.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2))
        return p
