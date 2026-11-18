"""Steps 2 and 3: fix the main code, then add the horizontal codes."""
from __future__ import annotations

from dataclasses import dataclass, field

from .codes import CATCH_ALL_CODES, CodeBook
from .matcher import Candidate
from .outline import Outline

SOFTWARE_CODE = "MDA 0315"


@dataclass
class Selection:
    main_code: str | None
    main_candidates: list[str]          # every applicable main code, in regulation order
    mds: list[str]
    mdt: list[str]
    notes: list[str] = field(default_factory=list)

    @property
    def all_codes(self) -> list[str]:
        return ([self.main_code] if self.main_code else []) + self.mds + self.mdt


def select(
    outline: Outline,
    candidates: list[Candidate],
    book: CodeBook,
    confirmed_main: list[str] | None = None,
    confirmed_horizontal: list[str] | None = None,
) -> Selection:
    """Apply the selection rules to candidate codes.

    confirmed_main / confirmed_horizontal let a person accept or reject
    candidates first. If omitted, every candidate is treated as applicable.
    """
    main_type = "MDA" if outline.is_active else "MDN"
    notes: list[str] = []

    # Step 2: main code. Consider every applicable code, then take the highest in the list.
    main_pool = confirmed_main if confirmed_main is not None else _codes_of(candidates, book, main_type)
    main_pool = _in_order([c for c in main_pool if book.get(c).type == main_type], book)
    specific = [c for c in main_pool if c not in CATCH_ALL_CODES]
    ranked = specific or main_pool
    main_code = ranked[0] if ranked else None

    if main_code is None:
        notes.append(
            f"No {main_type} code matched. Check whether the device is active, "
            "or consider the catch-all 'other' code."
        )
    elif main_code in CATCH_ALL_CODES:
        notes.append(f"{main_code} is a catch-all. Confirm no more specific code fits.")
    if len(ranked) > 1:
        others = ", ".join(ranked[1:])
        notes.append(
            f"Several main codes fit ({main_code}, {others}). Per MDCG 2019-14, the one "
            f"highest in Regulation 2017/2185 applies: {main_code}."
        )
    if SOFTWARE_CODE in main_pool and main_code != SOFTWARE_CODE:
        notes.append(
            "MDA 0315 (Software) also fits. Check MDCG 2019-14 on how software relates "
            "to the other MDA codes before finalising the main code."
        )

    # Step 3: horizontal codes, only where the device genuinely has the characteristic or process.
    horizontal_pool = (
        confirmed_horizontal
        if confirmed_horizontal is not None
        else _codes_of(candidates, book, "MDS") + _codes_of(candidates, book, "MDT")
    )
    mds = _in_order([c for c in horizontal_pool if book.get(c).type == "MDS"], book)
    mdt = _in_order([c for c in horizontal_pool if book.get(c).type == "MDT"], book)
    if not mdt:
        notes.append(
            "No MDT code yet. Every device needs at least one: add the main "
            "manufacturing processes to the outline."
        )

    return Selection(main_code, ranked, mds, mdt, notes)


def _codes_of(candidates: list[Candidate], book: CodeBook, code_type: str) -> list[str]:
    return list(dict.fromkeys(c.code for c in candidates if book.get(c.code).type == code_type))


def _in_order(codes: list[str], book: CodeBook) -> list[str]:
    unique = list(dict.fromkeys(book.get(c).code for c in codes if c in book))
    return sorted(unique, key=lambda c: book.get(c).order)
