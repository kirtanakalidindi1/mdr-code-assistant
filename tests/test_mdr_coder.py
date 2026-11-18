import pytest

from mdr_coder import KeywordMatcher, Outline, load_codes, review, select, trace
from mdr_coder.codes import normalise
from mdr_coder.examples import EXAMPLES
from mdr_coder.validator import ERROR, INFO, WARNING


@pytest.fixture(scope="module")
def book():
    return load_codes()


def run(outline, book):
    cands = KeywordMatcher().match(outline, book)
    return cands, select(outline, cands, book)


def test_code_counts_match_regulation(book):
    # Nadine's article: 26 MDA, 18 MDN, 14 MDS, 13 MDT
    counts = {t: len(book.of_type(t)) for t in ("MDA", "MDN", "MDS", "MDT")}
    assert counts == {"MDA": 26, "MDN": 18, "MDS": 14, "MDT": 13}


def test_normalise():
    assert normalise("mda0302") == "MDA 0302"
    assert normalise("MDA-0302") == "MDA 0302"


def test_eye_laser_takes_highest_code(book):
    # Nadine's worked example: 0302, 0309 and 0312 all fit; 0302 is highest in the list.
    _, sel = run(EXAMPLES["Eye-surgery laser (Nadine's example)"], book)
    assert sel.main_candidates == ["MDA 0302", "MDA 0309", "MDA 0312"]
    assert sel.main_code == "MDA 0302"


def test_every_example_gets_one_main_and_an_mdt(book):
    for outline in EXAMPLES.values():
        cands, sel = run(outline, book)
        result = trace(outline, sel.all_codes, cands, book)
        assert sel.main_code is not None
        assert sel.mdt, outline.device_name
        assert result.ok, [f.message for f in result.findings]


def test_person_can_override_candidates(book):
    outline = EXAMPLES["AI ECG photo app (SaMD)"]
    cands = KeywordMatcher().match(outline, book)
    sel = select(outline, cands, book, confirmed_main=["MDA 0315"])
    assert sel.main_code == "MDA 0315"


def test_trace_flags_structural_errors(book):
    outline = EXAMPLES["Eye-surgery laser (Nadine's example)"]
    cands = KeywordMatcher().match(outline, book)
    result = trace(outline, ["MDA 0302", "MDA 0309", "MDN 1208", "XYZ 9999"], cands, book)
    messages = " ".join(f.message for f in result.findings if f.severity == ERROR)
    assert "main codes" in messages          # more than one main code
    assert "non-active" not in messages
    assert "MDN" in messages                 # MDN on an active device
    assert "No MDT" in messages
    assert "XYZ 9999" in messages            # not a real code


def test_trace_flags_orphan_code_and_unmapped_component(book):
    outline = Outline(
        device_name="Test",
        intended_purpose="A laser for eye surgery.",
        is_active=True,
        characteristics=["Supplied sterile"],
        processes=["Packaging and labelling"],
    )
    cands = KeywordMatcher().match(outline, book)
    result = trace(outline, ["MDA 0302", "MDS 1007", "MDT 2011"], cands, book)
    warnings = [f for f in result.findings if f.severity == WARNING]
    assert any(f.code == "MDS 1007" for f in warnings)       # nanomaterial: nothing in outline
    assert any(f.component_id == "C1" for f in warnings)     # sterile: no code chosen


def test_review_catches_main_code_that_is_not_highest(book):
    outline = EXAMPLES["Eye-surgery laser (Nadine's example)"]
    cands = KeywordMatcher().match(outline, book)
    result = review(outline, ["MDA 0309", "MDS 1005", "MDT 2010", "MDT 2011"], cands, book)
    assert any(f.code == "MDA 0302" and f.severity == WARNING for f in result.findings)


def test_review_suggests_missing_horizontal_code(book):
    outline = EXAMPLES["Eye-surgery laser (Nadine's example)"]
    cands = KeywordMatcher().match(outline, book)
    result = review(outline, ["MDA 0302", "MDT 2010", "MDT 2011"], cands, book)
    assert any(f.code == "MDS 1005" and f.severity == INFO for f in result.findings)
