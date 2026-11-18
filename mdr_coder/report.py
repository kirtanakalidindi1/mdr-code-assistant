"""Turn a trace into a rationale table, the 'clean map from outline to codes'."""
from __future__ import annotations

from .codes import CodeBook
from .outline import Outline
from .validator import TraceResult


def rationale_markdown(outline: Outline, result: TraceResult, book: CodeBook) -> str:
    texts = {c.id: c.text for c in outline.components()}
    lines = [
        f"# MDR code rationale: {outline.device_name}",
        "",
        f"**Intended purpose:** {outline.intended_purpose}",
        "",
        "| Code | Description | Supported by |",
        "| --- | --- | --- |",
    ]
    for code in result.codes:
        support = "; ".join(f"{cid}: {texts[cid]}" for cid in result.code_support.get(code, [])) or "None found"
        lines.append(f"| {code} | {book.get(code).description} | {support} |")
    if result.findings:
        lines += ["", "## Findings", ""]
        lines += [f"- **{f.severity.upper()}**: {f.message}" for f in result.findings]
    lines += [
        "",
        "_Decision support only. The notified body has the final word on which codes apply._",
    ]
    return "\n".join(lines)
