"""Inspiration system for Dormammu hypothesis generation.

The inspiration system seeds hypothesis generation with ideas drawn from
science fiction narratives, manga/anime/novel storytelling patterns, real
historical analogues, and speculative futures. This prevents the DFS tree
from converging on boring, predictable branches and encourages the kind of
surprising emergent stories that make a living world worth watching.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class InspirationSeed:
    """A single SF or historical inspiration source.

    Used to prime the hypothesis generator with thematic direction.
    """

    title: str
    """Name of the source work or historical event."""
    domain: str
    """Category: 'sci-fi', 'historical', 'speculative', 'mythology', 'manga', 'anime', 'novel', 'film', 'game', 'webtoon'."""
    themes: list[str] = field(default_factory=list)
    """Thematic keywords extracted from the source."""
    prompt_fragment: str = ""
    """A short prompt fragment injected into the hypothesis generator."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "domain": self.domain,
            "themes": self.themes,
            "prompt_fragment": self.prompt_fragment,
        }


# Built-in seed library — expand freely
SEED_LIBRARY: list[InspirationSeed] = [
    InspirationSeed(
        title="Foundation (Asimov)",
        domain="sci-fi",
        themes=["psychohistory", "empire collapse", "long-term planning", "hidden influence"],
        prompt_fragment="Inspired by psychohistory: a hidden pattern in collective behavior shapes the future.",
    ),
    InspirationSeed(
        title="Westworld",
        domain="sci-fi",
        themes=["loops", "memory", "identity", "emergent consciousness", "narrative control"],
        prompt_fragment="Inspired by Westworld: a character breaks their programmed loop and acts unexpectedly.",
    ),
    InspirationSeed(
        title="The Left Hand of Darkness (Le Guin)",
        domain="sci-fi",
        themes=["gender fluidity", "political exile", "trust", "cultural difference"],
        prompt_fragment="Inspired by Le Guin: two fundamentally different beings must build trust across cultural barriers.",
    ),
    InspirationSeed(
        title="Black Death (1347)",
        domain="historical",
        themes=["pandemic", "social restructuring", "labor scarcity", "religious crisis"],
        prompt_fragment="Inspired by historical pandemics: a catastrophic event reshapes social hierarchies overnight.",
    ),
    InspirationSeed(
        title="Dune (Herbert)",
        domain="sci-fi",
        themes=["ecology", "religion as control", "prescience", "resource scarcity"],
        prompt_fragment="Inspired by Dune: control over a scarce critical resource becomes the axis of political power.",
    ),
    InspirationSeed(
        title="Ursula K. Le Guin — The Dispossessed",
        domain="sci-fi",
        themes=["anarchism", "physics", "inequality", "parallel societies"],
        prompt_fragment="Two societies with opposing philosophies are forced into contact; neither is purely right.",
    ),
    InspirationSeed(
        title="The Great Filter (Fermi Paradox)",
        domain="speculative",
        themes=["extinction", "technological threshold", "self-destruction", "transcendence"],
        prompt_fragment="The civilization approaches a threshold where technology could either destroy or elevate it.",
    ),
    InspirationSeed(
        title="Akira (Otomo)",
        domain="sci-fi",
        themes=["psychic power", "urban decay", "youth rebellion", "government control"],
        prompt_fragment="Latent extraordinary power awakens in an unexpected individual, destabilizing existing order.",
    ),
    InspirationSeed(
        title="Three-Body Problem (Liu Cixin)",
        domain="sci-fi",
        themes=["dark forest", "alien contact", "civilization survival", "game theory"],
        prompt_fragment="Inspired by the Dark Forest: mutual distrust between civilizations leads to inevitable conflict hidden beneath cooperation.",
    ),
    InspirationSeed(
        title="Brave New World (Huxley)",
        domain="sci-fi",
        themes=["social conditioning", "happiness vs freedom", "consumerism", "caste system"],
        prompt_fragment="Inspired by Huxley: stability is achieved by eliminating desire itself — but at what cost to humanity?",
    ),
    InspirationSeed(
        title="1984 (Orwell)",
        domain="sci-fi",
        themes=["surveillance", "doublethink", "totalitarianism", "memory manipulation"],
        prompt_fragment="Inspired by Orwell: the party rewrites history so thoroughly that truth becomes a political act.",
    ),
    InspirationSeed(
        title="Neuromancer (Gibson)",
        domain="sci-fi",
        themes=["cyberspace", "corporate power", "AI emergence", "underground economy"],
        prompt_fragment="Inspired by Gibson: the line between flesh and data blurs, and a rogue AI begins to want something.",
    ),
    InspirationSeed(
        title="Snow Crash (Stephenson)",
        domain="sci-fi",
        themes=["metaverse", "language as virus", "corporate enclaves", "memetic warfare"],
        prompt_fragment="Inspired by Snow Crash: a linguistic/memetic weapon spreads through a networked population with catastrophic speed.",
    ),
    InspirationSeed(
        title="Children of Time (Tchaikovsky)",
        domain="sci-fi",
        themes=["uplift", "convergent evolution", "alien cognition", "first contact"],
        prompt_fragment="Inspired by Children of Time: an uplifted species develops civilization along radically non-human lines.",
    ),
    InspirationSeed(
        title="Blindsight (Watts)",
        domain="sci-fi",
        themes=["consciousness", "alien intelligence", "self-deception", "evolutionary pressure"],
        prompt_fragment="Inspired by Blindsight: consciousness itself may be an evolutionary dead end — the truly alien thinks without self-awareness.",
    ),
    InspirationSeed(
        title="Ringworld (Niven)",
        domain="sci-fi",
        themes=["megastructure", "alien artifact", "resource exhaustion", "stellar engineering"],
        prompt_fragment="Inspired by Ringworld: a civilization encounters a structure so vast it reframes every assumption about what intelligence can build.",
    ),
    InspirationSeed(
        title="The Expanse (Corey)",
        domain="sci-fi",
        themes=["Belt politics", "protomolecule", "faction war", "class conflict"],
        prompt_fragment="Inspired by The Expanse: resource inequality between planets sparks a revolutionary movement that upends every alliance.",
    ),
    InspirationSeed(
        title="Hyperion (Simmons)",
        domain="sci-fi",
        themes=["time cruciform", "pilgrimage", "AI schism", "empire decline"],
        prompt_fragment="Inspired by Hyperion: multiple travelers each carry a piece of a mystery that, assembled, reveals the empire is already doomed.",
    ),
    InspirationSeed(
        title="French Revolution (1789)",
        domain="historical",
        themes=["class uprising", "idealism vs terror", "institutional collapse", "charismatic leaders"],
        prompt_fragment="Inspired by the French Revolution: a utopian ideal rapidly transforms into a reign of terror as factions turn on each other.",
    ),
    InspirationSeed(
        title="The Singularity (Vinge / Kurzweil)",
        domain="speculative",
        themes=["superintelligence", "exponential growth", "post-human", "incomprehensibility"],
        prompt_fragment="Inspired by the Singularity: a threshold is crossed beyond which the old categories of power, war, and meaning no longer apply.",
    ),
    InspirationSeed(
        title="Collapse of Bronze Age (1200 BCE)",
        domain="historical",
        themes=["systems collapse", "sea peoples", "trade network failure", "dark age"],
        prompt_fragment="Inspired by Bronze Age Collapse: interconnected civilizations fail simultaneously when multiple stressors converge at once.",
    ),
    InspirationSeed(
        title="Solaris (Lem)",
        domain="sci-fi",
        themes=["unknowable alien", "projection", "ocean intelligence", "communication failure"],
        prompt_fragment="Inspired by Solaris: contact with a truly alien mind forces each observer to confront their own unconscious projections.",
    ),
    # ===== Manga / Anime / Novel storytelling patterns =====
    InspirationSeed(
        title="진격의 거인 (이사야마 하지메)",
        domain="manga",
        themes=["자유 vs 속박", "순환하는 역사", "적과 아군의 경계", "선택의 무게", "세계의 잔혹함"],
        prompt_fragment="진격의 거인에서 영감: 적이었던 존재와 아군의 경계가 무너지며, 정의란 관점에 따라 달라진다는 것을 깨닫는 순간.",
    ),
    InspirationSeed(
        title="원피스 (오다 에이이치로)",
        domain="manga",
        themes=["꿈과 의지", "동료애", "세계정부의 은폐", "자유", "D의 의지"],
        prompt_fragment="원피스에서 영감: 거대한 권력에 맞서는 것은 거창한 이념이 아니라 '동료를 지키겠다'는 단순한 의지에서 시작된다.",
    ),
    InspirationSeed(
        title="강철의 연금술사 (아라카와 히로무)",
        domain="manga",
        themes=["등가교환", "진리의 문", "형제의 유대", "국가의 음모", "인조인간"],
        prompt_fragment="강철의 연금술사에서 영감: 무언가를 얻으려면 동등한 대가를 지불해야 한다. 가장 큰 진리는 가장 큰 희생을 요구한다.",
    ),
    InspirationSeed(
        title="데스노트 (오바 쓰구미)",
        domain="manga",
        themes=["정의의 이중성", "지능 대결", "권력의 부패", "신이 되려는 인간"],
        prompt_fragment="데스노트에서 영감: 절대적 힘을 가진 자의 도덕적 타락 — 정의를 실현하려는 의도가 어떻게 악으로 변질되는가.",
    ),
    InspirationSeed(
        title="나루토 (기시모토 마사시)",
        domain="manga",
        themes=["인정받고 싶은 욕구", "운명 vs 노력", "증오의 순환", "닌자 세계의 구조적 폭력"],
        prompt_fragment="나루토에서 영감: 증오의 순환을 끊는 것은 더 큰 폭력이 아니라 상대를 이해하려는 집요한 의지.",
    ),
    InspirationSeed(
        title="주술회전 (아쿠타미 게게)",
        domain="manga",
        themes=["저주", "비합리적 죽음", "강자의 고독", "세대 갈등"],
        prompt_fragment="주술회전에서 영감: 올바른 죽음이란 존재하지 않으며, 중요한 것은 어떻게 살았는가에 대한 자기 납득.",
    ),
    InspirationSeed(
        title="슬램덩크 (이노우에 다케히코)",
        domain="manga",
        themes=["성장", "팀워크", "패배의 의미", "재능 vs 노력"],
        prompt_fragment="슬램덩크에서 영감: 패배 그 자체가 성장이며, 포기하지 않는 것이 최고의 재능이다.",
    ),
    InspirationSeed(
        title="귀멸의 칼날 (고토게 코요하루)",
        domain="manga",
        themes=["유대의 힘", "악의 기원", "복수 vs 용서", "인간의 의지"],
        prompt_fragment="귀멸의 칼날에서 영감: 악인에게도 인간이었던 기억이 있으며, 진정한 강함은 타인을 지키려는 마음.",
    ),
    InspirationSeed(
        title="몬스터 (우라사와 나오키)",
        domain="manga",
        themes=["인간의 본질", "선과 악의 경계", "연쇄살인", "용서할 수 없는 악"],
        prompt_fragment="몬스터에서 영감: 절대적 악은 존재하는가? 생명을 구하는 행위가 더 큰 재앙을 낳을 때의 도덕적 딜레마.",
    ),
    InspirationSeed(
        title="카우보이 비밥",
        domain="anime",
        themes=["과거와의 대면", "고독한 방랑", "재즈적 즉흥성", "엔딩의 미학"],
        prompt_fragment="카우보이 비밥에서 영감: 과거를 떠나보낼 수 있는가? 진정한 자유는 과거와의 화해 이후에 온다.",
    ),
    InspirationSeed(
        title="해리 포터 (J.K. 롤링)",
        domain="novel",
        themes=["선택이 운명을 만든다", "죽음 앞의 사랑", "권력의 유혹", "정체성"],
        prompt_fragment="해리포터에서 영감: 태어난 환경이 아니라 무엇을 선택하느냐가 그 사람을 결정한다.",
    ),
    InspirationSeed(
        title="반지의 제왕 (톨킨)",
        domain="novel",
        themes=["절대 권력의 유혹", "작은 자의 위대함", "동맹", "귀환과 상실"],
        prompt_fragment="반지의 제왕에서 영감: 세상을 구하는 것은 가장 강한 자가 아니라 가장 순수한 의지를 가진 자.",
    ),
]


