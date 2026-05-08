"""Unit tests for the Treasury Reg + IRS guidance + Executive parser.

Pure-regex; no third-party dependencies. Covers Bluebook R14.5 (tax)
and R14.7 (executive materials).
"""

from __future__ import annotations

import pytest

from kaos_citations.parsers.regulatory import (
    extract_executive_action_citations,
    extract_irs_guidance_citations,
    extract_treasury_regulation_citations,
)


class TestTreasuryRegulations:
    @pytest.mark.parametrize(
        "text,status,section",
        [
            ("Treas. Reg. § 1.501(c)(3)-1(d)(2)", "final", "1.501(c)(3)-1(d)(2)"),
            ("Prop. Treas. Reg. § 1.482-7", "proposed", "1.482-7"),
            ("Temp. Treas. Reg. § 1.163-9T(b)", "temporary", "1.163-9T(b)"),
            ("Treasury Regulations § 1.61-1", "final", "1.61-1"),
        ],
    )
    def test_status_variants(self, text: str, status: str, section: str) -> None:
        cites = extract_treasury_regulation_citations(text)
        assert len(cites) == 1
        assert cites[0].status == status
        assert cites[0].section == section

    def test_normalized_form(self) -> None:
        cites = extract_treasury_regulation_citations("Treasury Reg. § 1.61-1")
        assert cites[0].normalized == "Treas. Reg. § 1.61-1"


class TestIRSGuidance:
    @pytest.mark.parametrize(
        "text,kind,number,year",
        [
            ("Rev. Rul. 2019-11", "rev_rul", "2019-11", 2019),
            ("Rev. Proc. 2023-12", "rev_proc", "2023-12", 2023),
            ("Notice 2014-21", "notice", "2014-21", 2014),
            ("Announcement 2024-3", "announcement", "2024-3", 2024),
            ("Priv. Ltr. Rul. 2023-12-345", "plr", "2023-12-345", 2023),
            ("PLR 200518009", "plr", "200518009", None),
            ("T.A.M. 200518009", "tam", "200518009", None),
            ("G.C.M. 39,914", "gcm", "39,914", None),
            ("T.D. 9930", "td", "9930", None),
        ],
    )
    def test_irs_kinds(
        self,
        text: str,
        kind: str,
        number: str,
        year: int | None,
    ) -> None:
        cites = extract_irs_guidance_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.guidance_kind == kind
        assert c.number == number
        assert c.year == year

    def test_irm_section(self) -> None:
        cites = extract_irs_guidance_citations("I.R.M. § 4.10.7.2")
        assert len(cites) == 1
        c = cites[0]
        assert c.guidance_kind == "irm"
        assert c.number == "4.10.7.2"
        assert c.normalized == "I.R.M. § 4.10.7.2"

    def test_internal_revenue_manual_long_form(self) -> None:
        cites = extract_irs_guidance_citations("Internal Revenue Manual § 5.1.7")
        assert len(cites) == 1
        assert cites[0].guidance_kind == "irm"
        assert cites[0].number == "5.1.7"

    def test_no_overlapping_dupes(self) -> None:
        # "Rev. Proc." should not also match the shorter "Rev." prefix
        # for "Rev. Rul." etc.
        cites = extract_irs_guidance_citations("Rev. Proc. 2023-12")
        assert len(cites) == 1
        assert cites[0].guidance_kind == "rev_proc"

    def test_multiple_in_one_string(self) -> None:
        text = "See Rev. Rul. 2019-11; Notice 2014-21; T.D. 9930."
        cites = extract_irs_guidance_citations(text)
        kinds = [c.guidance_kind for c in cites]
        assert "rev_rul" in kinds
        assert "notice" in kinds
        assert "td" in kinds


class TestExecutiveActions:
    @pytest.mark.parametrize(
        "text,action_kind,number",
        [
            ("Exec. Order No. 14,028", "executive_order", "14,028"),
            ("E.O. 13769", "executive_order", "13769"),
            ("Executive Order 14028", "executive_order", "14028"),
            ("Proclamation No. 10345", "proclamation", "10345"),
            ("Presidential Determination No. 2023-04", "determination", "2023-04"),
        ],
    )
    def test_executive_kinds(
        self,
        text: str,
        action_kind: str,
        number: str,
    ) -> None:
        cites = extract_executive_action_citations(text)
        assert len(cites) >= 1
        # Find the matching citation (de-duplication may have collapsed)
        matching = [c for c in cites if c.action_kind == action_kind]
        assert matching, f"no {action_kind} cite found in {cites}"
        assert matching[0].number == number

    def test_memorandum_with_title(self) -> None:
        text = "Presidential Memorandum on Combating Trafficking in Persons."
        cites = extract_executive_action_citations(text)
        memos = [c for c in cites if c.action_kind == "memorandum"]
        assert len(memos) == 1
        assert memos[0].title == "Combating Trafficking in Persons"

    def test_eo_does_not_match_substring(self) -> None:
        """``E.O. 13769`` keeps all five digits; we used to drop ``69``."""
        cites = extract_executive_action_citations("Issued E.O. 13769 in 2017.")
        eo = [c for c in cites if c.action_kind == "executive_order"]
        assert eo and eo[0].number == "13769"
