"""Unit tests for the CFR citation parser."""

from __future__ import annotations

import json
import pathlib

import pytest

from kaos_citations.errors import CitationParseError
from kaos_citations.extract import extract_citations
from kaos_citations.parsers.cfr import extract_cfr_citations

_FIXTURE = (
    pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "cfr-citations-golden.jsonl"
)


def _load_golden() -> list[dict]:
    rows: list[dict] = []
    for line in _FIXTURE.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


@pytest.mark.unit
class TestCFRGoldenSet:
    @pytest.mark.parametrize("row", _load_golden())
    def test_parses_each_golden_citation(self, row: dict) -> None:
        """Every golden fixture must parse to exactly one CFRCitation with
        the expected title, section, and normalized form."""
        citations = extract_cfr_citations(row["text"])
        assert len(citations) == 1, (
            f"Expected exactly 1 citation in {row['text']!r}, got {len(citations)}: "
            f"{[c.raw for c in citations]}"
        )
        cit = citations[0]
        assert cit.title == row["title"], (
            f"title mismatch for {row['text']!r}: got {cit.title}, expected {row['title']}"
        )
        assert cit.section == row["section"], (
            f"section mismatch for {row['text']!r}: got {cit.section!r}, "
            f"expected {row['section']!r}"
        )
        assert cit.normalized == row["normalized"], (
            f"normalized mismatch for {row['text']!r}: got {cit.normalized!r}, "
            f"expected {row['normalized']!r}"
        )
        # Span must point back at the raw substring.
        start, end = cit.span
        assert row["text"][start:end] == cit.raw


@pytest.mark.unit
class TestCFRRoundTrip:
    """The normalized form must itself re-parse to an equivalent citation."""

    @pytest.mark.parametrize("row", _load_golden())
    def test_normalized_round_trip(self, row: dict) -> None:
        first = extract_cfr_citations(row["text"])[0]
        second = extract_cfr_citations(first.normalized)
        assert len(second) == 1
        assert second[0].title == first.title
        assert second[0].section == first.section
        assert second[0].normalized == first.normalized


@pytest.mark.unit
class TestCFRExtraction:
    def test_returns_empty_list_for_empty_text(self) -> None:
        assert extract_cfr_citations("") == []

    def test_returns_empty_list_for_irrelevant_text(self) -> None:
        assert extract_cfr_citations("No citations in this sentence.") == []

    def test_handles_multiple_citations_in_one_paragraph(self) -> None:
        text = (
            "Defendant violated 17 CFR 240.10b-5 and 17 CFR § 240.10b5-1(c)(1). "
            "See also 42 CFR 482.24 for hospital requirements."
        )
        hits = extract_cfr_citations(text)
        assert len(hits) == 3
        assert hits[0].normalized == "17 CFR 240.10b-5"
        assert hits[1].normalized == "17 CFR 240.10b5-1(c)(1)"
        assert hits[2].normalized == "42 CFR 482.24"
        # Spans must be in source order.
        assert hits[0].span[0] < hits[1].span[0] < hits[2].span[0]

    def test_spans_are_exact_character_offsets(self) -> None:
        text = "Before... 17 CFR 240.10b-5 after."
        hits = extract_cfr_citations(text)
        assert len(hits) == 1
        start, end = hits[0].span
        assert text[start:end] == hits[0].raw

    def test_source_uri_threaded(self) -> None:
        text = "17 CFR 240.10b-5"
        hits = extract_cfr_citations(text, source_uri="doc:example")
        assert hits[0].source_uri == "doc:example"

    def test_implausible_title_rejected(self) -> None:
        """CFR titles are 1..50; '99 CFR ...' is a false positive."""
        assert extract_cfr_citations("99 CFR 1.2") == []


@pytest.mark.unit
class TestExtractCitationsDispatcher:
    def test_default_runs_all_supported_kinds(self) -> None:
        text = "Under 17 CFR 240.10b-5 the rule applies."
        hits = extract_citations(text)
        assert len(hits) == 1
        assert hits[0].kind == "cfr"

    def test_kinds_filter_limits_output(self) -> None:
        text = "Under 17 CFR 240.10b-5 the rule applies."
        hits = extract_citations(text, kinds=["cfr"])
        assert len(hits) == 1

    def test_stub_kinds_raise_with_three_part_error(self) -> None:
        """After WS-2.5 the only remaining stub is ``unknown`` — the
        identifier parsers (doi, arxiv, pmid) and Federal Register +
        Constitution are all live now."""
        with pytest.raises(CitationParseError, match="not yet support"):
            extract_citations("irrelevant", kinds=["unknown"])

    def test_arxiv_is_opt_in_not_stub(self) -> None:
        """arXiv parses cleanly when explicitly requested but is excluded
        from the default ``_SUPPORTED_KINDS`` because lawyers rarely
        cite preprints."""
        # Default extraction (no kinds) does NOT run arXiv:
        text = "see arXiv:2401.12345 and 17 CFR 240.10b-5."
        default_hits = extract_citations(text)
        assert all(c.kind != "arxiv" for c in default_hits)
        # Explicit opt-in DOES return arXiv:
        opt_in_hits = extract_citations(text, kinds=["arxiv"])
        assert any(c.kind == "arxiv" for c in opt_in_hits)

    def test_unknown_kinds_raise_with_three_part_error(self) -> None:
        with pytest.raises(CitationParseError, match="Unknown citation kinds"):
            extract_citations("irrelevant", kinds=["totally-made-up"])

    def test_source_uri_propagates_through_dispatcher(self) -> None:
        text = "17 CFR 240.10b-5"
        hits = extract_citations(text, source_uri="doc:multiformat/ecfr.html")
        assert hits[0].source_uri == "doc:multiformat/ecfr.html"

    def test_results_sorted_by_span_start(self) -> None:
        text = "17 CFR 240.10b-5 and earlier 21 CFR 312.2 too."
        hits = extract_citations(text)
        spans = [h.span[0] for h in hits]
        assert spans == sorted(spans)


# ---------------------------------------------------------------------------
# KCITE-02 — subsection-tail bound
# ---------------------------------------------------------------------------


class TestKCITE02SubsectionTailBound:
    """KCITE-02 — subsection-tail (?:\\(...\\)){0,8} cap.

    Pre-fix the tail was an unbounded ``*`` repetition; pathological
    input could match arbitrary nesting depth. Post-fix the ninth
    subsection token onward falls outside the match, so the citation's
    ``section`` text is bounded.
    """

    def test_normal_depth_unchanged(self) -> None:
        # Real-world deep cite — 4 levels — must still match in full.
        hits = extract_cfr_citations("17 CFR 240.10b-5(c)(1)(i)(A)")
        assert len(hits) == 1
        assert hits[0].section == "240.10b-5(c)(1)(i)(A)"

    def test_eight_levels_at_cap(self) -> None:
        text = "17 CFR 240.10b-5" + "".join(f"({c})" for c in "abcdefgh")
        hits = extract_cfr_citations(text)
        assert len(hits) == 1
        # 8 levels are inside the cap.
        assert hits[0].section.count("(") == 8

    def test_pathological_depth_truncated_at_cap(self) -> None:
        # 16 levels of nesting; only 8 should make it into the section.
        levels = "".join(f"({c})" for c in "abcdefghijklmnop")
        text = f"17 CFR 240.10b-5{levels}"
        hits = extract_cfr_citations(text)
        assert len(hits) == 1
        assert hits[0].section.count("(") == 8