class InspirationSystem:
    """Provides SF and historical inspiration seeds for hypothesis generation.

    The system selects seeds relevant to the simulation topic and injects
    them as prompt fragments to steer the LLM toward narratively rich hypotheses.
    """

    def __init__(self, seed_library: list[InspirationSeed] | None = None) -> None:
        self.library = seed_library or SEED_LIBRARY

    def pick(self, topic: str, count: int = 2, domain: str | None = None) -> list[InspirationSeed]:
        """Select `count` inspiration seeds relevant to the topic.

        Args:
            topic: Simulation topic for relevance filtering (currently unused
                   in the stub; add embedding similarity in full implementation).
            count: Number of seeds to return.
            domain: If provided, restrict to seeds from this domain.

        Returns:
            A list of InspirationSeed objects.
        """
        pool = [s for s in self.library if domain is None or s.domain == domain]
        if not pool:
            pool = self.library
        return random.sample(pool, min(count, len(pool)))

    def pick_by_genre(self, source_title: str, count: int = 2) -> list[InspirationSeed]:
        """원작과 동일한 장르의 영감 소스를 우선 선택.

        Args:
            source_title: 원작 제목 (scenario.json의 source.title).
            count: 반환할 시드 수.

        Returns:
            동일 장르 시드 우선, 부족하면 다른 장르에서 보충.
        """
        # 원작이 시드 라이브러리에 있으면 해당 도메인 파악
        source_domain = None
        for seed in self.library:
            if source_title.lower() in seed.title.lower():
                source_domain = seed.domain
                break

        if source_domain:
            # 동일 장르에서 원작 자체는 제외하고 선택
            same_genre = [
                s for s in self.library
                if s.domain == source_domain
                and source_title.lower() not in s.title.lower()
            ]
            if len(same_genre) >= count:
                return random.sample(same_genre, count)
            # 부족하면 다른 장르에서 보충
            others = [s for s in self.library if s not in same_genre]
            needed = count - len(same_genre)
            return same_genre + random.sample(others, min(needed, len(others)))

        # 원작 정보 없으면 기존 방식
        return self.pick(source_title, count)

    def build_injection(self, seeds: list[InspirationSeed]) -> str:
        """Format selected seeds as a prompt injection block.

        Args:
            seeds: Seeds to format.

        Returns:
            A multi-line string ready to append to a hypothesis generation prompt.
        """
        lines = ["이 분기에 참고할 서사 패턴 (동일 장르 명작에서 발췌):"]
        for seed in seeds:
            lines.append(f"- [{seed.domain}] {seed.title}: {seed.prompt_fragment}")
        return "\n".join(lines)

    def domains(self) -> list[str]:
        """Return unique domain names present in the library."""
        return list({s.domain for s in self.library})

    def all_themes(self) -> list[str]:
        """Return a deduplicated list of all themes across the library."""
        themes: set[str] = set()
        for seed in self.library:
            themes.update(seed.themes)
        return sorted(themes)

    async def search_web(self, topic: str, query: str) -> list[InspirationSeed]:
        """Search the web for inspiration seeds related to topic and query.

        Currently falls back to filtering the local seed library by keyword
        matching against themes and titles. Future implementations can use
        a web search API to fetch real-time results.

        Args:
            topic: The simulation topic for context.
            query: A search query to find relevant inspiration.

        Returns:
            A list of InspirationSeed objects matching the query.
        """
        query_lower = query.lower()
        topic_lower = topic.lower()
        scored: list[tuple[float, InspirationSeed]] = []

        for seed in self.library:
            score = 0.0
            # Score by theme keyword matches
            for theme in seed.themes:
                if any(word in theme.lower() for word in query_lower.split()):
                    score += 1.0
                if any(word in theme.lower() for word in topic_lower.split()):
                    score += 0.5
            # Score by title match
            if any(word in seed.title.lower() for word in query_lower.split()):
                score += 2.0
            # Score by prompt_fragment match
            if any(word in seed.prompt_fragment.lower() for word in query_lower.split()):
                score += 0.5
            if score > 0:
                scored.append((score, seed))

        if not scored:
            # Fallback: return random seeds
            logger.debug("search_web: no keyword matches for %r, returning random seeds", query)
            return self.pick(topic, count=2)

        scored.sort(key=lambda x: -x[0])
        results = [seed for _, seed in scored[:3]]
        logger.debug("search_web: found %d matching seeds for %r", len(results), query)
        return results
