"""Statute + Federal Register extractor — kaos-nlp-core, NO eyecite.

Native implementation backed by:

- ``law_reporter_fst`` (vendored ``laws.json``) — for statute / code
  reporter detection (U.S.C., I.R.C., state codes).
- ``regex(...)`` — a small RegexMatcher for the `<title> <code> § <section>`
  template plus the Federal Register form ``<vol> Fed. Reg. <page>``.

Output kinds:

- :class:`StatuteCitation` for U.S.C. / I.R.C. / state codes / U.S.C.A. /
  U.S.C.S.
- :class:`FederalRegisterCitation` for ``Fed. Reg.``
- (CFR is its own parser — see :mod:`kaos_citations.parsers.cfr`.)
"""

from __future__ import annotations

from functools import lru_cache

from kaos_citations.matchers import regex
from kaos_citations.model import (
    Citation,
    FederalRegisterCitation,
    StatuteCitation,
)

# ---------------------------------------------------------------------------
# U.S.C. and friends
# ---------------------------------------------------------------------------

# ``42 U.S.C. § 1983``, ``42 U.S.C.A. § 1983 (West 2024)``, ``42 U.S.C.S. § 1983``,
# ``15 U.S.C. § 78j(b)``, ``17 U.S.C. §§ 101-105``, ``26 U.S.C. § 501(c)(3)``.
_USC_SECTION = (
    r"[0-9]+(?:\.[0-9]+)*"
    r"(?:[-A-Za-z][A-Za-z0-9-]*)?"
    r"(?:\([A-Za-z0-9]+\))*"
)

_USC_PATTERN = (
    r"(?i)"
    r"\b(?P<title>[1-9][0-9]?)\s+"
    r"(?P<code>U\.?\s*S\.?\s*C\.?(?:\s*A\.?|\s*S\.?)?)\s*"
    r"(?:§§?\s*|sec(?:tion)?s?\.?\s+)"
    r"(?P<section>" + _USC_SECTION + r")"
)

# I.R.C. § 501(c)(3)
_IRC_PATTERN = (
    r"(?i)"
    r"\bI\.?R\.?C\.?\s*"
    r"(?:§§?\s*|sec(?:tion)?\.?\s+)"
    r"(?P<section>" + _USC_SECTION + r")"
)

# Federal Register: ``88 Fed. Reg. 12,345 (Mar. 1, 2023)``
_FED_REG_PATTERN = (
    r"(?i)"
    r"\b(?P<volume>\d{1,4})\s+Fed\.?\s*Reg\.?\s+"
    r"(?P<page>\d{1,3}(?:,\d{3})+|\d{1,6})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)


def _normalize_code(raw: str) -> str:
    """Map any USC spelling to canonical form.

    ``U.S.C.`` / ``U.S.C.A.`` / ``U.S.C.S.`` are distinct; the first
    is the official US Code, the others are West / Lexis annotated
    editions. We preserve the variant.
    """
    compact = "".join(raw.upper().split()).rstrip(".")
    if compact == "USC":
        return "U.S.C."
    if compact == "USCA":
        return "U.S.C.A."
    if compact == "USCS":
        return "U.S.C.S."
    return raw.strip()


@lru_cache(maxsize=1)
def _usc_matcher():  # type: ignore[no-untyped-def]
    return regex(_USC_PATTERN)


@lru_cache(maxsize=1)
def _irc_matcher():  # type: ignore[no-untyped-def]
    return regex(_IRC_PATTERN)


@lru_cache(maxsize=1)
def _fed_reg_matcher():  # type: ignore[no-untyped-def]
    return regex(_FED_REG_PATTERN)


def _parse_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return None


def extract_law_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[Citation]:
    """Extract every statute / Federal Register citation from ``text``."""
    if not text:
        return []

    results: list[Citation] = []
    seen: set[tuple[int, int]] = set()

    # USC family (U.S.C. / U.S.C.A. / U.S.C.S.)
    for m in _usc_matcher().find_all(text):
        # groups: [whole, title, code, section]
        title = m.groups[1] if len(m.groups) > 1 else ""
        code_raw = m.groups[2] if len(m.groups) > 2 else ""
        section = m.groups[3] if len(m.groups) > 3 else ""
        if not (title and code_raw and section):
            continue
        code = _normalize_code(code_raw)
        normalized = f"{title} {code} § {section}"
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        results.append(
            StatuteCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                title=title,
                code=code,
                section=section,
            )
        )

    # I.R.C. — Title 26 short form.
    for m in _irc_matcher().find_all(text):
        section = m.groups[1] if len(m.groups) > 1 else ""
        if not section:
            continue
        span = (m.start, m.end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        results.append(
            StatuteCitation(
                raw=m.text,
                normalized=f"I.R.C. § {section}",
                span=span,
                source_uri=source_uri,
                title="26",
                code="I.R.C.",
                section=section,
            )
        )

    # Federal Register
    for m in _fed_reg_matcher().find_all(text):
        # groups: [whole, volume, page, date]
        volume = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        page = _parse_int(m.groups[2] if len(m.groups) > 2 else None)
        date = m.groups[3] if len(m.groups) > 3 else None
        if volume is None or page is None:
            continue
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        normalized = f"{volume} Fed. Reg. {page:,}"
        if date:
            normalized = f"{normalized} ({date})"
        results.append(
            FederalRegisterCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                volume=volume,
                page=page,
                exact_date=date,
            )
        )

    results.sort(key=lambda c: c.span[0])
    return results


def extract_statute_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[StatuteCitation]:
    """Filter law citations to only :class:`StatuteCitation`."""
    return [
        c
        for c in extract_law_citations(text, source_uri=source_uri)
        if isinstance(c, StatuteCitation)
    ]


def extract_federal_register_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FederalRegisterCitation]:
    """Filter law citations to only :class:`FederalRegisterCitation`."""
    return [
        c
        for c in extract_law_citations(text, source_uri=source_uri)
        if isinstance(c, FederalRegisterCitation)
    ]


__all__ = [
    "extract_federal_register_citations",
    "extract_law_citations",
    "extract_statute_citations",
]
