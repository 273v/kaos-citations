"""Unit tests for the federal-rules + USSG parser.

Pure-regex; no third-party dependencies. Covers FRCP/FRE/FRAP/FRBP/
FRCRMP/SCT plus advisory-committee notes and the Sentencing Guidelines.
"""

from __future__ import annotations

import pytest

from kaos_citations.parsers.federal_rules import (
    extract_federal_rule_citations,
    extract_ussg_citations,
)

# ---------------------------------------------------------------------------
# Federal rules — full-form extraction
# ---------------------------------------------------------------------------


class TestFederalRules:
    @pytest.mark.parametrize(
        "text,rule_set,rule,subs",
        [
            ("Fed. R. Civ. P. 56(c)(1)(A)", "FRCP", "56", ("c", "1", "A")),
            ("Fed. R. Civ. P. 12(b)(6)", "FRCP", "12", ("b", "6")),
            ("Fed. R. Crim. P. 11(c)(1)(C)", "FRCRMP", "11", ("c", "1", "C")),
            ("Fed. R. Evid. 702", "FRE", "702", ()),
            ("Fed. R. App. P. 4(a)(1)(A)", "FRAP", "4", ("a", "1", "A")),
            ("Fed. R. Bankr. P. 9011", "FRBP", "9011", ()),
            ("Sup. Ct. R. 10", "SCT", "10", ()),
        ],
    )
    def test_full_form_variants(
        self,
        text: str,
        rule_set: str,
        rule: str,
        subs: tuple[str, ...],
    ) -> None:
        cites = extract_federal_rule_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.rule_set == rule_set
        assert c.rule_number == rule
        assert c.subdivisions == subs

    @pytest.mark.parametrize(
        "shorthand,rule_set",
        [
            ("FRCP 26(a)", "FRCP"),
            ("FRE 702", "FRE"),
            ("FRAP 4(a)", "FRAP"),
            ("FRBP 9011", "FRBP"),
        ],
    )
    def test_compact_shorthand(self, shorthand: str, rule_set: str) -> None:
        cites = extract_federal_rule_citations(shorthand)
        assert len(cites) == 1
        assert cites[0].rule_set == rule_set

    def test_advisory_committee_note_with_year(self) -> None:
        text = "Fed. R. Civ. P. 26 advisory committee's note to 2015 amendment."
        cites = extract_federal_rule_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.is_advisory_committee_note is True
        assert c.amendment_year == 2015

    def test_advisory_committee_note_no_year(self) -> None:
        text = "Fed. R. Civ. P. 56 advisory committee's note states..."
        cites = extract_federal_rule_citations(text)
        assert len(cites) == 1
        assert cites[0].is_advisory_committee_note is True
        assert cites[0].amendment_year is None

    def test_multiple_in_one_string(self) -> None:
        text = "See FRCP 26(a)(2)(B); Fed. R. Crim. P. 11(c)(1)(C); FRE 702."
        cites = extract_federal_rule_citations(text)
        assert len(cites) == 3
        assert {c.rule_set for c in cites} == {"FRCP", "FRCRMP", "FRE"}

    def test_no_false_positive_on_unrelated_text(self) -> None:
        """Don't match arbitrary mention of "rule"."""
        text = "Under the rule of reason, courts assess..."
        assert extract_federal_rule_citations(text) == []

    def test_normalized_form(self) -> None:
        text = "FRCP 26(a)(2)(B)"
        cites = extract_federal_rule_citations(text)
        assert cites[0].normalized == "Fed. R. Civ. P. 26(a)(2)(B)"

    def test_case_insensitive_prefix(self) -> None:
        text = "fed. r. civ. p. 56(c)(1)(A)"
        cites = extract_federal_rule_citations(text)
        assert len(cites) == 1
        assert cites[0].rule_set == "FRCP"


# ---------------------------------------------------------------------------
# USSG
# ---------------------------------------------------------------------------


class TestUSSG:
    @pytest.mark.parametrize(
        "text,section,subs",
        [
            ("U.S.S.G. § 2D1.1(a)(1)", "2D1.1", ("a", "1")),
            ("USSG § 5K2.0", "5K2.0", ()),
            ("Sentencing Guidelines § 2B1.1(b)(1)(F)", "2B1.1", ("b", "1", "F")),
        ],
    )
    def test_ussg_variants(self, text: str, section: str, subs: tuple[str, ...]) -> None:
        cites = extract_ussg_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.section == section
        assert c.subdivisions == subs

    def test_normalized_form(self) -> None:
        cites = extract_ussg_citations("USSG § 2D1.1(a)(1)")
        assert cites[0].normalized == "U.S.S.G. § 2D1.1(a)(1)"

    def test_no_false_positive(self) -> None:
        text = "The court applied a 2-level enhancement."
        assert extract_ussg_citations(text) == []
