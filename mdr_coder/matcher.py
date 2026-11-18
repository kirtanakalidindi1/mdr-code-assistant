"""Suggest candidate codes for each outline component.

Two interchangeable matchers:
- KeywordMatcher: transparent, offline, no API key. Uses the heuristic
  keywords in data/mdr_codes.json.
- LLMMatcher: asks Claude to map each component to codes from the official
  list only, then rejects any code it invents. Optional.

Either way, a person confirms the candidates. The tool proposes, the expert decides.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from .codes import CodeBook
from .outline import CHARACTERISTIC, PROCESS, PURPOSE, Component, Outline


@dataclass(frozen=True)
class Candidate:
    code: str
    component_id: str
    score: float
    rationale: str


def eligible_types(kind: str, is_active: bool) -> tuple[str, ...]:
    """Which code types a component can point to.

    Purpose and characteristics describe what the device is and what is
    special about it (main + MDS codes). Processes describe how it is made
    (MDT codes).
    """
    main = "MDA" if is_active else "MDN"
    if kind in (PURPOSE, CHARACTERISTIC):
        return (main, "MDS")
    if kind == PROCESS:
        return ("MDT",)
    return ()


class KeywordMatcher:
    name = "Keyword matcher (offline)"

    def match(self, outline: Outline, book: CodeBook) -> list[Candidate]:
        found: list[Candidate] = []
        for comp in outline.components():
            text = comp.text.lower()
            for code in book.of_type(*eligible_types(comp.kind, outline.is_active)):
                hits = [kw for kw in code.keywords if _contains(text, kw)]
                if hits:
                    found.append(
                        Candidate(
                            code=code.code,
                            component_id=comp.id,
                            score=float(len(hits)),
                            rationale=f"matched: {', '.join(hits)}",
                        )
                    )
        return found


def _contains(text: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}s?\b", text) is not None


class LLMMatcher:
    """Grounded LLM matching: the model may only choose from codes we give it."""

    name = "Claude (LLM)"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        import anthropic  # optional dependency

        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model or os.environ.get("MDR_LLM_MODEL", "claude-sonnet-5-5")

    def match(self, outline: Outline, book: CodeBook) -> list[Candidate]:
        found: list[Candidate] = []
        for comp in outline.components():
            allowed = book.of_type(*eligible_types(comp.kind, outline.is_active))
            found.extend(self._match_component(comp, allowed, book))
        return found

    def _match_component(self, comp: Component, allowed, book: CodeBook) -> list[Candidate]:
        code_list = "\n".join(c.label() for c in allowed)
        prompt = (
            "You help map a medical device description to EU MDR codes "
            "(Implementing Regulation 2017/2185).\n"
            f"Component of the device outline ({comp.kind}): \"{comp.text}\"\n\n"
            "Choose every code from the list below that this component plausibly "
            "supports. Consider all codes that might fit, not only the first. "
            "Use only codes from this list.\n\n"
            f"{code_list}\n\n"
            'Reply with JSON only: {"matches": [{"code": "MDA 0302", '
            '"confidence": 0.0-1.0, "rationale": "one short sentence"}]}. '
            'Return {"matches": []} if none fit.'
        )
        reply = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in reply.content if block.type == "text")
        allowed_codes = {c.code for c in allowed}
        results = []
        for m in _parse_matches(text):
            code = m.get("code", "")
            if code in book and book.get(code).code in allowed_codes:  # reject invented codes
                results.append(
                    Candidate(
                        code=book.get(code).code,
                        component_id=comp.id,
                        score=float(m.get("confidence", 0.5)),
                        rationale=str(m.get("rationale", "")),
                    )
                )
        return results


def _parse_matches(text: str) -> list[dict]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return []
    try:
        return json.loads(match.group(0)).get("matches", [])
    except json.JSONDecodeError:
        return []
