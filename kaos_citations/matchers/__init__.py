"""kaos-citations matching infrastructure.

ALL pattern matching, tokenization, and known-vocab lookups in
kaos-citations go through this module. There is no `import re` and
no third-party tokenizer — only kaos-nlp-core primitives.

Public API:

- ``regex(pattern)`` — compiled Rust-backed regex (replaces ``re.compile``)
- ``multi_pattern(prefixes, ...)`` — Aho-Corasick over literal strings
  (replaces hand-coded `\\b...\\b` regex prefix lists)
- ``tokenize_words(text)`` — word tokenizer (replaces ``re.findall(r'\\w+')``)
- ``sentence_tokenizer()`` — Punkt singleton with bundled legal model
- ``reporter_fst()`` — FstSet over ~3,500 reporter spellings (canonical
  + variations) from vendored reporters_db
- ``journal_fst()`` — FstSet over ~800 journal abbreviations
- ``law_reporter_fst()`` — FstSet over ~370 statute / code reporters
- ``court_citation_fst()`` — FstSet over ~2,000 court citation strings
- ``case_name_abbrev_fst()`` — FstSet over case-name token abbreviations
  (Inc., Corp., Ass'n, LLC, ...)
- ``state_abbrev_fst()`` — FstSet over US state postal abbreviations
- ``bluebook_signal_matcher()`` — RegexMatcher for Bluebook R1.2 signals
- ``subsequent_history_matcher()`` — RegexMatcher for R10.7 history relations

Every accessor is ``lru_cache(maxsize=1)`` so the underlying FST /
matcher is built exactly once per process.
"""

from __future__ import annotations

from functools import lru_cache

from kaos_nlp_core.matching import (
    FstSet,
    MultiPatternMatcher,
    RegexMatcher,
    RegexMatchSpan,
)

# Re-export so parsers can type-annotate matcher tuples without
# reaching into kaos_nlp_core directly.
__matchers_export__ = ["FstSet", "MultiPatternMatcher", "RegexMatcher", "RegexMatchSpan"]
from kaos_nlp_core.matching import substring_find_all as _substring_find_all
from kaos_nlp_core.tokenizer import Tokenizer, TokenSpan

from kaos_citations._nlp import get_sentence_tokenizer
from kaos_citations.data._loaders import (
    case_name_abbreviation_tokens,
    court_citation_strings,
    journal_abbreviation_set,
    law_reporter_set,
    reporter_all_spellings,
    state_abbreviation_set,
)

# ---------------------------------------------------------------------------
# Re-export typed match-span classes so parsers don't need to reach into
# kaos_nlp_core.matching directly.
# ---------------------------------------------------------------------------

__all_spans__ = ["RegexMatchSpan", "TokenSpan"]


# ---------------------------------------------------------------------------
# Thin builders — every parser calls these instead of `re.compile`
# ---------------------------------------------------------------------------


def regex(pattern: str) -> RegexMatcher:
    """Compile ``pattern`` to a Rust-backed RegexMatcher.

    Pattern syntax follows the Rust ``regex`` crate (Perl-style, but
    no backreferences and no lookaround). Where Bluebook context would
    normally call for lookaround, we capture trailing terminators and
    trim them post-match, or split the work across multiple matchers.
    """
    return RegexMatcher(pattern)


def multi_pattern(
    patterns: list[str],
    *,
    case_insensitive: bool = False,
    longest_match: bool = True,
) -> MultiPatternMatcher:
    """Aho-Corasick matcher over literal strings (no regex).

    The right tool for "find any of these N exact prefix strings in a
    document" — single linear pass with no regex backtracking, so it
    cannot fall into the ``Proc`` matches inside ``Proceeding`` trap.

    Defaults to ``longest_match=True`` so ``Rev. Proc.`` wins over
    ``Rev.`` (the longer prefix is more specific in the citation
    domain).
    """
    return MultiPatternMatcher(
        patterns,
        case_insensitive=case_insensitive,
        longest_match=longest_match,
    )


