"""Step 1: the working outline.

Nadine's method starts from the intended purpose, the device's specific
characteristics and its main manufacturing processes, broken into
individual components that can each be compared with the code descriptions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PURPOSE = "purpose"
CHARACTERISTIC = "characteristic"
PROCESS = "process"


@dataclass(frozen=True)
class Component:
    id: str        # e.g. "P1", "C2", "M1"
    kind: str      # purpose, characteristic or process
    text: str


@dataclass
class Outline:
    device_name: str
    intended_purpose: str
    is_active: bool                      # relies on external energy (incl. software) -> MDA
    characteristics: list[str] = field(default_factory=list)
    processes: list[str] = field(default_factory=list)

    def components(self) -> list[Component]:
        parts: list[Component] = []
        for i, sentence in enumerate(_split_sentences(self.intended_purpose), 1):
            parts.append(Component(f"P{i}", PURPOSE, sentence))
        for i, text in enumerate(_clean(self.characteristics), 1):
            parts.append(Component(f"C{i}", CHARACTERISTIC, text))
        for i, text in enumerate(_clean(self.processes), 1):
            parts.append(Component(f"M{i}", PROCESS, text))
        return parts


def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.;])\s+|\n+", text.strip())
    return [p.strip(" .;") for p in pieces if p.strip(" .;")]


def _clean(items: list[str]) -> list[str]:
    return [i.strip() for i in items if i and i.strip()]
