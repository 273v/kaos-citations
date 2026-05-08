"""Unit tests for the native (kaos-nlp-core) case citation parser."""

from __future__ import annotations

import json
import pathlib

import pytest

from kaos_citations.extract import extract_citations
from kaos_citations.model import CaseCitation

_FIXTURE = (
    pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "case-citations-golden.jsonl"
)


def _load_golden() -> list[dict]:
    rows: list[dict] = []
    for line in _FIXTURE.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


@pytest.mark.unit
class TestCaseGoldenSet:
    @pytest.mark.parametrize("row", _load_golden())
    def test_parses_each_golden_citation(self, row: dict) -> None:
        """Every golden fixture must parse to exactly one CaseCitation with
        the expected volume, reporter, page, year, and (when present)
        court + case_name."""
        from kaos_citations.parsers.case import extract_case_citations

        citations = extract_case_citations(row["text"])
        assert len(citations) == 1, (
            f"Expected exactly 1 citation in {row['text']!r}, got {len(citations)}: "
            f"{[c.raw for c in citations]}"
        )
        cit = citations[0]
        assert isinstance(cit, CaseCitation)
        assert cit.volume == row["volume"]
        assert cit.reporter == row["reporter"]
        assert cit.page == row["page"]
        assert cit.year == row["year"]
        if "court" in row:
            assert cit.court == row["court"]
        if "case_name" in row:
            assert cit.case_name == row["case_name"]
        # Span must point back at a substring containing the matched reporter.
        start, end = cit.span
        assert row["text"][start:end] == cit.raw


