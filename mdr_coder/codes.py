"""The MDR code list (Implementing Regulation (EU) 2017/2185) and helpers.

The order of codes in the regulation matters: MDCG 2019-14 says that when
more than one main (MDA/MDN) code applies, pick the one highest in the list,
because the list runs from most to least specialised expertise.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "mdr_codes.json"

MAIN_TYPES = ("MDA", "MDN")
HORIZONTAL_TYPES = ("MDS", "MDT")

# "Other ..." codes are catch-alls: only use them when nothing more specific fits.
CATCH_ALL_CODES = {"MDA 0318", "MDN 1214"}


@dataclass(frozen=True)
class Code:
    code: str
    type: str          # MDA, MDN, MDS or MDT
    section: str
    description: str
    order: int         # position in the regulation (lower = higher in the list)
    keywords: tuple[str, ...] = field(default=(), compare=False)

    @property
    def is_main(self) -> bool:
        return self.type in MAIN_TYPES

    def label(self) -> str:
        return f"{self.code}: {self.description}"


class CodeBook:
    """All MDR codes, kept in regulation order."""

    def __init__(self, codes: list[Code]):
        self.codes = sorted(codes, key=lambda c: c.order)
        self._by_code = {c.code: c for c in self.codes}

    def __contains__(self, code: str) -> bool:
        return normalise(code) in self._by_code

    def __len__(self) -> int:
        return len(self.codes)

    def get(self, code: str) -> Code:
        return self._by_code[normalise(code)]

    def of_type(self, *types: str) -> list[Code]:
        return [c for c in self.codes if c.type in types]

    def main_codes(self, is_active: bool) -> list[Code]:
        return self.of_type("MDA" if is_active else "MDN")

    def highest(self, codes: list[str]) -> str | None:
        """Return the code that appears highest in the regulation's list."""
        known = [self.get(c) for c in codes if c in self]
        if not known:
            return None
        return min(known, key=lambda c: c.order).code


def normalise(code: str) -> str:
    """'mda0302', 'MDA-0302' and 'MDA 0302' all become 'MDA 0302'."""
    cleaned = "".join(ch for ch in code.upper() if ch.isalnum())
    return f"{cleaned[:3]} {cleaned[3:]}" if len(cleaned) == 7 else code.strip().upper()


def load_codes(path: Path | str = DATA_FILE) -> CodeBook:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    codes = [
        Code(
            code=item["code"],
            type=item["type"],
            section=item["section"],
            description=item["description"],
            order=i,
            keywords=tuple(k.lower() for k in item.get("keywords", [])),
        )
        for i, item in enumerate(raw["codes"])
    ]
    return CodeBook(codes)
