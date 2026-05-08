"""Unit tests for DOI / arXiv / PubMed identifier parsers — WS-2.5."""

from __future__ import annotations

import pytest

from kaos_citations.parsers.identifiers import (
    extract_arxiv_citations,
    extract_doi_citations,
    extract_pubmed_citations,
)

# ---------------------------------------------------------------------------
# DOI
# ---------------------------------------------------------------------------


class TestDOI:
    @pytest.mark.parametrize(
        "text",
        [
            "10.1000/xyz123",
            "10.1145/3133956.3134105",
            "10.1109/TPAMI.2020.3001905",
            "10.1038/nature12373",
            "10.4135/9781452218373.n50",
        ],
    )
    def test_bare_doi(self, text: str) -> None:
        hits = extract_doi_citations(text)
        assert len(hits) == 1
        assert hits[0].doi == text
        assert hits[0].normalized == f"https://doi.org/{text}"

    def test_doi_url_prefix(self) -> None:
        hits = extract_doi_citations("https://doi.org/10.1145/3133956.3134105")
        assert len(hits) == 1
        assert hits[0].doi == "10.1145/3133956.3134105"

    def test_doi_url_with_dx(self) -> None:
        hits = extract_doi_citations("http://dx.doi.org/10.1000/xyz123")
        assert len(hits) == 1
        assert hits[0].doi == "10.1000/xyz123"

    def test_doi_inline_in_paragraph(self) -> None:
        text = "See the methods at 10.1145/3133956.3134105 for details."
        hits = extract_doi_citations(text)
        assert len(hits) == 1
        assert hits[0].span == (
            text.index("10.1145"),
            text.index("10.1145") + len("10.1145/3133956.3134105"),
        )

    def test_trailing_punctuation_stripped(self) -> None:
        """Sentence-final periods and parens must not be included in the DOI."""
        text = "(see 10.1145/3133956.3134105)."
        hits = extract_doi_citations(text)
        assert hits[0].doi == "10.1145/3133956.3134105"
        # Span should point AT the DOI, not include the trailing `).`
        assert text[hits[0].span[0] : hits[0].span[1]] == hits[0].raw

    def test_multiple_dois(self) -> None:
        text = "Compare 10.1109/TPAMI.2020.3001905 with 10.1145/3133956.3134105."
        hits = extract_doi_citations(text)
        assert len(hits) == 2
        assert hits[0].span[0] < hits[1].span[0]


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------


class TestArXivNewStyle:
    @pytest.mark.parametrize(
        ("text", "expected_id"),
        [
            ("arXiv:2401.12345", "2401.12345"),
            ("arxiv:2401.12345", "2401.12345"),
            ("arXiv:2401.12345v2", "2401.12345v2"),
            ("arXiv:0704.0001", "0704.0001"),
            ("arXiv:2301.12345v10", "2301.12345v10"),
        ],
    )
    def test_new_style(self, text: str, expected_id: str) -> None:
        hits = extract_arxiv_citations(text)
        assert len(hits) == 1
        assert hits[0].arxiv_id == expected_id
        assert hits[0].normalized == f"arXiv:{expected_id}"


class TestArXivOldStyle:
    @pytest.mark.parametrize(
        ("text", "expected_id"),
        [
            ("arXiv:hep-th/0001234", "hep-th/0001234"),
            ("arXiv:math.AG/9903012", "math.AG/9903012"),
            ("arXiv:cs.CL/0512012", "cs.CL/0512012"),
        ],
    )
    def test_old_style(self, text: str, expected_id: str) -> None:
        hits = extract_arxiv_citations(text)
        assert len(hits) == 1
        assert hits[0].arxiv_id == expected_id


class TestArXivURLs:
    def test_abs_url(self) -> None:
        hits = extract_arxiv_citations("https://arxiv.org/abs/2401.12345")
        assert len(hits) == 1
        assert hits[0].arxiv_id == "2401.12345"

    def test_pdf_url_with_version(self) -> None:
        hits = extract_arxiv_citations("https://arxiv.org/pdf/2401.12345v3")
        assert len(hits) == 1
        assert hits[0].arxiv_id == "2401.12345v3"


class TestArXivNoFalsePositives:
    def test_bare_id_without_prefix_skipped(self) -> None:
        """Bare ``2401.12345`` in running prose should NOT match — too
        easy to confuse with other numeric tokens."""
        assert extract_arxiv_citations("section 2401.12345") == []

    def test_unrelated_text(self) -> None:
        assert extract_arxiv_citations("The cat sat on the mat.") == []


# ---------------------------------------------------------------------------
# PubMed PMID
# ---------------------------------------------------------------------------


class TestPMID:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("PMID:12345678", 12345678),
            ("PMID: 12345678", 12345678),
            ("PMID 12345678", 12345678),
            ("pmid:12345", 12345),
            ("PMID:1", 1),
        ],
    )
    def test_canonical_forms(self, text: str, expected: int) -> None:
        hits = extract_pubmed_citations(text)
        assert len(hits) == 1
        assert hits[0].pmid == expected
        assert hits[0].normalized == f"PMID:{expected}"

    def test_pubmed_prefix_word(self) -> None:
        hits = extract_pubmed_citations("pubmed:12345678")
        assert len(hits) == 1
        assert hits[0].pmid == 12345678

    def test_pubmed_url(self) -> None:
        hits = extract_pubmed_citations("https://pubmed.ncbi.nlm.nih.gov/12345678/")
        assert len(hits) == 1
        assert hits[0].pmid == 12345678

    def test_pubmed_url_legacy(self) -> None:
        hits = extract_pubmed_citations("https://www.ncbi.nlm.nih.gov/pubmed/12345678")
        assert len(hits) == 1
        assert hits[0].pmid == 12345678


class TestPMIDNoFalsePositives:
    def test_bare_integer_without_prefix(self) -> None:
        """Bare ``12345678`` in prose must NOT match — would be a
        massive false-positive source (ISBNs, accession numbers, etc.)."""
        assert extract_pubmed_citations("The figure shows 12345678 records.") == []

    def test_unrelated_text(self) -> None:
        assert extract_pubmed_citations("The cat sat on the mat.") == []


class TestSourceUriPropagation:
    def test_doi(self) -> None:
        hits = extract_doi_citations("10.1145/x.y", source_uri="brief.pdf")
        assert hits[0].source_uri == "brief.pdf"

    def test_arxiv(self) -> None:
        hits = extract_arxiv_citations("arXiv:2401.12345", source_uri="brief.pdf")
        assert hits[0].source_uri == "brief.pdf"

    def test_pubmed(self) -> None:
        hits = extract_pubmed_citations("PMID:12345678", source_uri="brief.pdf")
        assert hits[0].source_uri == "brief.pdf"


class TestEmpty:
    def test_empty_text_doi(self) -> None:
        assert extract_doi_citations("") == []

    def test_empty_text_arxiv(self) -> None:
        assert extract_arxiv_citations("") == []

    def test_empty_text_pubmed(self) -> None:
        assert extract_pubmed_citations("") == []
