"""Compact tests for the Phase 2 / 3 / 4 parser families.

Pure-regex; no third-party deps. Each test class targets one parser
file and validates the canonical-form parse path. We're not exhaustively
re-validating Bluebook formatting — just confirming each citation kind
extracts without false positives on common forms.
"""

from __future__ import annotations

import pytest

from kaos_citations.parsers.accounting import (
    extract_aicpa_citations,
    extract_asc_citations,
    extract_asu_citations,
    extract_fasab_citations,
    extract_gasb_citations,
    extract_government_audit_citations,
    extract_iaasb_citations,
    extract_iesba_citations,
    extract_ifrs_citations,
    extract_legacy_fasb_citations,
    extract_naic_accounting_citations,
    extract_pcaob_citations,
    extract_sustainability_citations,
)
from kaos_citations.parsers.agency import (
    extract_agency_adjudication_citations,
    extract_agency_manual_citations,
    extract_bar_ethics_citations,
    extract_legal_opinion_citations,
)
from kaos_citations.parsers.sec import (
    extract_basel_citations,
    extract_cfpb_citations,
    extract_cftc_citations,
    extract_exchange_rule_citations,
    extract_fdic_citations,
    extract_fed_reserve_letter_citations,
    extract_fed_reserve_regulation_citations,
    extract_ffiec_citations,
    extract_finra_disciplinary_citations,
    extract_finra_notice_citations,
    extract_finra_rule_citations,
    extract_international_finance_citations,
    extract_naic_citations,
    extract_ncua_citations,
    extract_occ_citations,
    extract_sec_filing_citations,
    extract_sec_regulation_citations,
    extract_sec_release_citations,
    extract_sec_staff_citations,
)

# ---------------------------------------------------------------------------
# Phase 2 — agency, manuals, AG/OLC, bar ethics
# ---------------------------------------------------------------------------


class TestAgencyAdjudications:
    @pytest.mark.parametrize(
        "text,agency,volume,page",
        [
            ("311 NLRB 893 (1993)", "NLRB", 311, 893),
            ("13 E.A.D. 100 (EAB 2006)", "EPA_EAB", 13, 100),
            ("162 F.T.C. 1 (2016)", "FTC", 162, 1),
            ("35 FCC Rcd 12,789 (2020)", "FCC", 35, 12789),
            ("27 I. & N. Dec. 316 (A.G. 2018)", "BIA", 27, 316),
        ],
    )
    def test_reporter_form(self, text: str, agency: str, volume: int, page: int) -> None:
        cites = extract_agency_adjudication_citations(text)
        assert len(cites) == 1
        assert cites[0].agency == agency
        assert cites[0].volume == volume
        assert cites[0].page == page

    def test_nlrb_slip_form(self) -> None:
        cites = extract_agency_adjudication_citations("370 N.L.R.B. No. 12 (Mar. 1, 2020)")
        assert len(cites) == 1
        assert cites[0].slip_number == "12"

    def test_ferc_paragraph(self) -> None:
        cites = extract_agency_adjudication_citations("162 FERC ¶ 61,123 (2018)")
        assert len(cites) == 1
        assert cites[0].agency == "FERC"
        assert cites[0].paragraph == 61123

    def test_ptab(self) -> None:
        cites = extract_agency_adjudication_citations("Appeal 2020-002345 (PTAB 2021)")
        assert len(cites) == 1
        assert cites[0].agency == "PTAB"
        assert cites[0].year == 2021


class TestAgencyManuals:
    @pytest.mark.parametrize(
        "text,manual,section",
        [
            ("MPEP § 2106.04(a)", "MPEP", "2106.04(a)"),
            ("Manual of Patent Examining Procedure § 2106", "MPEP", "2106"),
            ("TMEP § 1202.02", "TMEP", "1202.02"),
            ("POMS § DI 25025.001", "POMS", "DI 25025.001"),
        ],
    )
    def test_manuals(self, text: str, manual: str, section: str) -> None:
        cites = extract_agency_manual_citations(text)
        assert len(cites) == 1
        assert cites[0].manual_id == manual
        assert cites[0].section == section


class TestLegalOpinions:
    def test_ag(self) -> None:
        cites = extract_legal_opinion_citations("42 Op. Att'y Gen. 5 (1981)")
        assert len(cites) == 1
        assert cites[0].authority == "AG"
        assert cites[0].volume == 42
        assert cites[0].page == 5
        assert cites[0].year == 1981

    def test_olc(self) -> None:
        cites = extract_legal_opinion_citations("38 Op. O.L.C. 1 (2014)")
        assert len(cites) == 1
        assert cites[0].authority == "OLC"


