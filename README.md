# MDR Code Assistant

Decision support for choosing and checking EU MDR codes (MDA, MDN, MDS, MDT) for a medical device.

When a manufacturer applies to a notified body under EU MDR, it proposes codes from
[Implementing Regulation (EU) 2017/2185](https://eur-lex.europa.eu/eli/reg_impl/2017/2185/oj/eng).
The codes decide whether the device is within the notified body's scope and which qualified
reviewers assess it, so wrong or missing codes cause back-and-forth and delays.

The tool follows the four-step method in Scarlet's article
[Small codes, big impact: how to get your MDR codes right](https://www.scarlet.cc/blog/small-codes-big-impact-how-to-get-your-mdr-codes-right):

1. **Create a working outline.** Intended purpose, specific characteristics and manufacturing processes, broken into components.
2. **Fix the main code.** Consider every MDA/MDN code that might fit, then take the one highest in the regulation's list (MDCG 2019-14).
3. **Add the horizontal codes.** MDS for characteristics, MDT for processes, only where the device genuinely has them. Every device needs at least one MDT.
4. **Trace each code back.** A code with no matching component may not be relevant. A component with no code may mean a code was missed.

## Two modes

| Mode | Who it's for | What it does |
| --- | --- | --- |
| Suggest codes | Manufacturer | Builds a code list from the outline, applies the selection rules and exports a rationale table |
| Review an application | Notified body | Checks a proposed code list against the outline: structure, highest-code rule, orphan codes, missed codes |

Example: for an eye-surgery laser, MDA 0302 (non-ionising radiation), 0309 (ophthalmic) and 0312
(surgical) all fit. The tool picks **MDA 0302** because it is highest in the list. In review mode, an
application proposing MDA 0309 is flagged.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest            # 9 tests
```

Load an example from the sidebar to see it work. The optional Claude matcher needs
`pip install anthropic` and an `ANTHROPIC_API_KEY`.

## Design choices

- **Rules are code, not AI.** One main code, highest-in-list tie-break, at least one MDT, active vs non-active, and the two-way trace are all deterministic and unit-tested.
- **Matching is swappable.** The offline keyword matcher is transparent and needs no key. The LLM matcher may only choose from the official list for that component type, and any code it invents is discarded.
- **A person decides.** Candidates appear as checkboxes. The tool proposes; the expert confirms.
- **The output is the rationale.** The trace table maps each code to the outline component that justifies it, which is the evidence a notified body wants to see.

## Limitations and open questions

- The keywords in `data/mdr_codes.json` are heuristics written for this tool, not part of the regulation. The code descriptions are copied verbatim.
- **Software devices.** Standalone software often fits a monitoring/diagnosis code (MDA 0203/0204) and MDA 0315 (Software). The tool applies the highest-in-list rule and flags the question for MDCG 2019-14 rather than deciding it.
- **MDT codes for standalone software.** None of the 13 MDT codes is software-specific. Which one(s) notified bodies expect for SaMD is worth confirming.
- Not legal or regulatory advice. The notified body has the final word on which codes apply.

## Ideas for next steps

- Run the review automatically at application intake, before a person picks up the file.
- Add EMDN codes and a change check: *does this change add or remove a code?* That question decides whether a Class IIa/IIb change extends the device range and needs prior approval.
- Map each code to the reviewers qualified for it, to plan assessments.

## Project layout

```
data/mdr_codes.json      all 71 codes from Regulation 2017/2185, in regulation order
mdr_coder/outline.py     step 1: outline and components
mdr_coder/matcher.py     candidate codes per component (keyword or LLM)
mdr_coder/selector.py    steps 2-3: main code and horizontal codes
mdr_coder/validator.py   step 4: two-way trace, and review of a proposed list
mdr_coder/report.py      rationale table export
app.py                   Streamlit UI
tests/                   pytest suite
```
