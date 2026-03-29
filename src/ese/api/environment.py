"""Environment layout generation for Dormammu 2D visualization.

Generates a 2D map layout appropriate for the simulation topic using an LLM.
Results are cached in memory (keyed by simulation_id) so generation runs only once.
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# In-process cache: simulation_id -> environment dict
_cache: dict[str, dict[str, Any]] = {}

# Map type inference keywords
_MAP_TYPE_HINTS: list[tuple[list[str], str]] = [
    (["화성", "mars", "행성", "planet", "colony", "식민지"], "planet"),
    (["우주", "space", "station", "정거장", "궤도", "orbital"], "space_station"),
    (["도시", "city", "서울", "뉴욕", "tokyo", "urban", "metropolitan"], "city"),
    (["마을", "village", "village", "농촌", "rural", "town"], "village"),
    (["숲", "forest", "jungle", "정글", "wilderness", "야생"], "forest"),
    (["바다", "ocean", "sea", "island", "섬", "해양"], "island"),
    (["미래", "future", "2100", "2200", "2300", "dystopia", "utopia"], "city"),
]

_DEFAULT_GRID = 20


def _infer_map_type(topic: str) -> str:
    topic_lower = topic.lower()
    for keywords, map_type in _MAP_TYPE_HINTS:
        if any(kw in topic_lower for kw in keywords):
            return map_type
    return "city"


def _default_layout(
    simulation_id: str,
    topic: str,
    agent_ids: list[str],
    width: int = _DEFAULT_GRID,
    height: int = _DEFAULT_GRID,
) -> dict[str, Any]:
    """Fallback environment when no LLM is available."""
    map_type = _infer_map_type(topic)

    landmarks = [
        {"name": "Central Hub", "x": width // 2, "y": height // 2, "type": "hub", "description": "The central meeting point of the simulation."},
        {"name": "Archive", "x": 2, "y": 2, "type": "archive", "description": "Repository of historical records."},
        {"name": "Market", "x": width - 3, "y": 2, "type": "market", "description": "Trade and exchange hub."},
        {"name": "Council Hall", "x": 2, "y": height - 3, "type": "government", "description": "Seat of governance."},
        {"name": "Research Lab", "x": width - 3, "y": height - 3, "type": "research", "description": "Center for innovation."},
    ]

    zones = [
        {"name": "Residential", "bounds": {"x": 0, "y": 0, "width": width // 2, "height": height // 2}, "type": "residential"},
        {"name": "Commercial", "bounds": {"x": width // 2, "y": 0, "width": width // 2, "height": height // 2}, "type": "commercial"},
        {"name": "Industrial", "bounds": {"x": 0, "y": height // 2, "width": width // 2, "height": height // 2}, "type": "industrial"},
        {"name": "Nature Reserve", "bounds": {"x": width // 2, "y": height // 2, "width": width // 2, "height": height // 2}, "type": "nature"},
    ]

    # Distribute agents evenly around the center
    agent_positions = []
    n = len(agent_ids)
    for i, agent_id in enumerate(agent_ids):
        if n == 1:
            x, y = width // 2, height // 2
        else:
            angle = (2 * math.pi * i) / n
            radius = min(width, height) // 4
            x = int(width // 2 + radius * math.cos(angle))
            y = int(height // 2 + radius * math.sin(angle))
        agent_positions.append({"agent_id": agent_id, "x": x, "y": y})

    return {
        "simulation_id": simulation_id,
        "map_type": map_type,
        "width": width,
        "height": height,
        "landmarks": landmarks,
        "zones": zones,
        "initial_agent_positions": agent_positions,
    }


async def _llm_layout(
    simulation_id: str,
    topic: str,
    agent_ids: list[str],
    agent_names: list[str],
    world_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Call OpenAI to generate a context-aware environment layout."""
    try:
        from ese.config import config

        if not config.openai_api_key:
            return None

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=config.openai_api_key)

        width, height = 20, 20
        map_type = _infer_map_type(topic)
        agents_desc = ", ".join(agent_names) if agent_names else "unknown agents"

        prompt = f"""You are designing a 2D grid map ({width}x{height}) for a world simulation.

Simulation topic: {topic}
Agents: {agents_desc}
Map type hint: {map_type}

Return a JSON object (no markdown) with these exact fields:
{{
  "map_type": "<city|village|planet|space_station|forest|island|other>",
  "landmarks": [
    {{"name": "...", "x": <0-{width-1}>, "y": <0-{height-1}>, "type": "<hub|market|archive|government|research|nature|residential|industrial|other>", "description": "..."}}
  ],
  "zones": [
    {{"name": "...", "bounds": {{"x": int, "y": int, "width": int, "height": int}}, "type": "<residential|commercial|industrial|nature|government|research|other>"}}
  ],
  "initial_agent_positions": [
    {{"agent_id": "<id>", "x": int, "y": int}}
  ]
}}

Rules:
- Include 4-8 landmarks with meaningful names for the topic.
- Include 3-5 zones that partition the map.
- Place agents at distinct starting positions relevant to the scenario.
- Agent IDs must be exactly: {json.dumps(agent_ids)}
- All coordinates must be within 0-{width-1} (x) and 0-{height-1} (y).
- Zones must fit within the {width}x{height} grid."""

        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )

        raw = response.choices[0].message.content or ""
        data = json.loads(raw)

        return {
            "simulation_id": simulation_id,
            "map_type": data.get("map_type", map_type),
            "width": width,
            "height": height,
            "landmarks": data.get("landmarks", []),
            "zones": data.get("zones", []),
            "initial_agent_positions": data.get("initial_agent_positions", []),
        }

    except Exception as exc:
        logger.warning("LLM environment generation failed: %s", exc)
        return None


async def generate_environment(
    simulation_id: str,
    topic: str,
    agents: list[dict[str, Any]],
    world_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Generate (or return cached) 2D environment layout for a simulation.

    Args:
        simulation_id: The simulation ID (used as cache key).
        topic: Free-form simulation topic string.
        agents: List of agent dicts with at least 'agent_id' and optionally 'persona'.
        world_state: World state at turn 0 (may be None).

    Returns:
        Environment dict compatible with EnvironmentResponse.
    """
    if simulation_id in _cache:
        return _cache[simulation_id]

    agent_ids = [a.get("agent_id", "") for a in agents]
    agent_names = [
        (a.get("persona") or {}).get("name", a.get("agent_id", ""))
        for a in agents
    ]

    result = await _llm_layout(simulation_id, topic, agent_ids, agent_names, world_state)
    if result is None:
        result = _default_layout(simulation_id, topic, agent_ids)

    _cache[simulation_id] = result
    return result
