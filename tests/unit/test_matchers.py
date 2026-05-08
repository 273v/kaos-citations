"""Verify the kaos_citations.matchers façade.

Every parser will go through these helpers — no `import re`, no
direct kaos-nlp-core imports outside this module + _nlp.py.
"""

from __future__ import annotations

from kaos_citations.matchers import (
    bluebook_signal_matcher,
    case_name_abbrev_fst,
    court_citation_fst,
    journal_fst,
    law_reporter_fst,
    multi_pattern,
    regex,
    reporter_fst,
    sentence_tokenizer,
    short_sentence_break_matcher,
    state_abbrev_fst,
    subsequent_history_matcher,
    substring_find_all,
    tokenize_words,
)


class TestBuilders:
    def test_regex_matcher(self) -> None:
        m = regex(r"(\d+)\s+U\.S\.\s+(\d+)")
        hits = m.find_all("See 347 U.S. 483 (1954) and 384 U.S. 436.")
        assert len(hits) == 2
        # Groups: [whole, vol, page]
        assert hits[0].groups[1] == "347"
        assert hits[0].groups[2] == "483"

    def test_multi_pattern(self) -> None:
        m = multi_pattern(["Fed. R. Civ. P.", "Rev. Rul.", "ASC"])
        text = "See Fed. R. Civ. P. 56; Rev. Rul. 2019-11; ASC 606."
        hits = m.find_all(text)
        # Three distinct prefixes hit
        assert len(hits) == 3
        prefixes = sorted(text[h.start : h.end] for h in hits)
        assert prefixes == ["ASC", "Fed. R. Civ. P.", "Rev. Rul."]

    def test_multi_pattern_does_not_match_substring(self) -> None:
        """Aho-Corasick with longest_match=True still respects whole-
        prefix boundaries when the prefix is contained in another
        word, because the user is responsible for adding word-level
        guards (the matcher itself is literal-substring). We document
        this: parsers must wrap with token-boundary checks if they
        want to avoid the ``Proc`` inside ``Proceeding`` trap."""
        m = multi_pattern(["Proc."])
        # Aho-Corasick will match the literal "Proc." substring
        # anywhere — including inside "Proceedings.". This is
        # expected literal-search behavior. Parsers handle by
        # checking token boundaries via tokenize_words.
        hits = m.find_all("FINRA Disciplinary Proceedings.")
        # ``Proc.`` does NOT appear inside ``Proceedings.`` because
        # the literal needle is "Proc." with the trailing dot, and
        # "Proceedings" has no internal dot before "eedings".
        assert len(hits) == 0

    def test_substring_find_all(self) -> None:
        spans = substring_find_all("foo bar foo bar foo", "foo")
        assert spans == [(0, 3), (8, 11), (16, 19)]

    def test_tokenize_words(self) -> None:
        toks = tokenize_words("Brown v. Board of Education, 347 U.S. 483 (1954).")
        words = [t.text for t in toks]
        assert "Brown" in words
        assert "Board" in words
        assert "1954" in words


class TestSentenceTokenizer:
    def test_returns_punkt_singleton(self) -> None:
        a = sentence_tokenizer()
        b = sentence_tokenizer()
        assert a is b

    def test_handles_legal_abbreviations(self) -> None:
        sents = sentence_tokenizer().tokenize("Brown v. Board, 347 U.S. 483, governs.")
        assert len(sents) == 1


class TestFsts:
    def test_reporter_fst_contains_known(self) -> None:
        f = reporter_fst()
        assert f.contains("U.S.")
        assert f.contains("F.3d")
        assert f.contains("S. Ct.")

    def test_journal_fst(self) -> None:
        f = journal_fst()
        assert f.contains("Yale L.J.")
        assert f.contains("Harv. L. Rev.")

    def test_law_reporter_fst(self) -> None:
        f = law_reporter_fst()
        assert f.contains("U.S.C.")

    def test_court_fst(self) -> None:
        f = court_citation_fst()
        # At least one of these flavors must be present
        any_present = any(f.contains(s) for s in ["2d Cir.", "2nd Cir."])
        assert any_present

    def test_case_name_abbrev_fst(self) -> None:
        f = case_name_abbrev_fst()
        for tok in ["Inc.", "Corp.", "Ass'n", "LLC"]:
            assert f.contains(tok), f"expected {tok!r} in case-name FST"

    def test_state_abbrev_fst(self) -> None:
        f = state_abbrev_fst()
        for tok in ["Cal.", "N.Y.", "Tex."]:
            assert f.contains(tok)


class TestModifierMatchers:
    def test_signals(self) -> None:
        m = bluebook_signal_matcher()
        text = "See Brown. But see Plessy. Cf. Marbury. Compare X."
        hits = m.find_all(text)
        signals = [h.groups[1] or "" for h in hits]
        assert "See" in signals
        # one of the multi-token signals should be matched
        assert any(s.startswith("But") for s in signals)
        assert any(s.startswith("Cf") for s in signals)
        assert "Compare" in signals

    def test_subsequent_history(self) -> None:
        m = subsequent_history_matcher()
        text = "..., aff'd, 521 U.S. 1; ..., cert. denied, 600 U.S. 700; ..., overruled by Brown."
        hits = m.find_all(text)
        connectors = [h.groups[1] or "" for h in hits]
        assert any("aff" in c for c in connectors)
        assert any("cert" in c for c in connectors)
        assert any("overruled" in c for c in connectors)

    def test_short_break(self) -> None:
        m = short_sentence_break_matcher()
        text = "End. Capital starts here."
        hits = m.find_all(text)
        assert len(hits) == 1