@pytest.mark.unit
class TestCaseExtractionBehavior:
    def test_returns_empty_list_for_empty_text(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        assert extract_case_citations("") == []

    def test_returns_empty_list_for_irrelevant_text(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        assert extract_case_citations("No citations in this sentence.") == []

    def test_handles_multiple_citations_in_one_paragraph(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = (
            "See Miranda v. Arizona, 384 U.S. 436 (1966); "
            "see also Brown v. Board of Education, 347 U.S. 483 (1954)."
        )
        hits = extract_case_citations(text)
        assert len(hits) == 2
        # Spans must be in source order.
        assert hits[0].span[0] < hits[1].span[0]
        assert hits[0].volume == 384
        assert hits[1].volume == 347

    def test_source_uri_threaded(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        hits = extract_case_citations(
            "Miranda v. Arizona, 384 U.S. 436 (1966)", source_uri="doc:ex"
        )
        assert hits[0].source_uri == "doc:ex"

    def test_dispatcher_routes_case_kind(self) -> None:
        hits = extract_citations(
            "See Miranda v. Arizona, 384 U.S. 436 (1966).",
            kinds=["case"],
        )
        assert len(hits) == 1
        cit = hits[0]
        assert isinstance(cit, CaseCitation)
        assert cit.volume == 384

    def test_mixed_cfr_and_case_dispatch(self) -> None:
        text = "Under 17 CFR 240.10b-5 and Miranda v. Arizona, 384 U.S. 436 (1966), defendants..."
        hits = extract_citations(text)
        kinds = [h.kind for h in hits]
        assert "cfr" in kinds
        assert "case" in kinds
        # Source-order: CFR first at "17 CFR", case later.
        assert hits[0].kind == "cfr"
        assert hits[-1].kind == "case"


@pytest.mark.unit
class TestParentheticalChain:
    """Lock in P0a: chained parens after a case cite are parsed per
    Bluebook R10.5/R10.6 — date paren feeds ``year``/``court``,
    weight-only paren feeds ``weight``, judge paren feeds ``judges``,
    and only the explanatory paren spills into ``parenthetical``."""

    def test_year_only_paren_does_not_pollute_parenthetical(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        cites = extract_case_citations("Brown v. Bd. of Educ., 347 U.S. 483 (1954).")
        assert len(cites) == 1
        c = cites[0]
        assert c.year == 1954
        assert c.parenthetical is None
        assert c.parenthetical_kind is None

    def test_explanatory_paren_after_date_is_captured(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = (
            "Brown v. Bd. of Educ., 347 U.S. 483 (1954) "
            "(holding that segregation is unconstitutional)."
        )
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.year == 1954
        assert c.parenthetical == "holding that segregation is unconstitutional"
        assert c.parenthetical_kind == "explanatory"

    def test_weight_paren_chain_sets_weight_not_parenthetical(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "Plumhoff v. Rickard, 134 S. Ct. 2012, 2017 (2014) (per curiam)."
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.year == 2014
        assert c.weight == "per_curiam"
        assert c.parenthetical is None

    def test_three_paren_chain_court_weight_explanatory(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "Foo v. Bar, 100 F.3d 200, 205 (5th Cir. 1996) (en banc) (holding the rule applies)."
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.case_name == "Foo v. Bar"
        assert c.year == 1996
        assert c.court == "ca5"
        assert c.weight == "en_banc"
        assert c.parenthetical == "holding the rule applies"
        assert c.parenthetical_kind == "explanatory"

    # P0 #21: year-bearing explanatory parens must NOT classify as date
    # parens (which would conflate a stray year token with the citation
    # year). Lock the four canonical patterns from the audit.

    def test_year_bearing_explanatory_paren_only(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "Smith v. Jones, 123 F.3d 456 (citing some 2009 statute)"
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        # The 2009 token belongs to the explanatory paren, not the year
        # field. Without a real `(YYYY)` paren, year stays None.
        assert c.year is None
        assert c.parenthetical == "citing some 2009 statute"
        assert c.parenthetical_kind == "explanatory"

    def test_date_paren_then_year_bearing_explanatory(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "Smith v. Jones, 123 F.3d 456 (5th Cir. 2010) (citing some 2009 case)"
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.year == 2010
        assert c.court == "ca5"
        assert c.parenthetical == "citing some 2009 case"
        assert c.parenthetical_kind == "explanatory"

    def test_quoting_year_bearing_paren(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "Smith v. Jones, 123 F.3d 456 (5th Cir. 2010) (quoting the 1990 precedent)"
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.year == 2010
        assert c.parenthetical == "quoting the 1990 precedent"

    def test_pin_cite_then_year_paren_then_judge_paren(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "Brown v. Bd. of Ed., 347 U.S. 483, 489 (1954) (Warren, C.J.)"
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.year == 1954
        # Judge paren goes to `judges`, not `parenthetical`.
        assert c.parenthetical is None
        assert "Warren" in (c.judges[0] if c.judges else "")


@pytest.mark.unit
class TestSubsequentHistoryBoundary:
    """Lock in P0b: a case-name walk-back never crosses the prior
    citation's right edge or its R10.7 history connector."""

    def test_overruled_by_does_not_swallow_prior_cite(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = (
            "Roe v. Wade, 410 U.S. 113 (1973), overruled by Dobbs v. Jackson, 597 U.S. 215 (2022)."
        )
        cites = extract_case_citations(text)
        assert len(cites) == 2
        assert cites[0].case_name == "Roe v. Wade"
        assert cites[1].case_name == "Dobbs v. Jackson"

    def test_affd_does_not_swallow_prior_cite(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "Foo v. Bar, 100 F.3d 1 (5th Cir. 1996), aff'd, Baz v. Qux, 200 F.3d 100 (1997)."
        cites = extract_case_citations(text)
        assert len(cites) == 2
        assert cites[0].case_name == "Foo v. Bar"
        assert cites[1].case_name == "Baz v. Qux"

    def test_string_cite_signal_still_extracts_each_name(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = (
            "See Miranda v. Arizona, 384 U.S. 436 (1966); "
            "see also Brown v. Board of Education, 347 U.S. 483 (1954)."
        )
        cites = extract_case_citations(text)
        assert len(cites) == 2
        assert cites[0].case_name == "Miranda v. Arizona"
        assert cites[1].case_name == "Brown v. Board of Education"

    # P0 #22: every connector verb in the punch list — bare and
    # `<verb> by ` forms — must terminate the case-name walk-back.
    # The audit found half the punch-list connectors silently leaking
    # into the next citation's case_name.

    @pytest.mark.parametrize(
        "connector",
        [
            "modified",
            "overruled",
            "superseded",
            "superseded by",
            "appeal denied",
            "appeal docketed",
            "petition denied",
            "mandamus denied",
            "mandamus granted",
            "reh'g denied",
            "reh'g granted",
            "on remand",
            "on rem.",
        ],
    )
    def test_subsequent_history_connector_terminates_case_name(self, connector: str) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = (
            f"Smith v. Jones, 123 F.3d 456 (5th Cir. 2010), {connector} "
            f"Baz v. Qux, 234 F.3d 789 (5th Cir. 2011)."
        )
        cites = extract_case_citations(text)
        assert len(cites) == 2, f"expected 2 cites for connector {connector!r}, got {len(cites)}"
        # First cite preserves its name; second cite extracts cleanly
        # without the connector leaking into case_name.
        assert cites[0].case_name == "Smith v. Jones"
        assert cites[1].case_name == "Baz v. Qux", (
            f"connector {connector!r} leaked into next case_name: {cites[1].case_name!r}"
        )


@pytest.mark.unit
class TestIntroVerbBoundary:
    """Lock in P0 supplemental: introductory verbs (`citing`, `quoting`,
    ...) appearing mid-sentence must terminate the case-name walk-back.
    Unlike R10.7 connectors which sit at the leading edge of the
    candidate, intro verbs occur arbitrarily in surrounding prose."""

    def test_citing_mid_sentence_terminates_walkback(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = (
            "The court held that 17 CFR 240.10b-5(b) applies, "
            "citing Brown v. Board of Education, 347 U.S. 483 (1954)."
        )
        cites = extract_case_citations(text)
        assert len(cites) == 1
        assert cites[0].case_name == "Brown v. Board of Education"
        assert cites[0].year == 1954

    def test_quoting_mid_sentence_terminates_walkback(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = (
            "See generally the discussion at length, "
            "quoting Roe v. Wade, 410 U.S. 113 (1973), as authority."
        )
        cites = extract_case_citations(text)
        assert len(cites) == 1
        assert cites[0].case_name == "Roe v. Wade"

    def test_no_intro_verb_keeps_full_walkback(self) -> None:
        """When no intro verb appears, walk-back behaves as before."""
        from kaos_citations.parsers.case import extract_case_citations

        text = "Brown v. Board of Education, 347 U.S. 483 (1954) sets the rule."
        cites = extract_case_citations(text)
        assert len(cites) == 1
        assert cites[0].case_name == "Brown v. Board of Education"


@pytest.mark.unit
class TestWestlawAndLEXISPages:
    """Lock in 0.1.0a2 fix: Westlaw / LEXIS cites use 7-8 digit page
    numbers; the prior 5-digit page bound truncated them silently
    (``2013 WL 3958350`` → ``page=39583``)."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            (
                "See Foo v. Bar, 2013 WL 3958350, at *3 (Fed. Cl. July 31, 2013).",
                {"volume": 2013, "reporter": "WL", "page": 3958350},
            ),
            (
                "Citing Jackson v. State, 2018 WL 4173192 (Nev. App. 2018).",
                {"volume": 2018, "reporter": "WL", "page": 4173192},
            ),
            (
                "See also Smith, 2021 WL 6773089, at *2 (D. Nev. 2021).",
                {"volume": 2021, "reporter": "WL", "page": 6773089},
            ),
        ],
    )
    def test_westlaw_full_page_number_preserved(
        self, text: str, expected: dict[str, object]
    ) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.volume == expected["volume"]
        assert c.reporter == expected["reporter"]
        assert c.page == expected["page"]

    def test_six_digit_pin_cite_preserved(self) -> None:
        """Pin cites can also run 6+ digits in Westlaw / LEXIS — same
        bound as the page anchor."""
        from kaos_citations.parsers.case import extract_case_citations

        text = "See Foo v. Bar, 2020 WL 1234567, at *2 (Fed. Cir. 2020)."
        cites = extract_case_citations(text)
        assert len(cites) == 1
        assert cites[0].page == 1234567


@pytest.mark.unit
class TestOCRDegradedReporterMatching:
    """Lock in 0.1.0a2 fix: PDF OCR commonly drops case on the second
    or later token of a multi-word reporter (``Fed. Cl.`` → ``Fed.
    cl.``, ``F. Supp.`` → ``F. supp.``). Case-insensitive fallback over
    spellings ≥4 chars recovers the canonical reporter without
    admitting bare-letter false positives.
    """

    def test_lowercase_fed_cl_recovered_to_canonical(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "See Faulkner v. United States, 43 Fed. cl. 84, 86 (1998)."
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.volume == 43
        # Normalized to the canonical Bluebook form.
        assert c.reporter == "Fed. Cl."
        assert c.page == 84

    def test_lowercase_f_supp_2d_recovered_to_canonical(self) -> None:
        from kaos_citations.parsers.case import extract_case_citations

        text = "See Big v. Co., 200 F. supp. 2d 100 (S.D.N.Y. 2002)."
        cites = extract_case_citations(text)
        assert len(cites) == 1
        c = cites[0]
        assert c.volume == 200
        assert c.reporter == "F. Supp. 2d"
        assert c.page == 100

    def test_mixed_canonical_and_ocr_degraded_in_string_cite(self) -> None:
        """A passage with one canonical and one OCR-degraded reporter
        should yield both citations cleanly."""
        from kaos_citations.parsers.case import extract_case_citations

        text = "See Smith, 100 F.3d 1 (5th Cir. 2000) and Jones, 50 Fed. cl. 100 (2001)."
        cites = extract_case_citations(text)
        assert len(cites) == 2
        assert cites[0].reporter == "F.3d"
        assert cites[1].reporter == "Fed. Cl."

    def test_short_reporter_not_case_folded(self) -> None:
        """Sub-4-char spellings (``P.``, ``F.``, ``WL``) MUST stay
        case-sensitive — case-folding them would match in any prose.
        The 4-char threshold is the design pivot.
        """
        from kaos_citations.parsers.case import extract_case_citations

        # Bare lowercase 'p.' in normal prose must NOT match.
        cites = extract_case_citations(
            "The plaintiff alleges that p. matters, but Fed. context is absent."
        )
        assert cites == []

    def test_lowercase_us_reporter_recovered(self) -> None:
        """``U.S.`` is exactly 4 chars — the threshold edge. Case-fold
        is allowed here because a lowercase ``u.s.`` between digits
        and a page number is always a citation, never coincidence."""
        from kaos_citations.parsers.case import extract_case_citations

        text = "See foo v. bar, 100 u.s. 200 (1900)."
        cites = extract_case_citations(text)
        assert len(cites) == 1
        assert cites[0].reporter == "U.S."
        assert cites[0].volume == 100
        assert cites[0].page == 200
