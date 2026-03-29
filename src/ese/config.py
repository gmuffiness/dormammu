"""Configuration management for Dormammu.

Loads settings from environment variables and/or a .env file.
All configuration is centralized here so the rest of the codebase
imports from a single source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Load .env from project root (two levels up from this file: src/ese/ -> root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Config(BaseSettings):
    """Dormammu runtime configuration.

    Values are resolved in order:
    1. Explicit environment variables
    2. .env file in the project root
    3. Defaults defined here
    """

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model to use")
    agent_model: str = Field(default="gpt-4o-mini", description="OpenAI model for agent interactions (cheaper model for agent decisions)")

    # Language
    language: str = Field(default="en", description="Simulation output language (e.g. 'en', 'ko', 'ja')")

    # Simulation parameters
    max_depth: int = Field(default=5, ge=1, description="Maximum DFS tree depth")
    node_years: int = Field(
        default=100, ge=1, description="Simulated years per leaf node"
    )
    cost_limit: float = Field(
        default=10.0, ge=0.0, description="Maximum USD spend per simulation run"
    )

    # Token tracking
    track_tokens: bool = Field(default=True, description="Track token usage per node and total")

    # LLM Backend
    llm_backend: str = Field(default="openai", description="LLM backend: 'openai' or 'claude-code'")
    claude_model: str = Field(default="claude-sonnet-4-20250514", description="Claude model to use when llm_backend is 'claude-code'")

    # Storage
    data_dir: Path = Field(
        default=_PROJECT_ROOT / "data" / "simulations",
        description="Directory where simulation data is stored",
    )
    db_path: Path = Field(
        default=_PROJECT_ROOT / "data" / "simulations" / "ese.db",
        description="SQLite database path",
    )

    @field_validator("openai_api_key")
    @classmethod
    def _require_api_key(cls, v: str) -> str:
        if not v:
            import warnings

            warnings.warn(
                "OPENAI_API_KEY is not set. LLM calls will fail.",
                stacklevel=2,
            )
        return v

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
        "populate_by_name": True,
    }


# Module-level singleton — import this in other modules
config = Config()


from pydantic import BaseModel


class SourceInfo(BaseModel):
    """원작 정보."""
    title: str
    media_type: str = "unknown"  # manga, novel, anime, game, movie, etc.


class TimeRange(BaseModel):
    """시뮬레이션 시간 범위."""
    value: int = 10
    unit: str = "years"
    label: str = "중기"


class EvaluationWeights(BaseModel):
    """6차원 평가 메트릭 가중치."""
    character_fidelity: float = 0.20
    fandom_resonance: float = 0.15
    emergence: float = 0.15
    diversity: float = 0.15
    plausibility: float = 0.15
    foreshadowing: float = 0.20


class WhatIfScenario(BaseModel):
    """What-If 소설 시나리오 설정.

    /ese:imagine에서 수집한 7가지 입력을 구조화한 모델.
    .ese/scenario.json으로 직렬화/역직렬화됩니다.
    """
    # 필수 입력
    topic: str
    """대주제 — What-If 질문"""
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

    # 분석 결과
    source: SourceInfo = SourceInfo(title="unknown")
    """원작 정보"""
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
        """Load scenario from .ese/scenario.json."""
        import json
        p = path or _PROJECT_ROOT / ".ese" / "scenario.json"
        if not p.exists():
            return None
        return cls.model_validate_json(p.read_text())

    def save(self, path: Path | None = None) -> Path:
        """Save scenario to .ese/scenario.json."""
        from datetime import datetime, timezone
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        p = path or _PROJECT_ROOT / ".ese" / "scenario.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2))
        return p
