"""Native case-citation extractor — kaos-nlp-core only, NO eyecite.

Replaces the eyecite adapter with a native implementation that uses:

- ``kaos_citations.matchers.reporter_fst`` (built from the vendored
  reporters_db) to detect reporter tokens via Aho-Corasick.
- ``kaos_citations.matchers.case_name_abbrev_fst`` to know which
  trailing tokens are part of a case name (``Inc.``, ``Corp.``).
- ``kaos_citations.matchers.court_citation_fst`` (built from the
  vendored courts_db) for court detection in the parenthetical.
- ``kaos_citations.matchers.sentence_tokenizer()`` (Punkt with the
  bundled legal model) for sentence-boundary anchoring.
- ``kaos_citations.matchers.regex(...)`` for the few small patterns
  that drive volume/page extraction.

The extractor handles the citation forms in the project test fixtures
plus the SCOTUS / SEC / accounting benchmark documents:

- Full-form: ``Miranda v. Arizona, 384 U.S. 436 (1966)``
- Short-form: ``Brown, 347 U.S. at 495``
- ``Id.`` / ``Id. at NN``
- ``X v. Y, 100 F.3d 200, 205 (5th Cir. 1996)`` with court detection
- Parenthetical with weight: ``(per curiam)``, ``(en banc)``,
  ``(Sotomayor, J., dissenting)``
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import cast

from kaos_citations.data._loaders import (
    court_id_by_citation_string,
    load_reporters,
    reporter_all_spellings,
    reporter_canonical_set,
    reporter_variations,
)
from kaos_citations.matchers import (
    multi_pattern,
    regex,
    sentence_tokenizer,
)
from kaos_citations.model import (
    CaseCitation,
    Citation,
    IdCitation,
    JournalCitation,
    SupraCitation,
    WeightOfAuthority,
)

# ---------------------------------------------------------------------------
# Reporter detection — Aho-Corasick over vendored reporters_db
# ---------------------------------------------------------------------------

# Minimum spelling length at which we accept a case-insensitive match.
# Set conservatively — many reporters are 1-3 chars (``P``, ``P.``,
# ``F.``, ``WL``, ``NV``, ``OK``, ``US``, ...) and case-folding those
# would match in any prose. The 4-char threshold keeps unique
# multi-token reporters like ``Fed. Cl.`` / ``F. Supp.`` / ``S. Ct.`` /
# ``L. Ed.`` recoverable from PDF OCR / Tesseract output where one or
# more letters have dropped case (``Fed. cl.``, ``F. supp.``), while
# refusing to widen the matcher into territory where coincidence
# becomes plausible.
_REPORTER_CASE_FOLD_MIN_LEN = 4


@lru_cache(maxsize=1)
def _reporter_matcher_strict():  # type: ignore[no-untyped-def]
    """Case-sensitive Aho-Corasick over every canonical + variation
    reporter spelling.

    longest_match=True so ``F. Supp. 2d`` wins over ``F. Supp.``.
    """
    # Cast: ``sorted(..., key=len)`` confuses ty's inference back to
    # ``list[Sized]`` even though the source set is ``frozenset[str]``.
    spellings = cast("list[str]", sorted(reporter_all_spellings(), key=len, reverse=True))
    return multi_pattern(spellings, longest_match=True)


@lru_cache(maxsize=1)
def _reporter_matcher_lenient():  # type: ignore[no-untyped-def]
    """Case-insensitive Aho-Corasick over reporter spellings ≥
    ``_REPORTER_CASE_FOLD_MIN_LEN`` chars. Only used as a fallback for
    spans the strict matcher missed (see ``_find_reporter_hits``).

    The length cutoff is the design pivot: a case-insensitive match on
    a single-letter pattern like ``P`` would fire in any sentence; a
    match on ``Fed. Cl.`` requires that exact 8-char shape (modulo
    case) which essentially never appears outside a citation.
    """
    spellings = sorted(
        (s for s in reporter_all_spellings() if len(s) >= _REPORTER_CASE_FOLD_MIN_LEN),
        key=len,
        reverse=True,
    )
    return multi_pattern(cast("list[str]", spellings), longest_match=True, case_insensitive=True)


def _find_reporter_hits(text: str):  # type: ignore[no-untyped-def]
    """Run both matchers and merge — longest match wins on overlaps.

    The strict matcher catches every well-cased canonical reporter
    spelling. The lenient case-insensitive matcher (≥4-char patterns
    only) picks up OCR-degraded forms — ``Fed. cl.`` for ``Fed. Cl.``,
    ``F. supp.`` for ``F. Supp.``. Both matchers can fire at
    overlapping positions: a strict ``Fed.`` (4 chars) at position
    3..7 vs a lenient ``Fed. cl.`` (8 chars) at 3..11.

    Resolution rule: the longer span wins. The strict matcher's
    short-prefix hit is discarded in favor of the lenient matcher's
    full-form hit when both anchor at the same start and the lenient
    one extends further. This recovers the OCR-degraded reporter
    without admitting bare-letter false positives (which the lenient
    matcher's 4-char minimum already excludes).
    """
    strict = list(_reporter_matcher_strict().find_all(text))
    lenient = list(_reporter_matcher_lenient().find_all(text))
    if not lenient:
        strict.sort(key=lambda h: h.start)
        return strict
    if not strict:
        return lenient

    merged = strict + lenient
    # Sort by start ascending, length descending — so when iterating,
    # at any given start position we see the longest hit first.
    merged.sort(key=lambda h: (h.start, -(h.end - h.start)))

    out: list = []
    last_end = -1
    for h in merged:
        if h.start < last_end:
            # Overlaps a previously-kept (longer-or-equal) hit — drop.
            continue
        out.append(h)
        last_end = h.end
    return out


@lru_cache(maxsize=1)
def _reporter_canonical_lookup() -> dict[str, str]:
    """Lowercase-keyed lookup mapping each spelling (and its case-folded
    form) to a canonical Bluebook reporter abbreviation.

    Built once and cached. Populated from ``reporter_variations`` plus
    the canonical-set itself; canonical wins when both a canonical and
    a variation share the same case-folded key. Used by
    ``_normalize_reporter`` to resolve OCR-degraded forms back to
    their canonical reporter.
    """
    out: dict[str, str] = {}
    # Canonical spellings map to themselves — they take precedence over
    # variation rewrites, so add them first.
    for canonical in reporter_canonical_set():
        out.setdefault(canonical.lower(), canonical)
    # Variation rewrites: only fill in lowercase keys not already
    # claimed by a canonical spelling.
    for variant, canonical in reporter_variations().items():
        out.setdefault(variant.lower(), canonical or variant)
    return out


def _normalize_reporter(spelling: str) -> str:
    """Map a matched spelling to its canonical Bluebook form.

    Order:
      1. Direct ``reporter_variations`` lookup (variant → canonical).
      2. Identity if the spelling is already canonical.
      3. Case-folded fallback for OCR-degraded forms (``Fed. cl.`` →
         ``Fed. Cl.``).
    """
    direct = reporter_variations().get(spelling)
    if direct is not None:
        return direct
    if spelling in reporter_canonical_set():
        return spelling
    return _reporter_canonical_lookup().get(spelling.lower(), spelling)


def _reporter_court_codes(canonical_reporter: str) -> tuple[str, ...]:
    """Return the reporter's mlz_jurisdiction list — used as a fallback
    court tag when the parenthetical doesn't surface a court abbrev."""
    entries = load_reporters().get(canonical_reporter)
    if not entries:
        # Could be an edition key — find the parent
        for _k, ents in load_reporters().items():
            for e in ents:
                if any(ed.edition_key == canonical_reporter for ed in e.editions):
                    return e.mlz_jurisdiction
        return ()
    return entries[0].mlz_jurisdiction


def _scotus_court_default(canonical_reporter: str) -> str | None:
    """Return ``"scotus"`` when this reporter is exclusively a US Reports
    family. Mirrors eyecite's behavior of tagging ``347 U.S. 483`` as
    SCOTUS even without an explicit parenthetical."""
    entries = load_reporters().get(canonical_reporter)
    if not entries:
        # Try parent lookup via edition
        for ents in load_reporters().values():
            for e in ents:
                if any(ed.edition_key == canonical_reporter for ed in e.editions):
                    entries = (e,)
                    break
            if entries:
                break
    if not entries:
        return None
    if canonical_reporter in {"U.S.", "S. Ct.", "L. Ed.", "L. Ed. 2d"}:
        return "scotus"
    return None


# ---------------------------------------------------------------------------
# Volume + page detection — small Rust regexes anchored at reporter span
# ---------------------------------------------------------------------------

# Volume: digits immediately preceding the reporter (with optional ws).
# Rust regex: ``\A`` start-of-input, ``\z`` end-of-input (lowercase).
_VOLUME_TAIL_PATTERN = r"(?P<vol>\d{1,4})\s+\z"
# Page: digits immediately following the reporter (with optional ws).
# Cap is 8 digits to accommodate Westlaw cites (``2013 WL 3958350`` —
# 7 digits) and LEXIS cites of similar magnitude. The earlier 5-digit
# bound was calibrated against Bluebook reporters where pages rarely
# exceed 5 digits; expanding to 8 keeps every conventional reporter
# happy while admitting Westlaw / LEXIS / star-paginated services.
_PAGE_HEAD_PATTERN = r"\A\s+(?P<page>\d{1,8})"
# Pin cite (single page or page-range or comma-list of pages). Same
# 8-digit bound as ``_PAGE_HEAD_PATTERN`` — pin cites can run as long
# as page numbers in Westlaw / LEXIS cites.
_PIN_HEAD_PATTERN = r"\A\s*,\s*(?P<pin>\d{1,8}(?:-\d{1,8})?(?:,\s*\d{1,8})*|\*\d+)"
# Parenthetical: balanced ``(...)`` capturing the inner text.
_PAREN_HEAD_PATTERN = r"\A\s*\((?P<inner>[^)]+)\)"
# Year inside a parenthetical (4-digit 1600-2200).
_YEAR_PATTERN = r"\b(1[6-9]\d{2}|20\d{2}|21\d{2})\b"
# A real `(YYYY)` parenthetical — used by `_find_year_after` to scan
# for a year-bearing paren after a citation when no `_PAREN_HEAD_PATTERN`
# match landed. Must be paren-anchored so a bare year token in
# explanatory prose doesn't qualify. Optional court abbreviation +
# optional date prefix kept inside the same paren.
_YEAR_PAREN_PATTERN = (
    r"\("
    r"(?:[A-Za-z0-9.\-' ]{0,40}\s+)?"
    r"(?:(?:Jan(?:\.|uary)?|Feb(?:\.|ruary)?|Mar(?:\.|ch)?|Apr(?:\.|il)?|May"
    r"|Jun(?:\.|e)?|Jul(?:\.|y)?|Aug(?:\.|ust)?|Sept?(?:\.|ember)?"
    r"|Oct(?:\.|ober)?|Nov(?:\.|ember)?|Dec(?:\.|ember)?)\s+\d{1,2},\s+)?"
    r"(1[6-9]\d{2}|20\d{2}|21\d{2})"
    r"\s*\)"
)
# Strict "this paren is a date paren" matcher per Bluebook R10.5: the
# entire paren contents must be either a bare year, a date prefix +
# year (`Mar. 14, 2010`), or an optional court abbreviation followed
# by an optional date prefix and a year. NO other tokens — anything
# explanatory makes this an explanatory paren even if a 4-digit year
# happens to appear inside it (e.g. `(citing the 2009 statute)` or
# `(holding that the 1965 statute …)`).
#
# Court-abbrev prefix has to start with an uppercase letter or a digit
# (so `5th Cir.`, `2d Cir.`, `9th Cir.`, `S.D.N.Y.`, `D.D.C.`,
# `Fed. Cir.` all match) but never with a lowercase letter (rules out
# `citing`, `quoting`, `holding`, `noting`, ...). Capped at 40 chars
# to prevent runaway matches against explanatory text.
_DATE_PAREN_PATTERN = (
    r"(?i)\A\s*"
    # optional court abbrev: uppercase- or digit-led tokens, no comma.
    # Character class includes a literal space so multi-word court
    # abbrevs like `5th Cir.` and `D.C. Cir.` match without a separate
    # alternation.
    r"(?:[A-Z0-9][A-Za-z0-9.\-' ]{0,40}\s+)?"
    # optional date prefix: `Jan. 14, ` / `January 14, ` / `Mar 14, `
    r"(?:(?:Jan(?:\.|uary)?|Feb(?:\.|ruary)?|Mar(?:\.|ch)?|Apr(?:\.|il)?|May"
    r"|Jun(?:\.|e)?|Jul(?:\.|y)?|Aug(?:\.|ust)?|Sept?(?:\.|ember)?"
    r"|Oct(?:\.|ober)?|Nov(?:\.|ember)?|Dec(?:\.|ember)?)\s+\d{1,2},\s+)?"
    r"(?:1[6-9]\d{2}|20\d{2}|21\d{2})\s*\z"
)
# Standalone weight-only parenthetical (Bluebook R10.6.1) — used to
# classify whether a chained ``(...)`` is purely a weight tag like
# ``(per curiam)`` / ``(en banc)`` (and therefore should NOT spill into
# the ``parenthetical`` field). Anchors at start; tolerates trailing
# whitespace.
_WEIGHT_ONLY_PATTERN = (
    r"(?i)\A\s*"
    r"(?:en\s+banc"
    r"|per\s+curiam"
    r"|plurality(?:\s+opinion)?"
    r"|mem(?:orandum|\.)?"
    r"|dissenting(?:\s+in\s+part)?"
    r"|concurring(?:\s+in\s+part)?)"
    r"\s*\z"
)
# Weight-of-authority parenthetical phrases.
_WEIGHT_PATTERN = (
    r"(?i)"
    r"\b(?P<en_banc>en\s+banc)"
    r"|\b(?P<per_curiam>per\s+curiam)"
    r"|\b(?P<plurality>plurality)"
    r"|\b(?P<memorandum>mem(?:orandum|\.)?)\b"
    r"|\b(?P<dissenting_in_part>dissenting\s+in\s+part)"
    r"|\b(?P<concurring_in_part>concurring\s+in\s+part)"
    r"|\b(?P<dissenting>dissenting)"
    r"|\b(?P<concurring>concurring)"
)
# Judge / opinion-author capture inside parenthetical.
_JUDGE_PATTERN = (
    r"(?P<judges>(?:[A-Z][a-zA-Z'\-]+(?:\s*&\s*[A-Z][a-zA-Z'\-]+)*"
    r"(?:,\s*(?:Jr\.|Sr\.|III|II|IV))?))\s*,?\s*"
    r"(?P<title>C\.?\s*JJ?\.?|J\.|JJ\.)"
)


@lru_cache(maxsize=1)
def _volume_tail_matcher():  # type: ignore[no-untyped-def]
    return regex(_VOLUME_TAIL_PATTERN)


@lru_cache(maxsize=1)
def _page_head_matcher():  # type: ignore[no-untyped-def]
    return regex(_PAGE_HEAD_PATTERN)


@lru_cache(maxsize=1)
def _pin_head_matcher():  # type: ignore[no-untyped-def]
    return regex(_PIN_HEAD_PATTERN)


@lru_cache(maxsize=1)
def _paren_head_matcher():  # type: ignore[no-untyped-def]
    return regex(_PAREN_HEAD_PATTERN)


@lru_cache(maxsize=1)
def _year_matcher():  # type: ignore[no-untyped-def]
    return regex(_YEAR_PATTERN)


@lru_cache(maxsize=1)
def _date_paren_matcher():  # type: ignore[no-untyped-def]
    return regex(_DATE_PAREN_PATTERN)


@lru_cache(maxsize=1)
def _year_paren_matcher():  # type: ignore[no-untyped-def]
    return regex(_YEAR_PAREN_PATTERN)


@lru_cache(maxsize=1)
def _weight_only_matcher():  # type: ignore[no-untyped-def]
    return regex(_WEIGHT_ONLY_PATTERN)


@lru_cache(maxsize=1)
def _weight_matcher():  # type: ignore[no-untyped-def]
    return regex(_WEIGHT_PATTERN)


@lru_cache(maxsize=1)
def _judge_matcher():  # type: ignore[no-untyped-def]
    return regex(_JUDGE_PATTERN)


# ---------------------------------------------------------------------------
# Anchored helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Anchor:
    """A fully-resolved volume-reporter-page anchor in the document."""

    volume: int
    reporter: str  # canonical Bluebook form
    raw_reporter: str  # exact spelling as it appeared
    page: int
    vol_start: int
    page_end: int


def _find_volume_before(text: str, pos: int) -> tuple[int, int] | None:
    """Find the volume integer immediately preceding ``text[pos]``.
    Returns ``(volume, vol_start)`` or ``None`` when no digits found.
    """
    # Look at the text just before pos.
    if pos <= 0:
        return None
    sub = text[:pos]
    hit = _volume_tail_matcher().find_first(sub)
    if hit is None or hit.end != len(sub):
        return None
    try:
        vol = int(hit.groups[1])
    except (TypeError, ValueError):
        return None
    return vol, hit.start


def _find_page_after(text: str, pos: int) -> tuple[int, int] | None:
    """Find the page integer immediately after ``text[pos]``.
    Returns ``(page, page_end)``."""
    sub = text[pos:]
    if not sub:
        return None
    hit = _page_head_matcher().find_first(sub)
    if hit is None or hit.start != 0:
        return None
    try:
        page = int(hit.groups[1])
    except (TypeError, ValueError):
        return None
    return page, pos + hit.end


def _find_anchors(text: str) -> list[_Anchor]:
    """Phase 1+2: find every <volume> <reporter> <page> anchor."""
    anchors: list[_Anchor] = []
    for hit in _find_reporter_hits(text):
        rep_start, rep_end = hit.start, hit.end
        raw_reporter = text[rep_start:rep_end]
        canonical = _normalize_reporter(raw_reporter)

        vol_info = _find_volume_before(text, rep_start)
        if vol_info is None:
            continue
        volume, vol_start = vol_info

        page_info = _find_page_after(text, rep_end)
        if page_info is None:
            continue
        page, page_end = page_info

        anchors.append(
            _Anchor(
                volume=volume,
                reporter=canonical,
                raw_reporter=raw_reporter,
                page=page,
                vol_start=vol_start,
                page_end=page_end,
            )
        )
    return anchors


# ---------------------------------------------------------------------------
# Case-name extraction
# ---------------------------------------------------------------------------

# Bluebook signals to strip from the leading edge of a case-name candidate.
_BLUEBOOK_SIGNAL_LEADERS: tuple[str, ...] = (
    "see, e.g.,",
    "see also",
    "see generally",
    "but see, e.g.,",
    "but see",
    "but cf.",
    "compare",
    "accord",
    "contra",
    "cf.",
    "e.g.,",
    "e.g.",
    "see",
)


# Bluebook R10.7 subsequent-history + R1.4 connectors that bridge two
# CaseCitations and so must be stripped from the LEADING edge of a
# case-name candidate when walking back from the next anchor. The
# prev-anchor floor in ``_extract_case_name`` removes everything up to
# the prior cite's right edge; this list strips the connector token
# itself plus any ``See also`` / ``E.g.,`` style fragments.
_BLUEBOOK_CONNECTORS: tuple[str, ...] = (
    # Subsequent-history (R10.7) — ordered longest-first within each
    # verb so `<verb> by ` / `<verb>, ` win over the bare `<verb> `
    # form when the fixpoint loop in `_strip_leading_signals` does
    # `startswith`. Both bare and ", "-suffixed forms are listed
    # because Bluebook style is inconsistent in real-world filings.
    "overruled in part by ",
    "overruled in part, ",
    "overruled by ",
    "overruled, ",
    "overruled ",
    "overruling ",
    "abrogated by ",
    "abrogated, ",
    "abrogated ",
    "abrogating ",
    "superseded by ",
    "superseded, ",
    "superseded ",
    "modified by ",
    "modified, ",
    "modified ",
    "modifying ",
    "vacated and remanded ",
    "vacated by ",
    "vacated, ",
    "vacated ",
    "remanded by ",
    "remanded, ",
    "remanded ",
    "reversed and remanded ",
    "reversed by ",
    "reversed, ",
    "reversed ",
    "rev'd by ",
    "rev'd, ",
    "rev'd ",
    "rev'g ",
    "affirmed by ",
    "affirmed, ",
    "affirmed ",
    "aff'd by ",
    "aff'd, ",
    "aff'd ",
    "aff'g ",
    "cert. denied, ",
    "cert. denied ",
    "cert. granted, ",
    "cert. granted ",
    "cert denied ",
    "cert granted ",
    "appeal denied, ",
    "appeal denied ",
    "appeal docketed, ",
    "appeal docketed ",
    "appeal dismissed, ",
    "appeal dismissed ",
    "petition denied, ",
    "petition denied ",
    "petition granted, ",
    "petition granted ",
    "mandamus denied, ",
    "mandamus denied ",
    "mandamus granted, ",
    "mandamus granted ",
    "reh'g denied, ",
    "reh'g denied ",
    "reh'g granted, ",
    "reh'g granted ",
    "on remand, ",
    "on remand ",
    "on rem., ",
    "on rem. ",
    # R1.4 string-cite connectors
    "with ",
    "and ",
    "in ",
)


# Common introductory verbs — handled separately from
# `_BLUEBOOK_CONNECTORS` because they can appear MID-sentence rather
# than at the leading edge. The walk-back floor for `_extract_case_name`
# needs a right-to-left pass to find the rightmost occurrence and trim
# everything before it. Example:
#
#   "The court held that ... applies, citing Brown v. Board of Education,
#    347 U.S. 483 (1954)"
#
# A leading-edge strip never reaches `citing` because the candidate
# starts with `The court held ...`. The right-to-left pass finds
# `, citing ` near the end, sets the floor just after, and yields
# case_name=`Brown v. Board of Education`.
_CASE_NAME_INTRO_VERBS: tuple[str, ...] = (
    ", citing ",
    ", quoting ",
    ", following ",
    ", applying ",
    ", construing ",
    ", discussing ",
    ", explaining ",
    ", noting ",
    ", holding ",
    ", relying on ",
    " citing ",
    " quoting ",
    " following ",
    " applying ",
    " construing ",
    " discussing ",
    " explaining ",
    " noting ",
    " holding ",
    " relying on ",
)


def _strip_leading_signals(name_candidate: str) -> str:
    """Strip Bluebook signals + connectors from the start of a case-name
    candidate.

    Both signal and connector lists are applied in a fixpoint loop —
    a candidate like ``, see also overruled by Foo`` chains the comma
    strip → ``see also`` → ``overruled by`` before stabilising.
    """
    s = name_candidate.lstrip(" ,;\"'(")
    while True:
        s_lower = s.lower()
        stripped = False
        for signal in _BLUEBOOK_SIGNAL_LEADERS:
            if s_lower.startswith(signal):
                s = s[len(signal) :].lstrip(" ,;")
                stripped = True
                break
        if stripped:
            continue
        for connector in _BLUEBOOK_CONNECTORS:
            if s_lower.startswith(connector):
                s = s[len(connector) :].lstrip(" ,;")
                stripped = True
                break
        if not stripped:
            break
    return s


def _is_plausible_case_name(name: str) -> bool:
    """Return True when ``name`` looks like a case caption."""
    if not name or len(name) < 3:
        return False
    # ``X v. Y`` — look for ` v. ` or ` v ` between two capitalized starts
    if " v. " in name or " v " in name:
        return True
    # ``In re X``, ``Matter of X``, ``Ex parte X``, ``In the Matter of X``
    lower = name.lower()
    return lower.startswith(("in re ", "matter of ", "ex parte ", "in the matter of "))


def _extract_case_name(text: str, vol_start: int, *, prev_end: int = 0) -> str | None:
    """Walk back from the volume to the start of the citation sentence,
    strip leading signals/connectors, return the case-name candidate.

    Punkt provides sentence boundaries; we don't re-roll abbreviation
    logic.

    ``prev_end`` is a floor: the rightmost edge of the previous anchor
    (its closing ``)`` if it had a date parenthetical, otherwise its
    page end). Walking back is clamped to that position so a case-name
    extraction for cite ``N+1`` cannot swallow text from cite ``N``.
    Bluebook subsequent-history bridges (``overruled by ...``,
    ``aff'd ...``, ``cert. denied ...``) live in that gap and are
    stripped by ``_strip_leading_signals``.
    """
    if vol_start <= 0:
        return None
    # Strip the trailing ``, `` (comma-space) before the volume.
    i = vol_start
    while i > 0 and text[i - 1] in ", \t":
        i -= 1
    name_end = i

    # Find sentence start via Punkt.
    starts = _sentence_starts_cached(text)
    sent_start = 0
    for s in starts:
        if s <= vol_start:
            sent_start = s
        else:
            break

    floor = max(sent_start, prev_end)
    name_candidate = text[floor:name_end].strip()
    # Right-to-left trim at the rightmost intro-verb occurrence
    # (`... applies, citing Brown v. Bd. ...` → `Brown v. Bd.`). Done
    # BEFORE the leading-edge strip because the leading strip can only
    # see the start of the candidate, while intro verbs appear mid-prose.
    name_candidate = _trim_at_last_intro_verb(name_candidate)
    name_candidate = _strip_leading_signals(name_candidate)
    # Strip leading semicolon / opening paren that survives signal-stripping.
    name_candidate = name_candidate.lstrip(" ,;")
    if not _is_plausible_case_name(name_candidate):
        return None
    return name_candidate


def _trim_at_last_intro_verb(candidate: str) -> str:
    """If any `_CASE_NAME_INTRO_VERBS` token appears in the candidate,
    drop everything up to and including the RIGHTMOST occurrence.

    This is the citation-introduction trim — different from the
    leading-edge strip done by `_strip_leading_signals`. Bluebook
    R1.2 signals + R10.7 subsequent-history connectors live at the
    leading edge; introductory verbs (`citing`, `quoting`,
    `holding`, ...) can appear anywhere in the surrounding prose.
    """
    lower = candidate.lower()
    best_cut = -1
    for token in _CASE_NAME_INTRO_VERBS:
        idx = lower.rfind(token)
        if idx >= 0:
            cut = idx + len(token)
            if cut > best_cut:
                best_cut = cut
    if best_cut < 0:
        return candidate
    return candidate[best_cut:].lstrip()


# ---------------------------------------------------------------------------
# Sentence-start cache (uses Punkt via _nlp / matchers — DO NOT re-roll)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=64)
def _sentence_starts_cached(text: str) -> tuple[int, ...]:
    """Punkt-derived sentence starts for ``text``."""
    spans = sentence_tokenizer().tokenize_spans(text)
    starts = [0]
    starts.extend(s[0] for s in spans)
    return tuple(sorted(set(starts)))


# ---------------------------------------------------------------------------
# Pin cite + parenthetical extraction
# ---------------------------------------------------------------------------


def _extract_pin_cite(text: str, page_end: int) -> tuple[str | None, int]:
    """If a pin cite immediately follows ``page_end``, return
    ``(pin_cite_str, new_end)``; otherwise ``(None, page_end)``."""
    sub = text[page_end:]
    if not sub:
        return None, page_end
    hit = _pin_head_matcher().find_first(sub)
    if hit is None or hit.start != 0:
        return None, page_end
    pin = hit.groups[1]
    return pin, page_end + hit.end


def _extract_parenthetical(text: str, pos: int) -> tuple[str | None, int]:
    """If a ``(...)`` follows ``text[pos]`` (after optional ws),
    return ``(inner_text, end_of_close_paren)``."""
    sub = text[pos:]
    if not sub:
        return None, pos
    hit = _paren_head_matcher().find_first(sub)
    if hit is None or hit.start != 0:
        return None, pos
    inner = hit.groups[1]
    return inner, pos + hit.end


def _extract_paren_chain(text: str, pos: int) -> list[tuple[str, int]]:
    """Greedily consume every consecutive ``(...)`` parenthetical that
    follows ``text[pos]``. Bluebook stacks them in this order
    (R10.5 / R10.6.1 / R10.6.2):

    - Date paren: ``(2014)`` or ``(5th Cir. 1996)``
    - Weight paren: ``(per curiam)`` / ``(en banc)``
    - Judge paren: ``(Sotomayor, J., dissenting)``
    - Explanatory paren: ``(holding that ...)``

    Returns ``[(inner_text, end_of_close_paren), ...]`` in source order;
    empty list when no paren follows.
    """
    out: list[tuple[str, int]] = []
    p = pos
    while True:
        sub = text[p:]
        if not sub:
            break
        hit = _paren_head_matcher().find_first(sub)
        if hit is None or hit.start != 0:
            break
        out.append((hit.groups[1], p + hit.end))
        p = p + hit.end
    return out


def _select_weight(parens: list[tuple[str, int]]) -> WeightOfAuthority | None:
    """Return the first weight tag found across a chain of parens."""
    for inner, _end in parens:
        role = _classify_paren(inner)
        if role in ("date", "weight", "judge"):
            _, _, w, _ = _parse_parenthetical(inner)
            if w is not None:
                return w
    return None


def _classify_paren(inner: str) -> str:
    """Classify a parenthetical's role per Bluebook R10.5 / R10.6.

    Returns one of ``'date'`` (year and/or court), ``'weight'``
    (standalone ``(per curiam)`` / ``(en banc)`` etc.), ``'judge'``
    (``(Sotomayor, J., dissenting)``), or ``'explanatory'``
    (everything else — ``(holding that ...)`` / ``(quoting ...)`` /
    free-text). Date / weight / judge parens populate dedicated fields
    (``year``, ``court``, ``weight``, ``judges``) and so MUST NOT
    spill into the ``parenthetical`` field — that field is reserved
    for the explanatory paren only.

    A paren is `date` only when its **entire** contents match
    ``_DATE_PAREN_PATTERN`` (optional court abbrev + optional date
    prefix + 4-digit year, anchored start to end). A bare year
    appearing inside otherwise-explanatory text — `(citing the 2009
    statute)`, `(quoting Restatement … (1965))` — does not classify
    the paren as date and so does not pollute the `year` / `court`
    fields. The earlier substring match `_year_matcher().find_first(inner)`
    was the conflation source.
    """
    if _date_paren_matcher().find_first(inner):
        return "date"
    if _weight_only_matcher().find_first(inner):
        return "weight"
    if _judge_matcher().find_first(inner):
        return "judge"
    return "explanatory"


def _parse_parenthetical(
    paren_text: str | None,
) -> tuple[int | None, str | None, WeightOfAuthority | None, tuple[str, ...]]:
    """Return ``(year, court, weight, judges)`` extracted from a
    parenthetical."""
    if not paren_text:
        return None, None, None, ()

    # Year — last 4-digit year in the parenthetical.
    year: int | None = None
    year_hits = _year_matcher().find_all(paren_text)
    if year_hits:
        try:
            year = int(year_hits[-1].text)
        except ValueError:
            year = None

    # Court — longest matching court_db citation_string in the parenthetical.
    court: str | None = None
    court_lookup = court_id_by_citation_string()
    # Sort court strings by length descending so we find the longest
    # match first (e.g. ``S.D.N.Y.`` wins over ``N.Y.``).
    matches: list[tuple[int, str]] = []
    # Limit search to reasonable-length court strings to keep this fast.
    for cs, cid in court_lookup.items():
        if len(cs) >= 3 and cs in paren_text:
            matches.append((len(cs), cid))
    if matches:
        matches.sort(reverse=True)
        court = matches[0][1]

    # Weight of authority.
    weight: WeightOfAuthority | None = None
    weight_hit = _weight_matcher().find_first(paren_text)
    if weight_hit is not None:
        # Find which named group fired by checking each.
        # groups index aligns with declaration order:
        # [whole, en_banc, per_curiam, plurality, memorandum,
        #  dissenting_in_part, concurring_in_part, dissenting, concurring]
        names = (
            "en_banc",
            "per_curiam",
            "plurality",
            "memorandum",
            "dissenting_in_part",
            "concurring_in_part",
            "dissenting",
            "concurring",
        )
        for i, name in enumerate(names, start=1):
            val = weight_hit.groups[i] if i < len(weight_hit.groups) else None
            if val:
                weight = cast("WeightOfAuthority", name)
                break

    # Judges.
    judges: tuple[str, ...] = ()
    judge_hit = _judge_matcher().find_first(paren_text)
    if judge_hit is not None:
        judges_raw = judge_hit.groups[1] if len(judge_hit.groups) > 1 else None
        if judges_raw:
            # Split on `&` for multi-judge benches.
            parts: list[str] = []
            for part in judges_raw.split("&"):
                part = part.strip()
                if part:
                    parts.append(part)
            judges = tuple(parts)

    return year, court, weight, judges


# ---------------------------------------------------------------------------
# Year fallback when parenthetical-less
# ---------------------------------------------------------------------------


def _find_year_after(text: str, pos: int, max_window: int = 60) -> int | None:
    """If a ``(YYYY)`` parenthetical appears within ``max_window`` chars
    of ``pos``, return the year.

    Used when the citation has no parenthetical we matched directly
    (no `_PAREN_HEAD_PATTERN` hit). The match is anchored on a real
    parenthesis-bracketed year — a bare year token in surrounding
    explanatory text (e.g. ``... see Brown, 347 U.S. 483; 2009 was
    the year of ...``) does not qualify and returns None.
    """
    window = text[pos : pos + max_window]
    hit = _year_paren_matcher().find_first(window)
    if hit is None:
        return None
    try:
        # Group 1 is the YYYY capture; groups[0] is the full match.
        return int(hit.groups[1])
    except (TypeError, ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Public extractors
# ---------------------------------------------------------------------------


def extract_case_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[CaseCitation]:
    """Extract every full-form case-law citation from ``text``."""
    if not text:
        return []

    out: list[CaseCitation] = []
    # Right-edge of the most recent anchor we've processed (case OR
    # journal/law). Used as a floor for the next anchor's case-name
    # walk-back so cite N+1 cannot swallow cite N's text.
    prev_anchor_end = 0
    for anchor in _find_anchors(text):
        # Compute paren chain regardless of whether we'll emit — we need
        # the rightmost end to advance prev_anchor_end correctly.
        pin_cite, after_pin = _extract_pin_cite(text, anchor.page_end)
        parens = _extract_paren_chain(text, after_pin)
        rightmost_end = parens[-1][1] if parens else after_pin

        # Skip law/journal reporters — they have separate parsers.
        if _is_journal_only(anchor.reporter) or _is_law_only(anchor.reporter):
            prev_anchor_end = max(prev_anchor_end, rightmost_end)
            continue

        case_name = _extract_case_name(text, anchor.vol_start, prev_end=prev_anchor_end)

        year: int | None = None
        court: str | None = None
        judges: tuple[str, ...] = ()
        explanatory: str | None = None
        # Accumulate the weight as a plain Optional[WeightOfAuthority] —
        # collected via the helper so ty doesn't lose narrowing across the
        # branched assignments inside the paren-chain loop.
        weight = _select_weight(parens)
        for inner, _end in parens:
            role = _classify_paren(inner)
            y, c, _w, j = _parse_parenthetical(inner)
            if role == "date":
                if year is None:
                    year = y
                if court is None:
                    court = c
                if not judges and j:
                    judges = j
            elif role == "judge":
                if not judges and j:
                    judges = j
            elif role == "explanatory":
                if explanatory is None:
                    explanatory = inner

        if year is None:
            # Fallback: look for ``(YYYY)`` close after page.
            year = _find_year_after(text, after_pin)

        if court is None:
            court = _scotus_court_default(anchor.reporter)

        # Span and raw cover only the volume-reporter-page anchor (matching
        # eyecite's contract). The parenthetical / pin-cite are exposed
        # via separate fields.
        normalized = f"{anchor.volume} {anchor.reporter} {anchor.page}"
        if year:
            normalized = f"{normalized} ({year})"

        out.append(
            CaseCitation(
                raw=text[anchor.vol_start : anchor.page_end],
                normalized=normalized,
                span=(anchor.vol_start, anchor.page_end),
                source_uri=source_uri,
                volume=anchor.volume,
                reporter=anchor.reporter,
                page=anchor.page,
                year=year,
                case_name=case_name,
                court=court,
                pin_cite=pin_cite,
                pin_cite_kind="page" if pin_cite else None,
                parenthetical=explanatory,
                parenthetical_kind="explanatory" if explanatory else None,
                weight=weight,
                judges=judges,
            )
        )
        prev_anchor_end = max(prev_anchor_end, rightmost_end)

    # Dedupe: a single citation may match multiple reporter spellings —
    # keep the longest span at each starting position.
    out.sort(key=lambda c: (c.span[0], -(c.span[1] - c.span[0])))
    deduped: list[CaseCitation] = []
    seen_starts: set[int] = set()
    for c in out:
        if c.span[0] in seen_starts:
            continue
        seen_starts.add(c.span[0])
        deduped.append(c)
    return deduped


# ---------------------------------------------------------------------------
# Reporter classification helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _journal_only_set() -> frozenset[str]:
    """Reporters that are pure journals (not case reporters). We
    detect them via cite_type but for now use journal_abbreviation_set
    keys as the source-of-truth journal universe."""
    from kaos_citations.data._loaders import journal_abbreviation_set

    return journal_abbreviation_set()


@lru_cache(maxsize=1)
def _law_only_set() -> frozenset[str]:
    from kaos_citations.data._loaders import law_reporter_set

    return law_reporter_set()


def _is_journal_only(reporter: str) -> bool:
    return reporter in _journal_only_set()


def _is_law_only(reporter: str) -> bool:
    return reporter in _law_only_set()


# ---------------------------------------------------------------------------
# Short-form / Id / Supra / Reference / Journal extractors
# ---------------------------------------------------------------------------

# ``Id.`` / ``Id. at NN``
_ID_PATTERN = r"\bId\.?(?:\s+at\s+(?P<pin>[*\d]+(?:[-,]\s*\d+)*))?"
# ``supra`` (case insensitive). With optional ``note NN`` and ``at NN``.
_SUPRA_PATTERN = (
    r"(?i)"
    r"\bsupra"
    r"(?:\s+note\s+(?P<note>\d+))?"
    r"(?:\s*,\s*at\s+(?P<pin>[*\d]+))?"
)
# ``CaseName, <vol> <reporter> at <pin>`` short form (R10.9).
_SHORT_CASE_TAIL_PATTERN = (
    r"\A\s*,?\s*"
    r"(?P<vol>\d{1,4})\s+"
    r"(?P<reporter_placeholder>__REPORTER__)\s+"
    r"at\s+(?P<pin>[*\d]+)"
)


@lru_cache(maxsize=1)
def _id_matcher():  # type: ignore[no-untyped-def]
    return regex(_ID_PATTERN)


@lru_cache(maxsize=1)
def _supra_matcher():  # type: ignore[no-untyped-def]
    return regex(_SUPRA_PATTERN)


def extract_case_short_forms(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[Citation]:
    """Extract short-form case + Id. + supra + reference citations.

    For now we ship Id. and supra (the high-frequency cases). Short-
    form ``X, vol reporter at pin`` and reference forms are a follow-on.
    """
    if not text:
        return []
    out: list[Citation] = []

    for m in _id_matcher().find_all(text):
        pin = m.groups[1] if len(m.groups) > 1 else None
        out.append(
            IdCitation(
                raw=m.text,
                normalized=m.text,
                span=(m.start, m.end),
                source_uri=source_uri,
                pin_cite=pin,
                pin_cite_kind="page" if pin else None,
            )
        )

    for m in _supra_matcher().find_all(text):
        # groups: [whole, note, pin]
        note_raw = m.groups[1] if len(m.groups) > 1 else None
        pin = m.groups[2] if len(m.groups) > 2 else None
        try:
            note_number = int(note_raw) if note_raw else None
        except (TypeError, ValueError):
            note_number = None
        out.append(
            SupraCitation(
                raw=m.text,
                normalized=m.text,
                span=(m.start, m.end),
                source_uri=source_uri,
                note_number=note_number,
                pin_cite=pin,
                pin_cite_kind="page" if pin else None,
            )
        )

    out.sort(key=lambda c: c.span[0])
    return out


def extract_journal_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[JournalCitation]:
    """Extract law-review / journal article citations.

    Same shape as case citations but the reporter must be in the
    journals.json universe.
    """
    if not text:
        return []
    out: list[JournalCitation] = []
    for anchor in _find_anchors(text):
        if not _is_journal_only(anchor.reporter):
            continue
        pin_cite, after_pin = _extract_pin_cite(text, anchor.page_end)
        parens = _extract_paren_chain(text, after_pin)
        rightmost_end = parens[-1][1] if parens else after_pin

        year: int | None = None
        explanatory: str | None = None
        for inner, _end in parens:
            role = _classify_paren(inner)
            if role == "date":
                y, _, _, _ = _parse_parenthetical(inner)
                if year is None:
                    year = y
            elif role == "explanatory":
                if explanatory is None:
                    explanatory = inner
            # weight / judge parens don't apply to journals; ignored.
        if year is None:
            year = _find_year_after(text, after_pin)

        normalized = f"{anchor.volume} {anchor.reporter} {anchor.page}"
        if year:
            normalized = f"{normalized} ({year})"
        out.append(
            JournalCitation(
                raw=text[anchor.vol_start : rightmost_end],
                normalized=normalized,
                span=(anchor.vol_start, anchor.page_end),
                source_uri=source_uri,
                volume=anchor.volume,
                journal=anchor.reporter,
                page=anchor.page,
                year=year,
                pin_cite=pin_cite,
                pin_cite_kind="page" if pin_cite else None,
                parenthetical=explanatory,
                parenthetical_kind="explanatory" if explanatory else None,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


def extract_case_family(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[Citation]:
    """One-pass extractor returning every case-family citation (full +
    short-form + journal). Used by the dispatcher to avoid running the
    reporter pass three times."""
    out: list[Citation] = []
    out.extend(extract_case_citations(text, source_uri=source_uri))
    out.extend(extract_case_short_forms(text, source_uri=source_uri))
    out.extend(extract_journal_citations(text, source_uri=source_uri))
    out.sort(key=lambda c: c.span[0])
    return out


__all__ = [
    "extract_case_citations",
    "extract_case_family",
    "extract_case_short_forms",
    "extract_journal_citations",
]
