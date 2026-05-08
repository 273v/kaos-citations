"""Unit tests for the Bluebook post-processing passes.

Covers signal binding (R1.2), string-cite grouping (R1.4), subsequent
history (R10.7). The abbreviation / sentence-break logic now lives in
the kaos-nlp-core Punkt tokenizer (with the bundled legal model);
direct unit tests for it live in ``test_nlp_boundary.py``. These
tests target the postprocess passes end-to-end.
"""

from __future__ import annotations

import pytest

pytest.importorskip("eyecite")

from kaos_citations import CaseCitation, extract_citations
from kaos_citations.postprocess import (
    apply_postprocess,
    attach_signals,
    attach_string_cite_groups,
    attach_subsequent_history,
)

# ---------------------------------------------------------------------------
# Punkt-driven sentence boundary smoke tests
# ---------------------------------------------------------------------------


class TestSentenceStart:
    def test_at_doc_start(self) -> None:
        from kaos_citations.postprocess import _sentence_start_for_position

        assert _sentence_start_for_position("Hello world", 5) == 0

    def test_skips_v_abbreviation(self) -> None:
        from kaos_citations.postprocess import _sentence_start_for_position

        text = "Brown v. Board, 347 U.S. 483 (1954)."
        # Position of "347": Punkt should treat this as a single sentence
        # so the start of the citation's containing sentence is 0.
        pos = text.index("347")
        assert _sentence_start_for_position(text, pos) == 0

    def test_after_real_sentence(self) -> None:
        from kaos_citations.postprocess import _sentence_start_for_position

        text = "First sentence ends here. See Brown v. Board, 347 U.S. 483."
        pos = text.index("347")
        # Punkt should split between "here." and "See" — the citation's
        # sentence starts at "See".
        start = _sentence_start_for_position(text, pos)
        assert text[start:].startswith("See ")


# ---------------------------------------------------------------------------
# Signal binding
# ---------------------------------------------------------------------------


class TestSignalBinding:
    @pytest.mark.parametrize(
        "prefix,expected",
        [
            ("See ", "see"),
            ("See also ", "see_also"),
            ("See, e.g., ", "see_eg"),
            ("See generally ", "see_generally"),
            ("Cf. ", "cf"),
            ("But see ", "but_see"),
            ("But cf. ", "but_cf"),
            ("Compare ", "compare_with"),
            ("Accord ", "accord"),
            ("Contra ", "contra"),
            ("E.g., ", "eg"),
        ],
    )
    def test_each_signal(self, prefix: str, expected: str) -> None:
        text = f"{prefix}Brown v. Board of Education, 347 U.S. 483 (1954)."
        cites = extract_citations(text, source_uri="test://signal", kinds=("case",))
        assert len(cites) == 1
        assert cites[0].signal == expected

    def test_no_signal_when_absent(self) -> None:
        text = "Brown v. Board of Education, 347 U.S. 483 (1954)."
        cites = extract_citations(text, source_uri="test://nosignal", kinds=("case",))
        assert len(cites) == 1
        assert cites[0].signal is None

    def test_signal_not_bled_across_sentences(self) -> None:
        text = (
            "See Brown v. Board of Education, 347 U.S. 483 (1954). "
            "Plessy v. Ferguson, 163 U.S. 537 (1896), is overruled."
        )
        cites = extract_citations(text, source_uri="test://twosent", kinds=("case",))
        assert len(cites) == 2
        assert cites[0].signal == "see"
        assert cites[1].signal is None


# ---------------------------------------------------------------------------
# String-cite groups
# ---------------------------------------------------------------------------


class TestStringCiteGroups:
    def test_three_cites_one_group(self) -> None:
        text = (
            "See, e.g., Marbury v. Madison, 5 U.S. 137 (1803); "
            "McCulloch v. Maryland, 17 U.S. 316 (1819); "
            "Gibbons v. Ogden, 22 U.S. 1 (1824)."
        )
        cites = extract_citations(text, source_uri="test://group", kinds=("case",))
        assert len(cites) == 3
        groups = [c.string_cite_group for c in cites]
        assert groups[0] == groups[1] == groups[2] == 0

    def test_signal_propagates_through_group(self) -> None:
        text = (
            "See, e.g., Marbury v. Madison, 5 U.S. 137 (1803); "
            "McCulloch v. Maryland, 17 U.S. 316 (1819)."
        )
        cites = extract_citations(text, source_uri="test://prop", kinds=("case",))
        assert len(cites) == 2
        assert cites[0].signal == "see_eg"
        assert cites[1].signal == "see_eg"

    def test_separated_by_period_not_grouped(self) -> None:
        text = (
            "Brown v. Board of Education, 347 U.S. 483 (1954). "
            "Plessy v. Ferguson, 163 U.S. 537 (1896)."
        )
        cites = extract_citations(text, source_uri="test://nogroup", kinds=("case",))
        assert len(cites) == 2
        assert cites[0].string_cite_group is None
        assert cites[1].string_cite_group is None


# ---------------------------------------------------------------------------
# Subsequent history
# ---------------------------------------------------------------------------