def substring_find_all(haystack: str, needle: str) -> list[tuple[int, int]]:
    """Return ``(start, end)`` spans for every occurrence of
    ``needle`` in ``haystack`` — Rust-backed substring search."""
    return [(span.start, span.end) for span in _substring_find_all(haystack, needle)]


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


# Singleton instance — Rust tokenizer is cheap to call but we cache
# to avoid repeated Python-Rust crossings.
_TOKENIZER_SINGLETON: Tokenizer | None = None


def _shared_tokenizer() -> Tokenizer:
    global _TOKENIZER_SINGLETON
    if _TOKENIZER_SINGLETON is None:
        _TOKENIZER_SINGLETON = Tokenizer()
    return _TOKENIZER_SINGLETON


def tokenize_words(text: str) -> list[TokenSpan]:
    """Word tokenizer from kaos-nlp-core. Returns ``TokenSpan``
    instances with ``text``, ``start``, ``end`` attributes.

    Replaces all ``re.findall(r'\\w+', ...)`` patterns.
    """
    return _shared_tokenizer().tokenize(text)


# ---------------------------------------------------------------------------
# Sentence segmentation — singleton Punkt tokenizer with legal model
# ---------------------------------------------------------------------------


def sentence_tokenizer():  # type: ignore[no-untyped-def]
    """Return the singleton Punkt sentence tokenizer initialised
    with the bundled legal model. See ``kaos_citations._nlp`` for
    full docs / verification."""
    return get_sentence_tokenizer()


# ---------------------------------------------------------------------------
# FstSet builders — known-vocab lookups
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def reporter_fst() -> FstSet:
    """FstSet of every reporter spelling — canonical Bluebook form
    plus historical/variant spellings. Drawn from vendored
    reporters_db data. Covers cases (~1,235 canonical) plus
    variations, ~3,500 strings total."""
    return FstSet(sorted(reporter_all_spellings()))


@lru_cache(maxsize=1)
def journal_fst() -> FstSet:
    """FstSet of law-journal Bluebook abbreviations (``Yale L.J.``,
    ``Harv. L. Rev.``, ...). ~800 entries."""
    return FstSet(sorted(journal_abbreviation_set()))


@lru_cache(maxsize=1)
def law_reporter_fst() -> FstSet:
    """FstSet of statute / code reporters (``U.S.C.``, ``I.R.C.``,
    ``Cal. Penal Code``, ``N.Y. C.P.L.R.``, etc.). ~370 entries."""
    return FstSet(sorted(law_reporter_set()))


@lru_cache(maxsize=1)
def court_citation_fst() -> FstSet:
    """FstSet of court citation strings (``2d Cir.``, ``S.D.N.Y.``,
    ``E.D. Pa.``, etc.) drawn from courts_db. ~2,000 entries."""
    return FstSet(sorted(court_citation_strings()))


@lru_cache(maxsize=1)
def case_name_abbrev_fst() -> FstSet:
    """FstSet of case-name word abbreviations (``Inc.``, ``Corp.``,
    ``Ass'n``, ``LLC``, ``Soc'y``, ...). Used by case-name boundary
    detection so a token like ``Inc.`` is NOT treated as a sentence
    terminator."""
    return FstSet(sorted(case_name_abbreviation_tokens()))


@lru_cache(maxsize=1)
def state_abbrev_fst() -> FstSet:
    """FstSet of US state Bluebook abbreviations (``Cal.``, ``N.Y.``,
    ``Tex.``, etc.). 50 entries."""
    return FstSet(sorted(state_abbreviation_set()))


# ---------------------------------------------------------------------------
# Pre-built citation-modifier matchers (Bluebook signals + history)
# ---------------------------------------------------------------------------


