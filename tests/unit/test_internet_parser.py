"""Unit tests for the internet + archive citation parser (Bluebook R18)."""

from __future__ import annotations

import pytest

from kaos_citations.parsers.internet import (
    extract_archive_citations,
    extract_internet_citations,
)


class TestInternetCitations:
    @pytest.mark.parametrize(
        "text,expected_url",
        [
            ("Available at https://www.example.com/foo.", "https://www.example.com/foo"),
            ("Visit http://example.com/path?q=1 for details.", "http://example.com/path?q=1"),
            ("https://www.gov/x", "https://www.gov/x"),
        ],
    )
    def test_url_extraction(self, text: str, expected_url: str) -> None:
        cites = extract_internet_citations(text)
        assert len(cites) == 1
        assert cites[0].url == expected_url

    def test_last_visited_tail(self) -> None:
        text = "https://example.com/policy (last visited Mar. 5, 2024)."
        cites = extract_internet_citations(text)
        assert len(cites) == 1
        assert cites[0].last_visited == "Mar. 5, 2024"

    def test_iso_last_visited(self) -> None:
        text = "See https://example.com (last visited 2024-03-05)."
        cites = extract_internet_citations(text)
        assert len(cites) == 1
        assert cites[0].last_visited == "2024-03-05"

    def test_multiple_urls(self) -> None:
        text = "URLs: https://a.com/foo, https://b.com/bar."
        cites = extract_internet_citations(text)
        assert len(cites) == 2
        assert {c.url for c in cites} == {"https://a.com/foo", "https://b.com/bar"}

    def test_archive_url_skipped(self) -> None:
        """Archive URLs should NOT also surface as plain InternetCitation."""
        text = "https://web.archive.org/web/20230401120000/https://example.com/old"
        cites = extract_internet_citations(text)
        assert cites == []

    def test_trailing_period_trimmed(self) -> None:
        cites = extract_internet_citations("See https://example.com/foo.")
        assert cites[0].url == "https://example.com/foo"

    def test_no_false_positive_on_non_url(self) -> None:
        assert extract_internet_citations("This text has no URL.") == []


class TestArchiveCitations:
    def test_wayback_machine(self) -> None:
        text = "https://web.archive.org/web/20230401120000/https://example.com/old-page"
        cites = extract_archive_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert "web.archive.org" in c.archive_url
        assert c.archive_id == "20230401120000"
        assert c.original_url == "https://example.com/old-page"
        assert c.archive_date == "2023-04-01"

    def test_perma_cc(self) -> None:
        text = "https://perma.cc/ABCD-1234"
        cites = extract_archive_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.archive_url == "https://perma.cc/ABCD-1234"
        assert c.archive_id == "ABCD-1234"
        assert c.original_url is None

    def test_non_archive_url_skipped(self) -> None:
        cites = extract_archive_citations("https://example.com/foo")
        assert cites == []
