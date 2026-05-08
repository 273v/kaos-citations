"""Verify the vendored-data loaders return expected shapes / counts.

These tests pin the data we depend on. If the vendored JSON is
corrupted or accidentally truncated at build time, these fail loudly
before the matchers try to consume the data.
"""

from __future__ import annotations

import pytest

from kaos_citations.data._loaders import (
    case_name_abbreviation_tokens,
    court_citation_strings,
    court_id_by_citation_string,
    journal_abbreviation_set,
    law_reporter_set,
    load_case_name_abbreviations,
    load_courts,
    load_journals,
    load_law_reporters,
    load_reporters,
    load_state_abbreviations,
    reporter_all_spellings,
    reporter_canonical_set,
    reporter_variations,
    state_abbreviation_set,
)


class TestReporters:
    def test_reporters_count(self) -> None:
        assert len(load_reporters()) >= 1_200, "reporters.json should ship ~1,235 entries"

    def test_us_reporter_present(self) -> None:
        rs = load_reporters()
        assert "U.S." in rs
        us = rs["U.S."][0]
        assert us.cite_type == "federal"
        assert "United States" in us.name

    def test_variations_present(self) -> None:
        # ``U. S.`` (with space) maps to canonical ``U.S.``
        var = reporter_variations()
        assert var.get("U. S.") == "U.S."

    def test_canonical_and_variations_distinct(self) -> None:
        canonical = reporter_canonical_set()
        spellings = reporter_all_spellings()
        # Every canonical form should be in spellings
        assert canonical <= spellings
        # And spellings should include at least one variant beyond canonicals
        assert len(spellings) > len(canonical)


class TestCaseNameAbbreviations:
    def test_count(self) -> None:
        assert len(load_case_name_abbreviations()) >= 100

    @pytest.mark.parametrize(
        "abbrev",
        ["Inc.", "Corp.", "Co.", "Ass'n", "Ltd.", "Soc'y", "LLC", "P.A."],
    )
    def test_modern_and_legacy_tokens_present(self, abbrev: str) -> None:
        assert abbrev in case_name_abbreviation_tokens()


class TestStateAbbreviations:
    def test_count(self) -> None:
        # 50 state codes
        assert len(load_state_abbreviations()) == 50

    @pytest.mark.parametrize(
        "abbrev,expected_state",
        [("Cal.", "California"), ("N.Y.", "New York"), ("Fla.", "Florida")],
    )
    def test_lookup(self, abbrev: str, expected_state: str) -> None:
        assert load_state_abbreviations().get(abbrev) == expected_state

    def test_set_contains_common(self) -> None:
        s = state_abbreviation_set()
        for a in ["Cal.", "N.Y.", "Tex.", "Fla.", "Ill."]:
            assert a in s


class TestLawReporters:
    def test_count(self) -> None:
        assert len(load_law_reporters()) >= 200

    def test_usc_present(self) -> None:
        laws = load_law_reporters()
        assert "U.S.C." in laws

    def test_set_contains(self) -> None:
        s = law_reporter_set()
        assert "U.S.C." in s


class TestJournals:
    def test_count(self) -> None:
        assert len(load_journals()) >= 700

    @pytest.mark.parametrize(
        "abbrev",
        ["Yale L.J.", "Harv. L. Rev.", "Stan. L. Rev.", "Colum. L. Rev."],
    )
    def test_well_known_journals_present(self, abbrev: str) -> None:
        assert abbrev in journal_abbreviation_set()


class TestCourts:
    def test_count(self) -> None:
        assert len(load_courts()) >= 2_500

    def test_citation_strings_indexed(self) -> None:
        # 2d Cir. should resolve via the lookup
        idx = court_id_by_citation_string()
        # Find a known mapping
        assert "2d Cir." in idx or "2nd Cir." in idx or "2d. Cir." in idx

    def test_citation_strings_set_nonempty(self) -> None:
        assert len(court_citation_strings()) > 1_000
