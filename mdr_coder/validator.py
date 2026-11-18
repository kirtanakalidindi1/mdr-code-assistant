"""Step 4: trace each code back to the outline, in both directions.

- A code with no matching component may not be relevant.
- A component with no matching code may mean a code was missed.

review() runs the same checks on a code list a manufacturer proposed, which
is the notified body (Certification Program Manager) side of the process.
"""
from __future__ import annotations

from dataclasses import dataclass

from .codes import CATCH_ALL_CODES, CodeBook
from .matcher import Candidate
from .outline import Outline

ERROR, WARNING, INFO = "error", "warning", "info"


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str
    code: str | None = None
    component_id: str | None = None


@dataclass
class TraceResult:
    codes: list[str]
    code_support: dict[str, list[str]]       # code -> component ids that support it
    component_codes: dict[str, list[str]]    # component id -> codes (from the list) it maps to
    findings: list[Finding]

    @property
    def ok(self) -> bool:
        return not any(f.severity == ERROR for f in self.findings)


def trace(outline: Outline, codes: list[str], candidates: list[Candidate], book: CodeBook) -> TraceResult:
    findings: list[Finding] = []
    known: list[str] = []
    for raw in codes:
        if raw in book:
            known.append(book.get(raw).code)
        else:
            findings.append(Finding(ERROR, f"'{raw}' is not a code in Regulation 2017/2185.", code=raw))
    known = list(dict.fromkeys(known))

    # Structural rules
    mains = [c for c in known if book.get(c).is_main]
    expected = "MDA" if outline.is_active else "MDN"
    if not mains:
        findings.append(Finding(ERROR, "No main (MDA/MDN) code. Every device needs exactly one."))
    elif len(mains) > 1:
        findings.append(Finding(ERROR, f"{len(mains)} main codes ({', '.join(mains)}). Exactly one is allowed."))
    for c in mains:
        if book.get(c).type != expected:
            kind = "active" if outline.is_active else "non-active"
            findings.append(Finding(ERROR, f"{c} is {book.get(c).type}, but the device is {kind} (expects {expected}).", code=c))
    if not any(book.get(c).type == "MDT" for c in known):
        findings.append(Finding(ERROR, "No MDT code. Every device needs at least one."))

    # Two-way trace
    code_support = {c: [] for c in known}
    component_codes = {comp.id: [] for comp in outline.components()}
    for cand in candidates:
        if cand.code in code_support and cand.component_id in component_codes:
            if cand.component_id not in code_support[cand.code]:
                code_support[cand.code].append(cand.component_id)
            if cand.code not in component_codes[cand.component_id]:
                component_codes[cand.component_id].append(cand.code)

    for code, support in code_support.items():
        if not support and code not in CATCH_ALL_CODES:
            findings.append(Finding(
                WARNING,
                f"{code} has no matching characteristic or process in the outline. "
                "It may not be relevant, or the outline is missing something.",
                code=code,
            ))
    texts = {comp.id: comp.text for comp in outline.components()}
    for comp_id, mapped in component_codes.items():
        if mapped:
            continue
        suggested = list(dict.fromkeys(c.code for c in candidates if c.component_id == comp_id))
        if suggested and all(book.get(c).is_main for c in suggested) and mains:
            findings.append(Finding(
                INFO,
                f"'{texts[comp_id]}' points to {', '.join(suggested)}, which lost the "
                f"highest-in-list tie-break to {mains[0]}. Covered by the main code.",
                component_id=comp_id,
            ))
        else:
            findings.append(Finding(
                WARNING,
                f"'{texts[comp_id]}' has no code. A code may have been missed.",
                component_id=comp_id,
            ))

    return TraceResult(known, code_support, component_codes, findings)


def review(outline: Outline, proposed: list[str], candidates: list[Candidate], book: CodeBook) -> TraceResult:
    """Check a manufacturer's proposed codes, as a notified body would."""
    result = trace(outline, proposed, candidates, book)
    proposed_known = set(result.codes)

    # Highest-applicable-code rule
    supported_mains = list(dict.fromkeys(
        c.code for c in candidates
        if book.get(c.code).is_main and c.code not in CATCH_ALL_CODES
    ))
    best = book.highest(supported_mains)
    proposed_main = [c for c in result.codes if book.get(c).is_main]
    if best and proposed_main and best not in proposed_main:
        if book.get(best).order < book.get(proposed_main[0]).order:
            result.findings.append(Finding(
                WARNING,
                f"The outline also supports {best} ({book.get(best).description}), which is higher "
                f"in the list than {proposed_main[0]}. Per MDCG 2019-14 the highest applicable code "
                "should be the main code.",
                code=best,
            ))

    # Horizontal codes the outline supports but the application doesn't list
    for code in dict.fromkeys(c.code for c in candidates):
        if not book.get(code).is_main and code not in proposed_known:
            result.findings.append(Finding(
                INFO,
                f"The outline suggests {code} ({book.get(code).description}). Confirm whether it applies.",
                code=code,
            ))
    return result