class TestBarEthics:
    def test_aba(self) -> None:
        cites = extract_bar_ethics_citations(
            "ABA Comm. on Ethics & Pro. Resp., Formal Op. 491 (2020)"
        )
        assert cites
        assert cites[0].opinion_number == "491"
        assert cites[0].year == 2020

    def test_state(self) -> None:
        cites = extract_bar_ethics_citations(
            "N.Y. State Bar Ass'n Comm. on Pro. Ethics, Op. 1234 (2023)"
        )
        assert cites
        assert cites[0].opinion_number == "1234"


# ---------------------------------------------------------------------------
# Phase 3 — SEC, FINRA, exchange, banking, intl
# ---------------------------------------------------------------------------


class TestSECFilings:
    @pytest.mark.parametrize(
        "text,form",
        [
            ("Form 10-K (Feb. 14, 2024)", "10-K"),
            ("Form 8-K (Mar. 14, 2024)", "8-K"),
            ("Schedule 13D (Mar. 1, 2024)", "13D"),
            ("Form ADV (Mar. 31, 2024)", "ADV"),
            ("Form S-1 (Jan. 5, 2024)", "S-1"),
        ],
    )
    def test_filing_forms(self, text: str, form: str) -> None:
        cites = extract_sec_filing_citations(text)
        assert len(cites) == 1
        assert cites[0].form == form


class TestSECReleases:
    @pytest.mark.parametrize(
        "text,act,num",
        [
            ("Securities Act Release No. 33-10777", "33", "33-10777"),
            ("Exchange Act Release No. 34-94168", "34", "34-94168"),
            ("Investment Company Act Release No. IC-34123", "IC", "IC-34123"),
            ("Investment Advisers Act Release No. IA-6500", "IA", "IA-6500"),
        ],
    )
    def test_releases(self, text: str, act: str, num: str) -> None:
        cites = extract_sec_release_citations(text)
        assert len(cites) == 1
        assert cites[0].act == act
        assert cites[0].release_number == num


class TestSECStaff:
    def test_sab(self) -> None:
        cites = extract_sec_staff_citations("Staff Accounting Bulletin No. 121")
        assert cites and cites[0].doc_kind == "sab" and cites[0].number == "121"

    def test_slb(self) -> None:
        cites = extract_sec_staff_citations("Staff Legal Bulletin No. 14L")
        assert cites and cites[0].doc_kind == "slb" and cites[0].number == "14L"

    def test_cdi(self) -> None:
        cites = extract_sec_staff_citations("C&DI Question 234.01")
        assert cites and cites[0].doc_kind == "cdi" and cites[0].question == "234.01"

    def test_no_action(self) -> None:
        cites = extract_sec_staff_citations("SEC No-Action Letter to Acme Corp. (Mar. 1, 2022)")
        assert cites and cites[0].doc_kind == "no_action"


class TestSECRegulations:
    @pytest.mark.parametrize(
        "text,reg",
        [
            ("Reg. S-X § 210.1-01", "S-X"),
            ("Reg. S-K Item 303", "S-K"),
            ("Reg. G", "G"),
        ],
    )
    def test_named_regulations(self, text: str, reg: str) -> None:
        cites = extract_sec_regulation_citations(text)
        assert cites and cites[0].regulation == reg


class TestFINRAAndExchange:
    def test_finra_rule(self) -> None:
        cites = extract_finra_rule_citations("FINRA Rule 2111(a)")
        assert cites and cites[0].rule_number == "2111"
        assert cites[0].subdivisions == ("a",)

    def test_finra_notice(self) -> None:
        cites = extract_finra_notice_citations("FINRA Regulatory Notice 23-12")
        assert cites and cites[0].notice_number == "23-12"

    def test_finra_disciplinary(self) -> None:
        cites = extract_finra_disciplinary_citations(
            "FINRA Disciplinary Proceeding No. 2020012345601 (NAC)"
        )
        assert cites and cites[0].decision_authority == "NAC"

    @pytest.mark.parametrize(
        "text,exchange,rule",
        [
            ("MSRB Rule G-15", "MSRB", "G-15"),
            ("NYSE Rule 123", "NYSE", "123"),
            ("Nasdaq Rule 5605(d)", "Nasdaq", "5605"),
            ("Cboe Rule 4.1", "Cboe", "4.1"),
        ],
    )
    def test_exchange(self, text: str, exchange: str, rule: str) -> None:
        cites = extract_exchange_rule_citations(text)
        assert cites
        assert cites[0].exchange == exchange
        assert cites[0].rule_number == rule


