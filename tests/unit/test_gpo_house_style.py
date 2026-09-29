"""GPO house style: the forms the Code of Federal Regulations, the U.S. Code's
notes and GovInfo print, without the Bluebook's section sign or ``Fed. Reg.``.

Examples are from the 2025 CFR (49 CFR part 1 and 7 CFR part 2 Authority
lines and delegation paragraphs) and the 2024 U.S. Code (49 U.S.C. 102
source credit), public-domain federal works.
"""

from __future__ import annotations

import pytest

from kaos_citations.extract import extract_citations
from kaos_citations.model import (
    CFRCitation,
    ExecutiveActionCitation,
    FederalRegisterCitation,
    PublicLawCitation,
    StatuteCitation,
)


def _of[T](kind: type[T], text: str) -> list[T]:
    return [c for c in extract_citations(text) if isinstance(c, kind)]


@pytest.mark.unit
class TestUscWithoutSectionSign:
    @pytest.mark.parametrize(
        ("text", "title", "section"),
        [
            ("Authority: 5 U.S.C. 301; 42 U.S.C. 300v-1(b).", "5", "301"),
            ("The Terminal Inspection Act, as amended (7 U.S.C. 166).", "7", "166"),
            ("The Honeybee Act, as amended (7 U.S.C. 281-286).", "7", "281-286"),
            ("functions vested in the Secretary by 49 U.S.C. 40113(a)", "49", "40113(a)"),
        ],
    )
    def test_reads_the_first_citation(self, text: str, title: str, section: str) -> None:
        first = _of(StatuteCitation, text)[0]
        assert (first.title, first.code, first.section) == (title, "U.S.C.", section)
        assert first.normalized == f"{title} U.S.C. § {section}"

    def test_reads_every_citation_in_an_authority_line(self) -> None:
        cites = _of(StatuteCitation, "Authority: 5 U.S.C. 301; 42 U.S.C. 300v-1(b).")
        assert [(c.title, c.section) for c in cites] == [("5", "301"), ("42", "300v-1(b)")]

    def test_bluebook_form_is_unchanged(self) -> None:
        [c] = _of(StatuteCitation, "42 U.S.C. § 1983")
        assert (c.title, c.section, c.normalized) == ("42", "1983", "42 U.S.C. § 1983")

    @pytest.mark.parametrize(
        "text",
        ["49 U.S.C. Subtitle VII (Aviation Programs)", "5 U.S.C. App.", "title 23, U.S.C."],
    )
    def test_a_division_or_appendix_is_not_a_section(self, text: str) -> None:
        assert _of(StatuteCitation, text) == []


@pytest.mark.unit
class TestFederalRegisterAbbreviation:
    def test_reads_fr(self) -> None:
        [c] = _of(FederalRegisterCitation, "81 FR 19819, Apr. 5, 2016, unless otherwise noted.")
        assert (c.volume, c.page, c.normalized) == (81, 19819, "81 Fed. Reg. 19,819")

    def test_fed_reg_is_unchanged(self) -> None:
        [c] = _of(FederalRegisterCitation, "88 Fed. Reg. 12,345 (Mar. 1, 2023)")
        assert (c.volume, c.page) == (88, 12345)

    @pytest.mark.parametrize(
        "text",
        [
            "3 CFR, 1978 Comp., p. 266",  # CFR is not FR
            "the 20 fr 30 ratio",  # lower case is not the abbreviation
        ],
    )
    def test_rejects_look_alikes(self, text: str) -> None:
        assert _of(FederalRegisterCitation, text) == []


@pytest.mark.unit
class TestPublicLawSourceCredit:
    def test_statutes_at_large_after_the_enactment_date(self) -> None:
        text = "Pub. L. 97-449, §1(b), Jan. 12, 1983, 96 Stat. 2414; Pub. L. 98-557"
        first, second = _of(PublicLawCitation, text)
        assert (first.public_law_number, first.stat_volume, first.stat_page) == (
            "97-449",
            96,
            2414,
        )
        assert second.public_law_number == "98-557"


@pytest.mark.unit
class TestMisprintedPublicLaw:
    def test_an_impossible_congress_is_skipped_not_raised(self) -> None:
        # 49 CFR 1.85 prints "Pub. L. 889-574" for Pub. L. 89-574.
        text = "(Pub. L. 889-574, 80 Stat. 766); and Pub. L. 89-670"
        laws = _of(PublicLawCitation, text)
        assert [c.public_law_number for c in laws] == ["89-670"]


@pytest.mark.unit
class TestSectionLists:
    def test_usc_list_items_are_citations_in_the_same_title(self) -> None:
        text = "5 U.S.C. 301; 7 U.S.C. 61, 87e, 228, 499o, 608c(9), 1622(g)."
        cites = _of(StatuteCitation, text)
        assert [(c.title, c.section) for c in cites] == [
            ("5", "301"),
            ("7", "61"),
            ("7", "87e"),
            ("7", "228"),
            ("7", "499o"),
            ("7", "608c(9)"),
            ("7", "1622(g)"),
        ]
        assert [text[c.span[0] : c.span[1]] for c in cites][2:4] == ["87e", "228"]

    def test_a_list_stops_at_the_next_citations_title(self) -> None:
        cites = _of(StatuteCitation, "42 U.S.C. 1983, 28 U.S.C. 1331")
        assert [(c.title, c.section) for c in cites] == [("42", "1983"), ("28", "1331")]

    def test_cfr_list(self) -> None:
        cites = _of(CFRCitation, "Authority: 7 CFR 2.35, 2.41.")
        assert [(c.title, c.section) for c in cites] == [(7, "2.35"), (7, "2.41")]

    def test_a_comma_followed_by_words_is_not_a_list(self) -> None:
        cites = _of(StatuteCitation, "7 U.S.C. 166, as amended, and the Act")
        assert [c.section for c in cites] == ["166"]


@pytest.mark.unit
class TestPublicLawAsTheCodesNotesWriteIt:
    def test_en_dash_and_a_pinpoint_through_division_and_title(self) -> None:
        text = "2015\u2014Pub. L. 114\u201394, div. A, title VIII, \u00a78001(b), Dec. 4, 2015"
        [c] = _of(PublicLawCitation, text)
        assert (c.public_law_number, c.congress, c.section) == ("114-94", 114, "8001(b)")


@pytest.mark.unit
class TestTheCodesNotesForms:
    def test_ex_ord_and_dotted_fr(self) -> None:
        text = "Ex. Ord. No. 13330, Feb. 24, 2004, 69 F.R. 9185, provided:"
        [eo] = _of(ExecutiveActionCitation, text)
        assert eo.number == "13330"
        [fr] = _of(FederalRegisterCitation, text)
        assert (fr.volume, fr.page) == (69, 9185)

    def test_plural_cfr_parts(self) -> None:
        cites = _of(CFRCitation, "controlled under 49 CFR parts 15 and 1520. No part")
        assert [(c.title, c.section) for c in cites] == [(49, "15"), (49, "1520")]
        # "through" gives the range's two ends; the model has no range field.
        cites = _of(CFRCitation, "(36 CFR parts 1220 through 1299; 44 U.S.C. 3301)")
        assert [c.section for c in cites] == ["1220", "1299"]

    def test_cfr_in_prose_is_not_a_citation(self) -> None:
        assert _of(CFRCitation, "see the List of CFR Sections Affected") == []
