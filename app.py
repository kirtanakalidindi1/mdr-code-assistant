"""MDR Code Assistant: Streamlit UI.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from mdr_coder import KeywordMatcher, Outline, load_codes, review, select, trace
from mdr_coder.examples import EXAMPLES
from mdr_coder.report import rationale_markdown

st.set_page_config(page_title="MDR Code Assistant", layout="wide")
book = load_codes()
for k, v in {"name": "", "purpose": "", "active": True, "chars": "", "procs": ""}.items():
    st.session_state.setdefault(k, v)

ICONS = {"error": "🔴", "warning": "🟠", "info": "🔵"}


# ---------- Sidebar ----------
st.sidebar.title("MDR Code Assistant")
mode = st.sidebar.radio(
    "Mode",
    ["Suggest codes (manufacturer)", "Review an application (notified body)"],
    help="Suggest: build a code list from the outline. Review: check codes someone else proposed.",
)

matcher_name = st.sidebar.selectbox("Matcher", ["Keyword (offline)", "Claude (LLM)"])
matcher = KeywordMatcher()
if matcher_name == "Claude (LLM)":
    key = st.sidebar.text_input("Anthropic API key", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""))
    if key:
        try:
            from mdr_coder import LLMMatcher
            matcher = LLMMatcher(api_key=key)
        except Exception as exc:  # missing package or bad key
            st.sidebar.error(f"LLM matcher unavailable ({exc}). Using keywords.")
    else:
        st.sidebar.info("Add a key to use Claude. Using keywords for now.")

example = st.sidebar.selectbox("Load an example", ["(none)"] + list(EXAMPLES))
if st.sidebar.button("Load") and example != "(none)":
    ex = EXAMPLES[example]
    st.session_state.update(
        name=ex.device_name,
        purpose=ex.intended_purpose,
        active=ex.is_active,
        chars="\n".join(ex.characteristics),
        procs="\n".join(ex.processes),
    )

st.sidebar.caption(
    "Based on Implementing Regulation (EU) 2017/2185 and MDCG 2019-14. "
    "Decision support only: the notified body has the final word."
)


# ---------- Step 1: working outline ----------
st.title("MDR Code Assistant")
st.caption("Outline → main code → horizontal codes → trace each code back")

st.header("1. Working outline")
c1, c2 = st.columns([2, 1])
with c1:
    name = st.text_input("Device name", key="name")
    purpose = st.text_area("Intended purpose", key="purpose", height=110)
with c2:
    active = st.toggle(
        "Active device (uses external energy, incl. software)", key="active",
        help="Active devices take an MDA main code; non-active devices take an MDN code.",
    )
chars = st.text_area("Specific characteristics (one per line)", key="chars", height=90)
procs = st.text_area("Main manufacturing processes (one per line)", key="procs", height=90)

if not purpose.strip():
    st.info("Write an intended purpose, or load an example from the sidebar, to begin.")
    st.stop()

outline = Outline(
    device_name=name or "Unnamed device",
    intended_purpose=purpose,
    is_active=active,
    characteristics=chars.splitlines(),
    processes=procs.splitlines(),
)
components = outline.components()
comp_text = {c.id: c.text for c in components}

with st.expander(f"Outline broken into {len(components)} components"):
    st.dataframe(
        pd.DataFrame([{"ID": c.id, "Type": c.kind, "Text": c.text} for c in components]),
        hide_index=True, width="stretch",
    )

with st.spinner("Matching components to codes..."):
    candidates = matcher.match(outline, book)


def support_for(code: str) -> str:
    return "; ".join(
        f"{c.component_id} ({c.rationale})" for c in candidates if c.code == code
    )


def show_trace(result) -> None:
    rows = []
    for code in result.codes:
        rows.append({
            "Code": code,
            "Description": book.get(code).description,
            "Supported by": "; ".join(f"{cid}: {comp_text[cid]}" for cid in result.code_support[code]) or "—",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if not result.findings:
        st.success("Every code traces to the outline, and every component has a code.")
    order = {"error": 0, "warning": 1, "info": 2}
    for f in sorted(result.findings, key=lambda f: order[f.severity]):
        st.markdown(f"{ICONS[f.severity]} **{f.severity.title()}:** {f.message}")


# ---------- Suggest mode ----------
if mode.startswith("Suggest"):
    st.header("2. Fix the main code")
    main_type = "MDA" if active else "MDN"
    main_cands = [c for c in dict.fromkeys(x.code for x in candidates) if book.get(c).type == main_type]
    main_cands.sort(key=lambda c: book.get(c).order)
    st.write(
        f"Consider every {main_type} code that might fit. Untick any that don't apply. "
        "The one highest in the regulation's list is selected."
    )
    confirmed = []
    for code in main_cands:
        if st.checkbox(f"**{code}**: {book.get(code).description}  \n_{support_for(code)}_", value=True, key=f"m_{code}"):
            confirmed.append(code)
    extra = st.multiselect(
        f"Add a {main_type} code the matcher missed",
        [c.code for c in book.main_codes(active) if c.code not in main_cands],
        format_func=lambda c: book.get(c).label(),
    )
    confirmed += extra

    st.header("3. Add the horizontal codes")
    horiz_suggested = [c for c in dict.fromkeys(x.code for x in candidates) if not book.get(c).is_main]
    horizontal = st.multiselect(
        "MDS (characteristics) and MDT (processes). Keep only what the device genuinely has.",
        [c.code for c in book.of_type("MDS", "MDT")],
        default=horiz_suggested,
        format_func=lambda c: book.get(c).label(),
    )

    selection = select(outline, candidates, book, confirmed_main=confirmed, confirmed_horizontal=horizontal)
    if selection.main_code:
        st.success(f"Main code: **{selection.main_code}**: {book.get(selection.main_code).description}")
    for note in selection.notes:
        st.markdown(f"🔵 {note}")

    st.header("4. Trace each code back")
    result = trace(outline, selection.all_codes, candidates, book)
    show_trace(result)
    st.download_button(
        "Download rationale (Markdown)",
        rationale_markdown(outline, result, book),
        file_name=f"{outline.device_name.replace(' ', '_')}_mdr_codes.md",
    )

# ---------- Review mode ----------
else:
    st.header("2–3. Codes proposed in the application")
    proposed_text = st.text_input("Proposed codes, separated by commas", placeholder="MDA 0309, MDS 1005, MDT 2011")
    proposed = [p.strip() for p in proposed_text.split(",") if p.strip()]
    if not proposed:
        st.info("Enter the manufacturer's proposed codes to review them against the outline.")
        st.stop()

    st.header("4. Trace and review")
    result = review(outline, proposed, candidates, book)
    show_trace(result)
    st.download_button(
        "Download review (Markdown)",
        rationale_markdown(outline, result, book),
        file_name=f"{outline.device_name.replace(' ', '_')}_code_review.md",
    )