class TestBanking:
    def test_fed_reserve_reg(self) -> None:
        cites = extract_fed_reserve_regulation_citations("Reg. Z, 12 C.F.R. pt. 226")
        assert cites
        assert cites[0].reg_letter == "Z"
        assert cites[0].cfr_title == 12

    def test_fed_reserve_letters(self) -> None:
        cites = extract_fed_reserve_letter_citations("SR 23-04 (Mar. 1, 2023)")
        assert cites and cites[0].letter_kind == "SR"

    def test_fdic(self) -> None:
        cites = extract_fdic_citations("FIL-12-2023 (Mar. 1, 2023)")
        assert cites and cites[0].number == "12-2023"

    def test_occ_bulletin(self) -> None:
        cites = extract_occ_citations("OCC Bulletin 2023-10")
        assert cites and cites[0].doc_kind == "BULLETIN"

    def test_cfpb_bulletin(self) -> None:
        cites = extract_cfpb_citations("CFPB Bulletin 2023-01")
        assert cites and cites[0].doc_kind == "BULLETIN"

    def test_cfpb_compliance_bulletin_distinct(self) -> None:
        cites = extract_cfpb_citations("CFPB Compliance Bulletin 2023-01")
        assert cites and cites[0].doc_kind == "COMPLIANCE_BULLETIN"

    def test_ncua(self) -> None:
        cites = extract_ncua_citations("NCUA Letter to Credit Unions 23-01 (Jan. 5, 2023)")
        assert cites and cites[0].number == "23-01"


class TestBaselCFTCNAICIntl:
    def test_basel(self) -> None:
        cites = extract_basel_citations("BCBS d544")
        assert cites and cites[0].document_id == "d544"

    def test_cftc(self) -> None:
        cites = extract_cftc_citations("CFTC Interp. Ltr. 23-12")
        assert cites and cites[0].doc_kind == "INTERP_LETTER"

    def test_naic(self) -> None:
        cites = extract_naic_citations("NAIC Bulletin 2023-01")
        assert cites and cites[0].doc_kind == "BULLETIN"

    def test_fatf(self) -> None:
        cites = extract_international_finance_citations("FATF Recommendation 10")
        assert cites and cites[0].body == "FATF"

    def test_iosco(self) -> None:
        cites = extract_international_finance_citations("IOSCO Final Report FR 04-2023")
        assert cites and cites[0].body == "IOSCO"

    def test_ffiec(self) -> None:
        cites = extract_ffiec_citations("FFIEC 031, Schedule RC-N, item 5")
        assert cites and cites[0].form_number == "031"


# ---------------------------------------------------------------------------
# Phase 4 — accounting
# ---------------------------------------------------------------------------


class TestASC:
    @pytest.mark.parametrize(
        "text,topic,subtopic,section,paragraph",
        [
            ("FASB ASC 805-10-25-1", 805, 10, 25, "1"),
            ("ASC 606", 606, None, None, None),
            ("ASC 740-10", 740, 10, None, None),
            ("FASB ASC 350-30-25-3", 350, 30, 25, "3"),
        ],
    )
    def test_asc_levels(
        self,
        text: str,
        topic: int,
        subtopic: int | None,
        section: int | None,
        paragraph: str | None,
    ) -> None:
        cites = extract_asc_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.topic == topic
        assert c.subtopic == subtopic
        assert c.section == section
        assert c.paragraph == paragraph


class TestASU:
    def test_with_title(self) -> None:
        cites = extract_asu_citations("ASU 2023-09, Improvements to Income Tax Disclosures.")
        assert cites and cites[0].year == 2023 and cites[0].sequence == 9
        assert cites[0].title == "Improvements to Income Tax Disclosures"

    def test_without_title(self) -> None:
        cites = extract_asu_citations("ASU 2014-09.")
        assert cites and cites[0].sequence == 9


class TestLegacyFASB:
    @pytest.mark.parametrize(
        "text,kind,num",
        [
            ("FAS 142", "FAS", "142"),
            ("FIN 48", "FIN", "48"),
            ("FSP FAS 142-3", "FSP", "142-3"),
            ("EITF Issue 02-13", "EITF", "02-13"),
            ("CON 8", "CON", "8"),
            ("APB Op. 18", "APB", "18"),
            ("ARB 43", "ARB", "43"),
        ],
    )
    def test_legacy(self, text: str, kind: str, num: str) -> None:
        cites = extract_legacy_fasb_citations(text)
        assert cites and cites[0].statement_kind == kind
        assert cites[0].number == num


class TestPCAOB:
    @pytest.mark.parametrize(
        "text,kind,num",
        [
            ("PCAOB AS 2401", "AS", "2401"),
            ("PCAOB Staff Audit Practice Alert No. 12", "PRACTICE_ALERT", "12"),
            ("PCAOB Release No. 2023-001", "RELEASE", "2023-001"),
            ("PCAOB Rule 3502", "RULE", "3502"),
        ],
    )
    def test_pcaob(self, text: str, kind: str, num: str) -> None:
        cites = extract_pcaob_citations(text)
        assert cites and cites[0].doc_kind == kind and cites[0].number == num


