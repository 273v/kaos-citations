"""Unit tests for US Constitution citation parser — WS-2.5."""

from __future__ import annotations

import pytest

from kaos_citations.parsers.constitution import (
    extract_constitution_citations,
    iter_constitution_matches,
)


class TestArticleCitations:
    @pytest.mark.parametrize(
        ("text", "article", "section", "clause"),
        [
            ("U.S. Const. art. III", "III", None, None),
            ("U.S. Const. art. III, § 2", "III", "2", None),
            ("U.S. Const. art. I, § 8, cl. 3", "I", "8", "3"),
            ("U.S. Const. art. II, § 1, cl. 5", "II", "1", "5"),
            ("U.S. Const. art. VI", "VI", None, None),
        ],
    )
    def test_article_form(
        self,
        text: str,
        article: str,
        section: str | None,
        clause: str | None,
    ) -> None:
        hits = extract_constitution_citations(text)
        assert len(hits) == 1
        assert hits[0].article == article
        assert hits[0].section == section
        assert hits[0].clause == clause
        assert hits[0].amendment is None

    def test_lowercase_const_token(self) -> None:
        hits = extract_constitution_citations("u.s. const. art. iii")
        assert len(hits) == 1
        assert hits[0].article == "III"  # normalized to uppercase

    def test_full_united_states_constitution(self) -> None:
        hits = extract_constitution_citations("United States Constitution, art. III")
        assert len(hits) == 1
        assert hits[0].article == "III"


class TestAmendmentCitations:
    @pytest.mark.parametrize(
        ("text", "amendment", "section"),
        [
            ("U.S. Const. amend. I", "I", None),
            ("U.S. Const. amend. XIV, § 1", "XIV", "1"),
            ("U.S. Const. amend. XIV, § 5", "XIV", "5"),
            ("U.S. Const. amend. V", "V", None),
            ("U.S. Const. amend. XXVII", "XXVII", None),
        ],
    )
    def test_amendment_form(self, text: str, amendment: str, section: str | None) -> None:
        hits = extract_constitution_citations(text)
        assert len(hits) == 1
        assert hits[0].amendment == amendment
        assert hits[0].section == section
        assert hits[0].article is None
        assert hits[0].clause is None


class TestNormalization:
    def test_article_with_clause_normalized(self) -> None:
        hits = extract_constitution_citations("U.S. Const. art. I, § 8, cl. 3")
        assert hits[0].normalized == "U.S. Const. art. I, § 8, cl. 3"

    def test_amendment_with_section_normalized(self) -> None:
        hits = extract_constitution_citations("u.s. const. amend. xiv, § 1")
        assert hits[0].normalized == "U.S. Const. amend. XIV, § 1"

    def test_bare_amendment_normalized(self) -> None:
        hits = extract_constitution_citations("U.S. Const. amend. I")
        assert hits[0].normalized == "U.S. Const. amend. I"


class TestSpanRoundTrip:
    def test_span_matches_raw(self) -> None:
        text = "Plaintiffs cite U.S. Const. amend. XIV, § 1 in support."
        hits = extract_constitution_citations(text)
        assert len(hits) == 1
        s = hits[0].span
        assert text[s[0] : s[1]] == hits[0].raw


class TestMultipleCitations:
    def test_article_and_amendment_in_same_text(self) -> None:
        text = (
            "See U.S. Const. art. I, § 8, cl. 3 (Commerce Clause) and "
            "U.S. Const. amend. XIV, § 1 (Equal Protection)."
        )
        hits = extract_constitution_citations(text)
        assert len(hits) == 2
        kinds = {h.article or h.amendment for h in hits}
        assert "I" in kinds
        assert "XIV" in kinds
        # Sorted by span
        assert hits[0].span[0] < hits[1].span[0]


class TestNoFalsePositives:
    def test_unrelated_text(self) -> None:
        assert extract_constitution_citations("The cat sat on the mat.") == []

    def test_const_token_alone_doesnt_match(self) -> None:
        # "Const." without "U.S." prefix should not match
        assert extract_constitution_citations("Const. art. III") == []


class TestSourceUriPropagation:
    def test_source_uri_threaded(self) -> None:
        hits = extract_constitution_citations("U.S. Const. amend. I", source_uri="brief.pdf")
        assert hits[0].source_uri == "brief.pdf"


class TestIterMatches:
    def test_yields_in_source_order(self) -> None:
        text = "U.S. Const. amend. I and U.S. Const. art. III"
        positions = [m.start for m in iter_constitution_matches(text)]
        assert positions == sorted(positions)


class TestEmpty:
    def test_empty_text(self) -> None:
        assert extract_constitution_citations("") == []