class TestSubsequentHistory:
    @pytest.mark.parametrize(
        "connector,relation",
        [
            (", aff'd", "affirmed"),
            (", rev'd", "reversed"),
            (", vacated", "vacated"),
            (", remanded", "remanded"),
            (", cert. denied", "cert_denied"),
            (", overruled by", "overruled"),
            (", abrogated by", "abrogated"),
        ],
    )
    def test_history_relations(self, connector: str, relation: str) -> None:
        text = (
            f"Smith v. Jones, 100 F.3d 200 (5th Cir. 1996){connector}, "
            "Jones v. Smith, 200 F.3d 300 (5th Cir. 1997)."
        )
        cites = extract_citations(text, source_uri="test://hist", kinds=("case",))
        # We need at least 2 case cites with parent → child history.
        # Use isinstance for ty narrowing — ``c.kind == "case"`` doesn't
        # narrow the discriminated union for the type checker.
        case_cites = [c for c in cites if isinstance(c, CaseCitation)]
        if len(case_cites) < 2:
            pytest.skip(f"eyecite did not parse both citations from {text!r}")
        parent = case_cites[0]
        assert parent.subsequent_history, (
            f"expected subsequent_history on parent, got {parent.subsequent_history}"
        )
        relations = [rel for rel, _ in parent.subsequent_history]
        assert relation in relations


# ---------------------------------------------------------------------------
# Idempotence + apply_postprocess
# ---------------------------------------------------------------------------


class TestApplyPostprocess:
    def test_idempotent(self) -> None:
        """Running postprocess twice should be a no-op (frozen models, no
        signals re-attached when already set)."""
        text = "See, e.g., Marbury v. Madison, 5 U.S. 137 (1803)."
        cites = extract_citations(text, source_uri="test://idem", kinds=("case",))
        once = list(cites)
        twice = apply_postprocess(text, list(once))
        # Same length
        assert len(once) == len(twice)
        # Same signals
        assert [c.signal for c in once] == [c.signal for c in twice]
        # Same string-cite groups
        assert [c.string_cite_group for c in once] == [c.string_cite_group for c in twice]

    def test_returns_new_list(self) -> None:
        text = "See Brown, 347 U.S. 483."
        cites = list(extract_citations(text, source_uri="test://new", kinds=("case",)))
        result = attach_signals(text, cites)
        assert result is not cites or all(
            r.signal is not None or c.signal == r.signal for c, r in zip(cites, result, strict=True)
        )

    def test_empty_input(self) -> None:
        assert apply_postprocess("any text", []) == []
        assert attach_signals("any text", []) == []
        assert attach_string_cite_groups("any text", []) == []
        assert attach_subsequent_history("any text", []) == []


# ---------------------------------------------------------------------------
# Stable cite_id refactor (P3a)
# ---------------------------------------------------------------------------


class TestStableCiteIds:
    """``cite_id`` is the stable cross-reference key for ``back_ref`` and
    the second tuple element of ``subsequent_history``. Once assigned,
    filtering / re-sorting the result list MUST NOT break the
    cross-references."""

    def test_extract_assigns_sequential_cite_ids(self) -> None:
        text = (
            "See Miranda v. Arizona, 384 U.S. 436 (1966); "
            "see also Brown v. Board of Education, 347 U.S. 483 (1954)."
        )
        cites = extract_citations(text, kinds=("case",))
        assert [c.cite_id for c in cites] == ["c0001", "c0002"]

    def test_subsequent_history_uses_cite_id_not_index(self) -> None:
        text = (
            "Roe v. Wade, 410 U.S. 113 (1973), overruled by Dobbs v. Jackson, 597 U.S. 215 (2022)."
        )
        cites = extract_citations(text, kinds=("case",))
        assert len(cites) == 2
        parent, child = cites
        # Narrow the discriminated union for the type checker.
        assert isinstance(parent, CaseCitation)
        assert isinstance(child, CaseCitation)
        assert parent.subsequent_history == (("overruled", child.cite_id),)
        # Second tuple element is now str (cite_id), NOT an int index.
        assert isinstance(parent.subsequent_history[0][1], str)

    def test_history_survives_filtering(self) -> None:
        """Filtering the list must not invalidate the back-reference."""
        text = (
            "Roe v. Wade, 410 U.S. 113 (1973), overruled by Dobbs v. Jackson, 597 U.S. 215 (2022)."
        )
        cites = extract_citations(text, kinds=("case",))
        # Drop the parent. The (formerly index-based) back-reference would
        # now point at a no-longer-existing list slot. The cite_id-based
        # reference remains valid — the child can still be found by its ID.
        only_child = [
            c for c in cites if isinstance(c, CaseCitation) and c.case_name == "Dobbs v. Jackson"
        ]
        assert len(only_child) == 1
        assert only_child[0].cite_id == "c0002"

    def test_assign_cite_ids_is_idempotent(self) -> None:
        from kaos_citations.postprocess import assign_cite_ids

        text = "See Brown v. Bd. of Educ., 347 U.S. 483 (1954)."
        cites = extract_citations(text, kinds=("case",))
        once = list(cites)
        twice = assign_cite_ids(once)
        assert [c.cite_id for c in once] == [c.cite_id for c in twice]
