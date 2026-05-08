"""Unit tests for the eyecite-backed statute citation parser."""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

from kaos_citations.extract import extract_citations
from kaos_citations.model import StatuteCitation

_HAS_EYECITE = importlib.util.find_spec("eyecite") is not None

_FIXTURE = (
    pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "statute-citations-golden.jsonl"
)


def _load_golden() -> list[dict]:
    rows: list[dict] = []
    for line in _FIXTURE.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


@pytest.mark.unit
@pytest.mark.skipif(not _HAS_EYECITE, reason="eyecite not installed ([legal] extra)")
class TestStatuteGoldenSet:
    @pytest.mark.parametrize("row", _load_golden())
    def test_parses_each_golden_citation(self, row: dict) -> None:
        from kaos_citations.parsers.statute import extract_statute_citations

        citations = extract_statute_citations(row["text"])
        assert len(citations) == 1, (
            f"Expected exactly 1 citation in {row['text']!r}, got {len(citations)}: "
            f"{[c.raw for c in citations]}"
        )
        cit = citations[0]
        assert isinstance(cit, StatuteCitation)
        assert cit.title == row["title"]
        assert cit.code == row["code"]
        assert cit.section == row["section"]
        # Span round-trip.
        start, end = cit.span
        assert row["text"][start:end] == cit.raw


@pytest.mark.unit
@pytest.mark.skipif(not _HAS_EYECITE, reason="eyecite not installed ([legal] extra)")
class TestStatuteBehavior:
    def test_dispatcher_routes_statute_kind(self) -> None:
        hits = extract_citations("See 42 U.S.C. § 1983.", kinds=["statute"])
        assert len(hits) == 1
        cit = hits[0]
        assert isinstance(cit, StatuteCitation)
        assert cit.title == "42"
        assert cit.section == "1983"

    def test_mixed_cfr_and_statute(self) -> None:
        """CFR + statute with a numeric-only section — both must be picked up."""
        text = "17 CFR 240.10b-5 implements the authority granted by 42 U.S.C. § 1983."
        hits = extract_citations(text)
        kinds = [h.kind for h in hits]
        assert "cfr" in kinds
        assert "statute" in kinds


@pytest.mark.unit
@pytest.mark.skipif(not _HAS_EYECITE, reason="eyecite not installed ([legal] extra)")
class TestStatuteKnownLimitations:
    """Document what eyecite's ``FullLawCitation`` parser cannot handle.

    These are pinned as tests so the coverage truth lives in code, not
    hope. When a future eyecite release fixes any of these, the
    corresponding test will start failing and we'll move the citation
    into the golden set.
    """

    def test_section_with_trailing_paren(self) -> None:
        """``18 U.S.C. § 924(c)`` — the parser captures the full
        ``924(c)`` section, including the parenthesized subsection."""
        from kaos_citations.parsers.statute import extract_statute_citations

        hits = extract_statute_citations("18 U.S.C. § 924(c)")
        assert len(hits) == 1
        assert hits[0].section == "924(c)"

    def test_alphanumeric_section_via_regex_fallback(self) -> None:
        """WS-2.5 fix: USC sections with alphanumeric/parenthesized
        subsections (``78j(b)``, ``2000e``) confused eyecite into
        emitting just the ``§`` as an UnknownCitation. Our regex
        fallback recovers them as proper StatuteCitations.
        """
        from kaos_citations.parsers.statute import extract_statute_citations

        hits_78j = extract_statute_citations("15 U.S.C. § 78j(b)")
        assert len(hits_78j) == 1
        assert hits_78j[0].title == "15"
        assert hits_78j[0].section == "78j(b)"
        assert hits_78j[0].code == "U.S.C."

        hits_2000e = extract_statute_citations("42 U.S.C. § 2000e")
        assert len(hits_2000e) == 1
        assert hits_2000e[0].section == "2000e"