class TestAICPA:
    @pytest.mark.parametrize(
        "text,kind,num",
        [
            ("AICPA SAS 145", "SAS", "145"),
            ("AICPA SSAE 18", "SSAE", "18"),
            ("AICPA SSARS 25", "SSARS", "25"),
            ("AICPA SOP 03-1", "SOP", "03-1"),
            ("AICPA TQA 1300.10", "TQA", "1300.10"),
        ],
    )
    def test_aicpa(self, text: str, kind: str, num: str) -> None:
        cites = extract_aicpa_citations(text)
        assert cites and cites[0].doc_kind == kind and cites[0].number == num

    def test_code(self) -> None:
        cites = extract_aicpa_citations("AICPA Code of Pro. Conduct, ET § 1.295")
        assert cites and cites[0].doc_kind == "CODE"
        assert cites[0].section == "1.295"


class TestIFRS:
    @pytest.mark.parametrize(
        "text,kind,num,paragraph",
        [
            ("IFRS 15", "IFRS", "15", None),
            ("IFRS 15.31", "IFRS", "15", "31"),
            ("IAS 36", "IAS", "36", None),
            ("IAS 36.12", "IAS", "36", "12"),
            ("IFRIC 23", "IFRIC", "23", None),
            ("SIC-7", "SIC", "7", None),
            ("IFRS Practice Statement 1", "PS", "1", None),
        ],
    )
    def test_ifrs(self, text: str, kind: str, num: str, paragraph: str | None) -> None:
        cites = extract_ifrs_citations(text)
        assert cites and cites[0].standard_kind == kind
        assert cites[0].number == num
        assert cites[0].paragraph == paragraph

    def test_conceptual_framework(self) -> None:
        cites = extract_ifrs_citations("IFRS Conceptual Framework ¶ 4.5")
        assert cites and cites[0].standard_kind == "CF"
        assert cites[0].paragraph == "4.5"


class TestIAASBIESBA:
    def test_isa(self) -> None:
        cites = extract_iaasb_citations("ISA 315 (Revised 2019)")
        assert cites and cites[0].standard_kind == "ISA" and cites[0].number == "315"

    def test_isae(self) -> None:
        cites = extract_iaasb_citations("ISAE 3000 (Revised)")
        assert cites and cites[0].standard_kind == "ISAE"

    def test_iesba(self) -> None:
        cites = extract_iesba_citations("IESBA Code § 290")
        assert cites and cites[0].section == "290"


class TestGASBFASAB:
    def test_gasb_statement(self) -> None:
        cites = extract_gasb_citations("GASB Statement No. 87, ¶ 12")
        assert cites and cites[0].doc_kind == "STATEMENT"
        assert cites[0].number == "87"
        assert cites[0].paragraph == "12"

    def test_gasb_implementation_guide(self) -> None:
        cites = extract_gasb_citations("GASB Implementation Guide 2019-1")
        assert cites and cites[0].doc_kind == "IMPLEMENTATION_GUIDE"

    def test_fasab(self) -> None:
        cites = extract_fasab_citations("FASAB SFFAS 56")
        assert cites and cites[0].doc_kind == "SFFAS" and cites[0].number == "56"


class TestGovernmentAudit:
    def test_omb_circular(self) -> None:
        cites = extract_government_audit_citations("OMB Circular A-133")
        assert cites and cites[0].doc_kind == "OMB_CIRCULAR"
        assert cites[0].document_id == "A-133"

    def test_yellow_book(self) -> None:
        cites = extract_government_audit_citations("GAO Yellow Book (2018 Rev.)")
        assert cites and cites[0].doc_kind == "GAO_YELLOWBOOK"
        assert cites[0].revision_year == 2018


class TestNAICAccounting:
    def test_ssap(self) -> None:
        cites = extract_naic_accounting_citations("NAIC SSAP No. 5R, Liabilities, Contingencies")
        assert cites and cites[0].ssap_number == "5R"


class TestSustainability:
    def test_gri(self) -> None:
        cites = extract_sustainability_citations("GRI 305: Emissions 2016")
        assert cites and cites[0].framework == "GRI"
        assert cites[0].standard_id == "305"

    def test_sasb(self) -> None:
        cites = extract_sustainability_citations("SASB FB-FR-110a.1")
        assert cites and cites[0].framework == "SASB"

    def test_tcfd(self) -> None:
        cites = extract_sustainability_citations("TCFD Recommended Disclosures (June 2017)")
        assert cites and cites[0].framework == "TCFD"

    def test_issb(self) -> None:
        cites = extract_sustainability_citations("IFRS S1.10")
        assert cites and cites[0].framework == "ISSB"

    def test_esrs(self) -> None:
        cites = extract_sustainability_citations("ESRS 2")
        assert cites and cites[0].framework == "ESRS"
