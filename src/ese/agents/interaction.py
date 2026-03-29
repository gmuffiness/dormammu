"""Agent interaction via OpenAI for Dormammu.

This module handles the actual OpenAI API calls that drive agent decision-making
and agent-to-agent dialogue. All LLM calls are routed through here so that
token counting, cost tracking, and rate limiting are centralized.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Parsed response from an OpenAI API call."""

    content: str
    tokens_prompt: int
    tokens_completion: int
    model: str

    @property
    def tokens_total(self) -> int:
        return self.tokens_prompt + self.tokens_completion

    def cost_usd(self, model: str = "gpt-4o") -> float:
        """Estimate cost in USD based on token counts.

        Pricing (as of 2024): gpt-4o $0.005/1k input, $0.015/1k output.
        """
        rates = {
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-2024-08-06": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4-turbo": (0.01, 0.03),
        }
        in_rate, out_rate = rates.get(model, (0.005, 0.015))
        return (self.tokens_prompt / 1000) * in_rate + (self.tokens_completion / 1000) * out_rate


class AgentInteraction:
    """Manages OpenAI API calls for agent decisions and dialogues.

    Usage
    -----
    interaction = AgentInteraction(api_key="sk-...", model="gpt-4o")
    response = await interaction.get_action(system_prompt, user_prompt)
    """

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self.api_key = api_key
        self.model = model
        self._client: Any = None  # openai.AsyncOpenAI, lazily initialized

    def _get_client(self) -> Any:
        """Lazily initialize the OpenAI async client."""
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def get_action(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """Ask the LLM to decide an agent's action.

        Args:
            system_prompt: Sets the agent persona and world context.
            user_prompt: The specific turn query.
            temperature: Sampling temperature (higher = more creative).

        Returns:
            An LLMResponse with the raw content and token usage.

        Raises:
            openai.RateLimitError: After one retry with backoff.
            openai.OpenAIError: On other API failures (logged then re-raised).
        """
        import openai

        client = self._get_client()
        logger.debug(
            "get_action: model=%s system_len=%d user_len=%d",
            self.model,
            len(system_prompt),
            len(user_prompt),
        )
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                choice = response.choices[0]
                usage = response.usage
                return LLMResponse(
                    content=choice.message.content or "",
                    tokens_prompt=usage.prompt_tokens,
                    tokens_completion=usage.completion_tokens,
                    model=self.model,
                )
            except openai.RateLimitError:
                if attempt == 0:
                    logger.warning("Rate limit hit; retrying after 5 s.")
                    await asyncio.sleep(5)
                else:
                    logger.error("Rate limit persists after retry.")
                    raise
            except openai.OpenAIError as exc:
                logger.error("OpenAI API error in get_action: %s", exc)
                raise
        # unreachable, but satisfies type checker
        raise RuntimeError("get_action: exhausted retries")

    async def dialogue(
        self,
        agent_a_persona: str,
        agent_b_persona: str,
        context: str,
        topic: str,
        turns: int = 3,
    ) -> list[dict[str, str]]:
        """Simulate a multi-turn dialogue between two agents.

        Args:
            agent_a_persona: System prompt block for agent A.
            agent_b_persona: System prompt block for agent B.
            context: World state summary for grounding.
            topic: What the agents are discussing/doing together.
            turns: Number of dialogue exchanges.

        Returns:
            List of {"speaker": name, "utterance": text} dicts.
        """
        client = self._get_client()
        messages: list[dict[str, str]] = []
        history: list[dict[str, str]] = []

        system = (
            f"You are simulating a conversation between two characters in a world:\n"
            f"Context: {context}\n"
            f"Topic: {topic}\n\n"
            f"Character A:\n{agent_a_persona}\n\n"
            f"Character B:\n{agent_b_persona}\n\n"
            "Alternate speaking as A and B. Output JSON: "
            '{"speaker": "A" or "B", "utterance": "..."}'
        )

        for i in range(turns):
            speaker = "A" if i % 2 == 0 else "B"
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Now {speaker} speaks. Previous: {json.dumps(history[-3:])}"},
                ],
                temperature=0.9,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            history.append(parsed)

        return history

    async def get_action_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """Like get_action but without forcing JSON response format.

        Used when the caller does not need structured JSON output.
        """
        import openai

        client = self._get_client()
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                )
                choice = response.choices[0]
                usage = response.usage
                return LLMResponse(
                    content=choice.message.content or "",
                    tokens_prompt=usage.prompt_tokens,
                    tokens_completion=usage.completion_tokens,
                    model=self.model,
                )
            except openai.RateLimitError:
                if attempt == 0:
                    logger.warning("Rate limit hit; retrying after 5 s.")
                    await asyncio.sleep(5)
                else:
                    raise
            except openai.OpenAIError as exc:
                logger.error("OpenAI API error in get_action_text: %s", exc)
                raise
        raise RuntimeError("get_action_text: exhausted retries")

    async def generate_narrative(
        self, world_summary: str, events: list[str], style: str = "omniscient"
    ) -> str:
        """Generate a prose narrative for a turn's events.

        Args:
            world_summary: Brief world state description.
            events: List of event descriptions from this turn.
            style: Narrative POV style hint for the LLM.

        Returns:
            A 1-3 paragraph narrative string.
        """
        client = self._get_client()
        prompt = (
            f"World: {world_summary}\n"
            f"Events this turn:\n" + "\n".join(f"- {e}" for e in events) + "\n\n"
            f"Write a {style} narrative (1-3 paragraphs) describing what happened."
        )
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
        )
        return response.choices[0].message.content or ""


class ClaudeCodeInteraction:
    """Claude Code CLI를 통한 LLM 호출.

    ``claude -p`` 명령을 subprocess로 실행하여 응답을 받아 LLMResponse 형태로 반환.
    토큰 수 추적은 CLI가 제공하지 않으므로 0으로 설정.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        self.model = model

    async def get_action(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """Claude Code CLI를 통해 응답 생성.

        Args:
            system_prompt: 에이전트 페르소나 및 세계 컨텍스트.
            user_prompt: 특정 턴 쿼리.
            temperature: 무시됨 (CLI가 직접 지원하지 않음).

        Returns:
            LLMResponse with content and zero token counts.
        """
        import subprocess

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        result = await asyncio.to_thread(
            subprocess.run,
            ["claude", "-p", full_prompt, "--model", self.model, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code CLI failed: {result.stderr}")

        return LLMResponse(
            content=result.stdout.strip(),
            tokens_prompt=0,
            tokens_completion=0,
            model=self.model,
        )


def get_interaction(
    backend: str | None = None,
    model: str | None = None,
) -> "AgentInteraction | ClaudeCodeInteraction":
    """LLM 백엔드에 따른 interaction 객체 팩토리.

    Args:
        backend: 'openai' or 'claude-code'. None이면 config.llm_backend 사용.
        model: 사용할 모델. None이면 config에서 자동 결정.

    Returns:
        AgentInteraction (OpenAI) 또는 ClaudeCodeInteraction (Claude Code CLI).
    """
    from ese.config import config

    effective_backend = backend or config.llm_backend

    if effective_backend == "claude-code":
        effective_model = model or config.claude_model
        return ClaudeCodeInteraction(model=effective_model)
    else:
        effective_model = model or config.openai_model
        return AgentInteraction(api_key=config.openai_api_key, model=effective_model)
