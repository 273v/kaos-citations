"""Unit tests for the legislative + Public Law + Restatement + Uniform Act parser.

Pure-regex; no third-party dependencies. Covers Bluebook R12-R15.
"""

from __future__ import annotations

import pytest

from kaos_citations.parsers.legislative import (
    extract_legislative_citations,
    extract_public_law_citations,
    extract_restatement_citations,
    extract_uniform_act_citations,
)


class TestPublicLaws:
    def test_full_form_with_section_and_stat(self) -> None:
        cites = extract_public_law_citations("Pub. L. No. 111-148, § 1501, 124 Stat. 119 (2010).")
        assert len(cites) == 1
        c = cites[0]
        assert c.public_law_number == "111-148"
        assert c.congress == 111
        assert c.section == "1501"
        assert c.stat_volume == 124
        assert c.stat_page == 119

    def test_short_form_only(self) -> None:
        cites = extract_public_law_citations("Pub. L. 116-136")
        assert len(cites) == 1
        c = cites[0]
        assert c.public_law_number == "116-136"
        assert c.congress == 116
        assert c.stat_volume is None
        assert c.section is None

    def test_full_phrase(self) -> None:
        cites = extract_public_law_citations("Public Law 117-2, § 9001")
        assert len(cites) == 1
        assert cites[0].public_law_number == "117-2"


class TestBills:
    @pytest.mark.parametrize(
        "text,doc_kind,number,congress",
        [
            ("H.R. 1 (115th Cong. 2017)", "house_bill", "1", 115),
            ("S. 1234 (116th Cong.)", "senate_bill", "1234", 116),
            ("H.J. Res. 5", "house_joint_resolution", "5", None),
            ("S.J. Res. 7", "senate_joint_resolution", "7", None),
            ("H. Con. Res. 12", "house_concurrent_resolution", "12", None),
            ("S. Con. Res. 8", "senate_concurrent_resolution", "8", None),
            ("H. Res. 15", "house_resolution", "15", None),
            ("S. Res. 9", "senate_resolution", "9", None),
        ],
    )
    def test_bill_kinds(
        self,
        text: str,
        doc_kind: str,
        number: str,
        congress: int | None,
    ) -> None:
        cites = extract_legislative_citations(text)
        # Find the matching cite (resolution forms may overlap with bill prefixes)
        matching = [c for c in cites if c.doc_kind == doc_kind]
        assert matching, f"no {doc_kind} extracted from {text!r}"
        c = matching[0]
        assert c.number == number
        assert c.congress == congress

    def test_no_false_positive_inside_reporter(self) -> None:
        """``U.S. 436`` should NOT be extracted as ``S. 436`` (senate bill)."""
        text = "Miranda v. Arizona, 384 U.S. 436 (1966)."
        cites = extract_legislative_citations(text)
        assert all(c.doc_kind != "senate_bill" for c in cites)


class TestReports:
    @pytest.mark.parametrize(
        "text,doc_kind,number",
        [
            ("H.R. Rep. No. 117-89", "house_report", "117-89"),
            ("S. Rep. No. 116-141", "senate_report", "116-141"),
            ("H.R. Conf. Rep. No. 115-466", "conference_report", "115-466"),
            ("H. Doc. No. 116-72", "house_document", "116-72"),
            ("S. Doc. No. 117-3", "senate_document", "117-3"),
        ],
    )
    def test_report_kinds(self, text: str, doc_kind: str, number: str) -> None:
        cites = extract_legislative_citations(text)
        matching = [c for c in cites if c.doc_kind == doc_kind]
        assert matching, f"no {doc_kind} from {text!r}; got {[c.doc_kind for c in cites]}"
        assert matching[0].number == number


class TestCongressionalRecord:
    @pytest.mark.parametrize(
        "text,chamber,page",
        [
            ("168 Cong. Rec. H1234", "H", 1234),
            ("150 Cong. Rec. S1234", "S", 1234),
            ("150 Cong. Rec. E1234", "E", 1234),
            ("150 Cong. Rec. D5", "D", 5),
        ],
    )
    def test_daily_edition(self, text: str, chamber: str, page: int) -> None:
        cites = extract_legislative_citations(text)
        cong = [c for c in cites if c.doc_kind == "cong_record_daily"]
        assert cong
        assert cong[0].chamber_page_prefix == chamber
        assert cong[0].page == page

    def test_bound_edition(self) -> None:
        cites = extract_legislative_citations("150 Cong. Rec. 12,345")
        cong = [c for c in cites if c.doc_kind == "cong_record_bound"]
        assert cong
        assert cong[0].page == 12345


class TestRestatements:
    @pytest.mark.parametrize(
        "text,series,subject,section",
        [
            ("Restatement (Second) of Torts § 402A", "Second", "Torts", "402A"),
            ("Restatement (Third) of Agency § 1.01", "Third", "Agency", "1.01"),
            ("Restatement (First) of Contracts § 90", "First", "Contracts", "90"),
            ("Restatement (2d) of Property § 6.5", "Second", "Property", "6.5"),
        ],
    )
    def test_restatements(self, text: str, series: str, subject: str, section: str) -> None:
        cites = extract_restatement_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.series == series
        assert c.subject == subject
        assert c.section == section

    def test_with_comment(self) -> None:
        cites = extract_restatement_citations("Restatement (Third) of Agency § 1.01 cmt. b")
        assert len(cites) == 1
        c = cites[0]
        assert c.comment_letter == "b"

    def test_with_illustration(self) -> None:
        cites = extract_restatement_citations("Restatement (Third) of Property § 6.5 illus. 3")
        assert len(cites) == 1
        assert cites[0].illustration_number == 3


class TestUniformActs:
    @pytest.mark.parametrize(
        "text,short,section",
        [
            ("U.C.C. § 2-207", "U.C.C.", "2-207"),
            ("U.P.C. § 2-101", "U.P.C.", "2-101"),
            ("M.P.C. § 2.02", "M.P.C.", "2.02"),
            ("U.T.C. § 105", "U.T.C.", "105"),
            ("U.E.T.A. § 7", "U.E.T.A.", "7"),
        ],
    )
    def test_uniform_acts(self, text: str, short: str, section: str) -> None:
        cites = extract_uniform_act_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.act_short == short
        assert c.section == section