# Bluebook R1.2 introductory signals. Order in the alternation matters —
# longer, more-specific signals win the leftmost match (the Rust regex
# crate is leftmost-first, so we list multi-token signals first).
# We do NOT use lookaround (Rust regex doesn't support it). Instead the
# trailing word-boundary ``\b`` after the alternation handles the
# "signal must end at a word break" constraint.
_BLUEBOOK_SIGNAL_PATTERN = (
    r"(?P<full_signal>"
    r"See,\s+e\.\s*g\.,?"
    r"|See\s+also\b"
    r"|See\s+generally\b"
    r"|But\s+see,\s+e\.\s*g\.,?"
    r"|But\s+see\b"
    r"|But\s+cf\."
    r"|Compare\b"
    r"|Accord\b"
    r"|Contra\b"
    r"|Cf\."
    r"|E\.\s*g\.,?"
    r"|See\b"
    r")"
)


@lru_cache(maxsize=1)
def bluebook_signal_matcher() -> RegexMatcher:
    """RegexMatcher for Bluebook R1.2 signals. Returns the matched
    signal string in ``groups[1]`` for normalization to the typed
    SignalKind literal."""
    return regex(_BLUEBOOK_SIGNAL_PATTERN)


# Bluebook R10.7 subsequent-history connectors that appear between two
# adjacent CaseCitations (parent → child).
_SUBSEQUENT_HISTORY_PATTERN = (
    r"(?P<connector>"
    r"aff'?d(?:\s+in\s+part)?"
    r"|rev'?d(?:\s+in\s+part)?"
    r"|vacated(?:\s+in\s+part)?"
    r"|remanded"
    r"|cert\.?\s*denied"
    r"|cert\.?\s*granted"
    r"|overruled(?:\s+in\s+part)?"
    r"|abrogated"
    r"|modified"
    r"|aff'?g"
    r"|rev'?g"
    r")"
)


@lru_cache(maxsize=1)
def subsequent_history_matcher() -> RegexMatcher:
    """RegexMatcher for Bluebook R10.7 subsequent-history connectors
    (``aff'd``, ``rev'd``, ``cert. denied``, ``overruled by``, ...).
    """
    return regex(_SUBSEQUENT_HISTORY_PATTERN)


# Sentence-end heuristic: ``[.!?]`` followed by whitespace + capital.
# Does NOT make abbreviation decisions — that's Punkt's job. We use this
# only in narrow string-cite-grouping logic that needs a SHORT-WINDOW
# break detector. The Punkt tokenizer is the source of truth for
# sentence boundaries in postprocess.py.
#
# Rust regex doesn't support lookahead, so we capture the leading
# character of the next sentence via group(1) instead of a lookahead.
# Callers should treat the match as ``[.!?]\\s+`` only — the captured
# capital belongs to the NEXT sentence, not the break itself.
_SHORT_BREAK_PATTERN = r"[.!?]\s+(?P<next_lead>[A-Z(\"'])"


@lru_cache(maxsize=1)
def short_sentence_break_matcher() -> RegexMatcher:
    """RegexMatcher for ``[.!?]\\s+`` followed by a capital — used
    only inside string-cite grouping where we ask "did a sentence
    end between cite A and cite B?". The captured next-lead character
    in group(1) belongs to the NEXT sentence; consumers should adjust
    spans accordingly. For full sentence segmentation, use
    ``sentence_tokenizer()``."""
    return regex(_SHORT_BREAK_PATTERN)


__all__ = [
    "RegexMatchSpan",
    "TokenSpan",
    "bluebook_signal_matcher",
    "case_name_abbrev_fst",
    "court_citation_fst",
    "journal_fst",
    "law_reporter_fst",
    "multi_pattern",
    "regex",
    "reporter_fst",
    "sentence_tokenizer",
    "short_sentence_break_matcher",
    "state_abbrev_fst",
    "subsequent_history_matcher",
    "substring_find_all",
    "tokenize_words",
]
