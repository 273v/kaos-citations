"""Agency adjudications + AG/OLC opinions + agency manuals + bar ethics.

kaos-nlp-core RegexMatcher only — no `re`. Covers Bluebook R14.3 and R14.4:

- Agency adjudications: NLRB, FERC, FCC, FTC, NTSB, BIA, EPA EAB, PTAB, TTAB
- Agency manuals: MPEP, TMEP, POMS
- Attorney General / OLC opinions
- State bar ethics opinions
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatchSpan, regex
from kaos_citations.model import (
    AdjudicatingAgency,
    AgencyAdjudicationCitation,
    AgencyManualCitation,
    BarEthicsOpinionCitation,
    LegalOpinionCitation,
    OpinionAuthority,
)

# ---------------------------------------------------------------------------
# Reporter-style decisions: <volume> <reporter> <page> [(year)]
# ---------------------------------------------------------------------------

# Agency-reporter alternation. Each token is matched as a Rust regex
# substring; we collapse it to a canonical alnum-only key downstream
# to identify the agency.
_AGENCY_REPORTERS: tuple[tuple[str, AdjudicatingAgency], ...] = (
    (r"N\.?L\.?R\.?B\.?", "NLRB"),
    (r"F\.?T\.?C\.?", "FTC"),
    (r"N\.?T\.?S\.?B\.?", "NTSB"),
    (r"E\.?A\.?D\.?", "EPA_EAB"),
    (r"I\.?\s*&\s*N\.?\s*Dec\.?", "BIA"),
    (r"F\.?C\.?C\.?\s*Rcd", "FCC"),
    (r"F\.?C\.?C\.?2d", "FCC"),
)

_REPORTER_DECISION_PATTERN = (
    r"(?i)"
    r"\b(?P<volume>\d{1,4})"
    r"\s+"
    r"(?P<reporter>" + "|".join(rpt for rpt, _ in _AGENCY_REPORTERS) + r")"
    r"\s+"
    r"(?P<page>\d{1,3}(?:,\d{3})+|\d{1,5})"
    r"(?:\s*,\s*(?P<pin>\d{1,3}(?:,\d{3})+|\d{1,5}))?"
    r"(?:\s*\(\s*(?P<authority>A\.?G\.?|BIA|EAB)?\s*(?P<year>\d{4})\s*\))?"
)

_NLRB_SLIP_PATTERN = (
    r"(?i)"
    r"\b(?P<volume>\d{1,4})\s+N\.?L\.?R\.?B\.?\s+No\.?\s+(?P<slip>\d{1,5})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)

_FERC_PARAGRAPH_PATTERN = (
    r"(?i)"
    r"\b(?P<volume>\d{1,4})\s+FERC\s*¶\s*"
    r"(?P<para>\d{1,3}(?:,\d{3})+|\d{4,8})"
    r"(?:\s*\(\s*(?P<year>\d{4})\s*\))?"
)

_PTAB_PATTERN = (
    r"(?i)"
    r"\bAppeal\s+(?P<num>\d{4}-\d{3,7})"
    r"(?:\s*,\s*(?:Application\s+No\.?\s+(?P<app>\d{1,3}/\d{3,4}(?:,\d{3})?)))?"
    r"\s*\(\s*PTAB\s*(?P<year>\d{4})\s*\)"
)

_TTAB_PATTERN = (
    r"(?i)"
    r"\bSer(?:ial)?\.?\s+No\.?\s+(?P<serial>\d{1,3}/\d{3},?\d{0,3})"
    r"\s*\(\s*TTAB\s*(?P<year>\d{4})\s*\)"
)

# Pattern that strips everything except a-z0-9 from a reporter token —
# replaces ``re.sub(r"[^a-z0-9]", "", text.lower())``.
_NON_ALNUM_PATTERN = r"[^a-z0-9]+"

# Pattern that collapses runs of whitespace — replaces
# ``re.sub(r"\s+", " ", text)`` for POMS section normalization.
_WHITESPACE_RUN_PATTERN = r"\s+"


@lru_cache(maxsize=1)
def _reporter_decision_matcher():  # type: ignore[no-untyped-def]
    return regex(_REPORTER_DECISION_PATTERN)


@lru_cache(maxsize=1)
def _nlrb_slip_matcher():  # type: ignore[no-untyped-def]
    return regex(_NLRB_SLIP_PATTERN)


@lru_cache(maxsize=1)
def _ferc_paragraph_matcher():  # type: ignore[no-untyped-def]
    return regex(_FERC_PARAGRAPH_PATTERN)


@lru_cache(maxsize=1)
def _ptab_matcher():  # type: ignore[no-untyped-def]
    return regex(_PTAB_PATTERN)


@lru_cache(maxsize=1)
def _ttab_matcher():  # type: ignore[no-untyped-def]
    return regex(_TTAB_PATTERN)


@lru_cache(maxsize=1)
def _non_alnum_matcher():  # type: ignore[no-untyped-def]
    return regex(_NON_ALNUM_PATTERN)


@lru_cache(maxsize=1)
def _whitespace_run_matcher():  # type: ignore[no-untyped-def]
    return regex(_WHITESPACE_RUN_PATTERN)


def _strip_to_alnum(s: str) -> str:
    """Lowercase + strip non-alphanumerics. Collapses ``F.T.C.`` and
    ``I. & N. Dec.`` to canonical keys for agency classification."""
    return _non_alnum_matcher().replace_all(s.lower(), "")


def _classify_agency(reporter: str) -> AdjudicatingAgency:
    norm = _strip_to_alnum(reporter)
    if "fccrcd" in norm or "fcc2d" in norm:
        return "FCC"
    if "nlrb" in norm:
        return "NLRB"
    if "ftc" in norm:
        return "FTC"
    if "ntsb" in norm:
        return "NTSB"
    if "ead" in norm:
        return "EPA_EAB"
    if "indec" in norm or norm == "in":
        return "BIA"
    return "OTHER"


def _normalize_agency_reporter(reporter: str) -> str:
    norm = _strip_to_alnum(reporter)
    if "fccrcd" in norm:
        return "FCC Rcd"
    if "fcc2d" in norm:
        return "F.C.C.2d"
    if "nlrb" in norm:
        return "N.L.R.B."
    if "ftc" in norm:
        return "F.T.C."
    if "ntsb" in norm:
        return "N.T.S.B."
    if "ead" in norm:
        return "E.A.D."
    if "indec" in norm:
        return "I. & N. Dec."
    return reporter


def _parse_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return None


def iter_agency_adjudication_matches(text: str) -> Iterator[RegexMatchSpan]:
    yield from _reporter_decision_matcher().find_all(text)


def extract_agency_adjudication_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[AgencyAdjudicationCitation]:
    if not text:
        return []
    out: list[AgencyAdjudicationCitation] = []
    seen: set[tuple[int, int]] = set()

    # Reporter-style: groups [whole, volume, reporter, page, pin, authority, year]
    for m in _reporter_decision_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        volume_str = m.groups[1] if len(m.groups) > 1 else None
        reporter = m.groups[2] if len(m.groups) > 2 else ""
        page_str = m.groups[3] if len(m.groups) > 3 else None
        authority_raw = m.groups[5] if len(m.groups) > 5 else None
        year = _parse_int(m.groups[6] if len(m.groups) > 6 else None)
        agency = _classify_agency(reporter)
        norm_rpt = _normalize_agency_reporter(reporter)
        volume = _parse_int(volume_str)
        page = _parse_int(page_str)
        decision_authority = authority_raw.upper() if authority_raw else None
        if decision_authority == "AG":
            decision_authority = "A.G."
        normalized = f"{volume} {norm_rpt} {page_str}"
        if year:
            authority_part = f"{decision_authority} {year}" if decision_authority else f"{year}"
            normalized = f"{normalized} ({authority_part})"
        out.append(
            AgencyAdjudicationCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                agency=agency,
                volume=volume,
                reporter=norm_rpt,
                page=page,
                year=year,
                decision_authority=decision_authority,
            )
        )

    # NLRB slip-style
    for m in _nlrb_slip_matcher().find_all(text):
        span = (m.start, m.end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        volume = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        slip = m.groups[2] if len(m.groups) > 2 else ""
        date = m.groups[3] if len(m.groups) > 3 else None
        normalized = f"{volume} N.L.R.B. No. {slip}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            AgencyAdjudicationCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                agency="NLRB",
                volume=volume,
                reporter="N.L.R.B.",
                slip_number=slip,
                exact_date=date,
            )
        )

    # FERC paragraph: groups [whole, volume, para, year]
    for m in _ferc_paragraph_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        volume = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        para_str = m.groups[2] if len(m.groups) > 2 else ""
        paragraph = _parse_int(para_str)
        year = _parse_int(m.groups[3] if len(m.groups) > 3 else None)
        normalized = f"{volume} FERC ¶ {para_str}"
        if year:
            normalized = f"{normalized} ({year})"
        out.append(
            AgencyAdjudicationCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                agency="FERC",
                volume=volume,
                reporter="FERC ¶",
                paragraph=paragraph,
                year=year,
            )
        )

    # PTAB: groups [whole, num, app, year]
    for m in _ptab_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        year = _parse_int(m.groups[3] if len(m.groups) > 3 else None)
        out.append(
            AgencyAdjudicationCitation(
                raw=m.text,
                normalized=f"Appeal {num} (PTAB {year})" if year else f"Appeal {num} (PTAB)",
                span=span,
                source_uri=source_uri,
                agency="PTAB",
                docket_number=num,
                year=year,
            )
        )

    # TTAB: groups [whole, serial, year]
    for m in _ttab_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        serial = m.groups[1] if len(m.groups) > 1 else ""
        year = _parse_int(m.groups[2] if len(m.groups) > 2 else None)
        out.append(
            AgencyAdjudicationCitation(
                raw=m.text,
                normalized=(
                    f"Ser. No. {serial} (TTAB {year})" if year else f"Ser. No. {serial} (TTAB)"
                ),
                span=span,
                source_uri=source_uri,
                agency="TTAB",
                docket_number=serial,
                year=year,
            )
        )

    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Agency manuals (MPEP / TMEP / POMS)
# ---------------------------------------------------------------------------

_MPEP_PATTERN = (
    r"(?i)"
    r"\b(?:Manual\s+of\s+Patent\s+Examining\s+Procedure|MPEP)\s*"
    r"(?:§|Section\s+|sec\.?\s+)?\s*"
    r"(?P<section>\d+(?:\.\d+)?(?:\([a-zA-Z0-9]+\))*)"
)

_TMEP_PATTERN = (
    r"(?i)"
    r"\b(?:Trademark\s+Manual\s+of\s+Examining\s+Procedure|TMEP)\s*"
    r"(?:§|Section\s+|sec\.?\s+)?\s*"
    r"(?P<section>\d+(?:\.\d+)?(?:\([a-zA-Z0-9]+\))*)"
)

_POMS_PATTERN = (
    r"(?i)"
    r"\b(?:Program\s+Operations?\s+Manual\s+System|POMS)\s*"
    r"(?:§|Section\s+)?\s*"
    r"(?P<section>[A-Z]{1,3}\s*\d{2,5}\.\d{1,5}(?:\.\d+)?)"
)


@lru_cache(maxsize=1)
def _mpep_matcher():  # type: ignore[no-untyped-def]
    return regex(_MPEP_PATTERN)


@lru_cache(maxsize=1)
def _tmep_matcher():  # type: ignore[no-untyped-def]
    return regex(_TMEP_PATTERN)


@lru_cache(maxsize=1)
def _poms_matcher():  # type: ignore[no-untyped-def]
    return regex(_POMS_PATTERN)


def extract_agency_manual_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[AgencyManualCitation]:
    if not text:
        return []
    out: list[AgencyManualCitation] = []
    ws = _whitespace_run_matcher()
    for m in _mpep_matcher().find_all(text):
        section = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            AgencyManualCitation(
                raw=m.text,
                normalized=f"MPEP § {section}",
                span=(m.start, m.end),
                source_uri=source_uri,
                manual_id="MPEP",
                section=section,
            )
        )
    for m in _tmep_matcher().find_all(text):
        section = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            AgencyManualCitation(
                raw=m.text,
                normalized=f"TMEP § {section}",
                span=(m.start, m.end),
                source_uri=source_uri,
                manual_id="TMEP",
                section=section,
            )
        )
    for m in _poms_matcher().find_all(text):
        section_raw = m.groups[1] if len(m.groups) > 1 else ""
        section = ws.replace_all(section_raw.strip(), " ")
        out.append(
            AgencyManualCitation(
                raw=m.text,
                normalized=f"POMS § {section}",
                span=(m.start, m.end),
                source_uri=source_uri,
                manual_id="POMS",
                section=section,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# AG / OLC opinions
# ---------------------------------------------------------------------------

_OPINION_PATTERN = (
    r"(?i)"
    r"\b(?P<volume>\d{1,3})\s+Op\.?\s*"
    r"(?P<authority>Att'?y\s*Gen\.?|O\.?L\.?C\.?)"
    r"\s+(?P<page>\d{1,5})"
    r"(?:\s*\(\s*(?P<year>\d{4})\s*\))?"
)


@lru_cache(maxsize=1)
def _opinion_matcher():  # type: ignore[no-untyped-def]
    return regex(_OPINION_PATTERN)


def extract_legal_opinion_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[LegalOpinionCitation]:
    if not text:
        return []
    out: list[LegalOpinionCitation] = []
    for m in _opinion_matcher().find_all(text):
        # groups: [whole, volume, authority, page, year]
        volume = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        authority_raw = (m.groups[2] or "").lower() if len(m.groups) > 2 else ""
        page = _parse_int(m.groups[3] if len(m.groups) > 3 else None)
        year = _parse_int(m.groups[4] if len(m.groups) > 4 else None)
        authority: OpinionAuthority = "AG" if "att" in authority_raw else "OLC"
        prefix = "Op. Att'y Gen." if authority == "AG" else "Op. O.L.C."
        normalized = f"{volume} {prefix} {page}"
        if year:
            normalized = f"{normalized} ({year})"
        out.append(
            LegalOpinionCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                authority=authority,
                volume=volume,
                page=page,
                year=year,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# State bar ethics opinions
# ---------------------------------------------------------------------------

_BAR_ETHICS_PATTERN = (
    r"(?i)"
    r"\b(?P<state>"
    r"ABA"
    r"|(?:N\.Y|Cal|Tex|Fla|Ill|Mass|D\.C|Pa|N\.J|Ohio|Ga|Va|N\.C|Mich|Wash|Or|Conn)\.?"
    r")"
    r"[^\n]{0,80}?"
    r"(?:Comm(?:ittee)?[^\n]{0,40}?(?:Ethics|Pro\.?\s*Resp\.?))"
    r"[^\n]{0,40}?"
    r"\b(?:Formal\s+)?Op(?:inion)?\.?\s*(?:No\.?\s*)?(?P<num>[\dA-Za-z\-]+)"
    r"(?:\s*\(\s*(?P<year>\d{4})\s*\))?"
)


@lru_cache(maxsize=1)
def _bar_ethics_matcher():  # type: ignore[no-untyped-def]
    return regex(_BAR_ETHICS_PATTERN)


def extract_bar_ethics_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[BarEthicsOpinionCitation]:
    if not text:
        return []
    out: list[BarEthicsOpinionCitation] = []
    for m in _bar_ethics_matcher().find_all(text):
        # groups: [whole, state, num, year]
        state_raw = (m.groups[1] or "").rstrip(".") if len(m.groups) > 1 else ""
        num = m.groups[2] if len(m.groups) > 2 else ""
        year = _parse_int(m.groups[3] if len(m.groups) > 3 else None)
        normalized = f"{state_raw} Bar Ethics Op. {num}"
        if year:
            normalized = f"{normalized} ({year})"
        out.append(
            BarEthicsOpinionCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                state=state_raw,
                opinion_number=num,
                year=year,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


__all__ = [
    "extract_agency_adjudication_citations",
    "extract_agency_manual_citations",
    "extract_bar_ethics_citations",
    "extract_legal_opinion_citations",
    "iter_agency_adjudication_matches",
]
