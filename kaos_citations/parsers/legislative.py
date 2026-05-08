"""Legislative + Public Law + Restatement + Uniform Act parser — kaos-nlp-core, no `re`.

Covers Bluebook R12-R15 for the highest-volume Tier-1 legislative
materials:

- **Public Laws / Statutes at Large**: ``Pub. L. No. 111-148``,
  ``111-148, § 1501``, ``124 Stat. 119``
- **Bills**: ``H.R. 1``, ``S. 1234``, ``H.R.J. Res. 5``, ``S.J. Res. 7``,
  ``H. Con. Res. 12``, etc.
- **Reports**: ``H.R. Rep. No. 117-89``, ``H.R. Conf. Rep. No. 115-466``
- **Congressional Record**: ``168 Cong. Rec. H1234``, etc.
- **Restatements**: ``Restatement (Second) of Torts § 402A``
- **Uniform Acts / Model Codes**: ``U.C.C. § 2-207``, ``M.P.C. § 2.02``
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Literal, cast

from kaos_citations.matchers import RegexMatcher, RegexMatchSpan, regex
from kaos_citations.model import (
    LegislativeCitation,
    LegislativeDocKind,
    PublicLawCitation,
    RestatementCitation,
    RestatementSeries,
    UniformActCitation,
    UniformActShort,
)

# ---------------------------------------------------------------------------
# Public Laws
# ---------------------------------------------------------------------------

_PUB_LAW_PATTERN = (
    r"(?i)"
    r"\bPub(?:lic)?\.?\s*L(?:aw)?\.?\s*(?:No\.?\s*)?"
    r"(?P<plnum>\d{1,3}-\d{1,4})"
    r"(?:\s*,?\s*§\s*(?P<section>[\dA-Z\.\-()]{1,40}))?"
    r"(?:\s*,?\s*(?P<stat_vol>\d{1,4})\s*Stat\.?\s*(?P<stat_pg>[\d,]+))?"
)


@lru_cache(maxsize=1)
def _pub_law_matcher():  # type: ignore[no-untyped-def]
    return regex(_PUB_LAW_PATTERN)


def _parse_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return None


def iter_public_law_matches(text: str) -> Iterator[RegexMatchSpan]:
    yield from _pub_law_matcher().find_all(text)


def extract_public_law_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[PublicLawCitation]:
    if not text:
        return []
    out: list[PublicLawCitation] = []
    for match in iter_public_law_matches(text):
        # groups: [whole, plnum, section, stat_vol, stat_pg]
        plnum = match.groups[1] if len(match.groups) > 1 else ""
        if not plnum:
            continue
        congress = _parse_int(plnum.split("-")[0])
        section = match.groups[2] if len(match.groups) > 2 else None
        stat_vol = _parse_int(match.groups[3] if len(match.groups) > 3 else None)
        stat_pg = _parse_int(match.groups[4] if len(match.groups) > 4 else None)
        norm = f"Pub. L. No. {plnum}"
        if section:
            norm = f"{norm}, § {section}"
        if stat_vol and stat_pg:
            norm = f"{norm}, {stat_vol} Stat. {stat_pg}"
        out.append(
            PublicLawCitation(
                raw=match.text,
                normalized=norm,
                span=(match.start, match.end),
                source_uri=source_uri,
                congress=congress,
                public_law_number=plnum,
                section=section,
                stat_volume=stat_vol,
                stat_page=stat_pg,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Bills + Resolutions — order matters; longer prefixes first
# ---------------------------------------------------------------------------

# Bill / resolution patterns. Note: Rust regex doesn't support
# negative lookahead/lookbehind. We post-filter ``H.R.``/``S.`` bills
# below to (a) reject ``S.`` inside reporter abbreviations like ``U.S.``
# and (b) reject ``H.R. <digits>`` when followed by ``Rep.``/``Conf.``/etc.
_BILL_PATTERN_DEFS: tuple[tuple[str, LegislativeDocKind], ...] = (
    (r"(?i)\bH\.?\s*R?\.?\s*J\.?\s*Res\.?\s*(?P<num>\d{1,5})\b", "house_joint_resolution"),
    (r"(?i)\bS\.?\s*J\.?\s*Res\.?\s*(?P<num>\d{1,5})\b", "senate_joint_resolution"),
    (r"(?i)\bH\.?\s*Con\.?\s*Res\.?\s*(?P<num>\d{1,5})\b", "house_concurrent_resolution"),
    (r"(?i)\bS\.?\s*Con\.?\s*Res\.?\s*(?P<num>\d{1,5})\b", "senate_concurrent_resolution"),
    (r"(?i)\bH\.?\s*Res\.?\s*(?P<num>\d{1,5})\b", "house_resolution"),
    (r"(?i)\bS\.?\s*Res\.?\s*(?P<num>\d{1,5})\b", "senate_resolution"),
    # Plain bills — must come last and need post-filter for false-positives.
    (r"(?i)\bH\.?\s*R\.?\s+(?P<num>\d{1,5})\b", "house_bill"),
    (r"(?i)\bS\.\s+(?P<num>\d{1,5})\b", "senate_bill"),
)


@lru_cache(maxsize=1)
def _bill_matchers() -> tuple[tuple[LegislativeDocKind, RegexMatcher], ...]:
    return tuple((kind, regex(pat)) for pat, kind in _BILL_PATTERN_DEFS)


# Patterns that MUST NOT directly follow ``H.R. \d``/``S. \d`` — these
# would mean we matched the bill prefix of a longer report/document form.
_BILL_FOLLOWUP_REJECT_PATTERN = r"(?i)\A\s*(?:Rep|Conf|Doc|J|Con|Res)\."


@lru_cache(maxsize=1)
def _bill_followup_matcher():  # type: ignore[no-untyped-def]
    return regex(_BILL_FOLLOWUP_REJECT_PATTERN)


def _is_inside_reporter_abbrev(text: str, pos: int) -> bool:
    """Return True when ``text[pos]`` is an ``S`` immediately preceded by
    ``[A-Za-z].`` — i.e. it's the trailing letter of an abbreviation
    like ``U.S.``, ``F.R.D.``, ``L.R.B.``. Replaces the regex negative
    lookbehind ``(?<![A-Z]\\.)`` that Rust regex doesn't support."""
    if pos < 2:
        return False
    return text[pos - 1] == "." and text[pos - 2].isalpha()


_CONGRESS_TAIL_PATTERN = (
    r"(?i)\A\s*\(?\s*(?P<congress>\d{1,3})(?:st|nd|rd|th)\s+Cong\."
    r"(?:\s+(?P<year>\d{4}))?\s*\)?"
)


@lru_cache(maxsize=1)
def _congress_tail_matcher():  # type: ignore[no-untyped-def]
    return regex(_CONGRESS_TAIL_PATTERN)


def _consume_congress_tail(text: str, end_pos: int) -> tuple[int, int | None, int | None]:
    sub = text[end_pos:]
    if not sub:
        return end_pos, None, None
    hit = _congress_tail_matcher().find_first(sub)
    if hit is None or hit.start != 0:
        return end_pos, None, None
    return end_pos + hit.end, _parse_int(hit.groups[1]), _parse_int(hit.groups[2])


# ---------------------------------------------------------------------------
# Reports + Documents
# ---------------------------------------------------------------------------

_REPORT_PATTERN_DEFS: tuple[tuple[str, LegislativeDocKind], ...] = (
    (
        r"(?i)\bH\.?\s*R\.?\s*Conf\.?\s*Rep\.?\s*(?:No\.?\s*)?(?P<num>\d{1,3}-\d{1,4})",
        "conference_report",
    ),
    (r"(?i)\bH\.?\s*R\.?\s*Rep\.?\s*(?:No\.?\s*)?(?P<num>\d{1,3}-\d{1,4})", "house_report"),
    (r"(?i)\bS\.?\s*Rep\.?\s*(?:No\.?\s*)?(?P<num>\d{1,3}-\d{1,4})", "senate_report"),
    (r"(?i)\bH\.?\s*Doc\.?\s*(?:No\.?\s*)?(?P<num>\d{1,3}-\d{1,4})", "house_document"),
    (r"(?i)\bS\.?\s*Doc\.?\s*(?:No\.?\s*)?(?P<num>\d{1,3}-\d{1,4})", "senate_document"),
)


@lru_cache(maxsize=1)
def _report_matchers() -> tuple[tuple[LegislativeDocKind, RegexMatcher], ...]:
    return tuple((kind, regex(pat)) for pat, kind in _REPORT_PATTERN_DEFS)


# ---------------------------------------------------------------------------
# Congressional Record
# ---------------------------------------------------------------------------

_CONG_REC_PATTERN = (
    r"(?i)"
    r"\b(?P<volume>\d{1,4})\s*Cong\.?\s*Rec\.?\s*"
    r"(?:"
    r"(?P<chamber>[HSED])(?P<page_d>\d{1,5})"
    r"|(?P<page_b>\d{1,3}(?:,\d{3})+|\d{1,5})"
    r")"
)


@lru_cache(maxsize=1)
def _cong_rec_matcher():  # type: ignore[no-untyped-def]
    return regex(_CONG_REC_PATTERN)


def _normalize_legislative_doc_prefix(kind: LegislativeDocKind, num: str) -> str:
    forms = {
        "house_bill": f"H.R. {num}",
        "senate_bill": f"S. {num}",
        "house_joint_resolution": f"H.R.J. Res. {num}",
        "senate_joint_resolution": f"S.J. Res. {num}",
        "house_concurrent_resolution": f"H. Con. Res. {num}",
        "senate_concurrent_resolution": f"S. Con. Res. {num}",
        "house_resolution": f"H. Res. {num}",
        "senate_resolution": f"S. Res. {num}",
        "house_report": f"H.R. Rep. No. {num}",
        "senate_report": f"S. Rep. No. {num}",
        "conference_report": f"H.R. Conf. Rep. No. {num}",
        "house_document": f"H. Doc. No. {num}",
        "senate_document": f"S. Doc. No. {num}",
    }
    return forms.get(kind, f"{kind} {num}")


def extract_legislative_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[LegislativeCitation]:
    if not text:
        return []

    out: list[LegislativeCitation] = []
    seen: set[tuple[int, int]] = set()
    followup_matcher = _bill_followup_matcher()

    # Bills + resolutions
    for kind, matcher in _bill_matchers():
        for m in matcher.find_all(text):
            # Lookbehind replacement: skip ``S.``/``H.R.`` inside
            # reporter-abbrev contexts like ``U.S. 436``.
            if kind in {"senate_bill", "house_bill"} and _is_inside_reporter_abbrev(text, m.start):
                continue
            # Lookahead replacement: skip when the captured prefix is
            # actually the start of a longer ``H.R. Rep.``/``S. Rep.`` etc.
            if kind in {"senate_bill", "house_bill"}:
                tail = text[m.end :]
                rejected = followup_matcher.find_first(tail)
                if rejected is not None and rejected.start == 0:
                    continue
            num = m.groups[1] if len(m.groups) > 1 else ""
            if not num:
                continue
            end_pos, congress, year = _consume_congress_tail(text, m.end)
            span = (m.start, end_pos)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            out.append(
                LegislativeCitation(
                    raw=text[span[0] : span[1]],
                    normalized=_normalize_legislative_doc_prefix(kind, num),
                    span=span,
                    source_uri=source_uri,
                    doc_kind=kind,
                    congress=congress,
                    number=num,
                    year=year,
                )
            )

    # Reports + documents
    for kind, matcher in _report_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            num = m.groups[1] if len(m.groups) > 1 else ""
            if not num:
                continue
            congress = _parse_int(num.split("-")[0])
            out.append(
                LegislativeCitation(
                    raw=m.text,
                    normalized=_normalize_legislative_doc_prefix(kind, num),
                    span=span,
                    source_uri=source_uri,
                    doc_kind=kind,
                    congress=congress,
                    number=num,
                )
            )

    # Cong. Rec.
    for m in _cong_rec_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        # groups: [whole, volume, chamber, page_d, page_b]
        volume = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        chamber_raw = m.groups[2] if len(m.groups) > 2 else None
        chamber: Literal["H", "S", "E", "D"] | None
        if chamber_raw:
            chamber = cast('Literal["H", "S", "E", "D"]', chamber_raw.upper())
            page = _parse_int(m.groups[3] if len(m.groups) > 3 else None)
            doc_kind: LegislativeDocKind = "cong_record_daily"
            normalized = f"{volume} Cong. Rec. {chamber}{page}"
        else:
            chamber = None
            page = _parse_int(m.groups[4] if len(m.groups) > 4 else None)
            doc_kind = "cong_record_bound"
            normalized = f"{volume} Cong. Rec. {page:,}" if page is not None else m.text
        out.append(
            LegislativeCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind=doc_kind,
                page=page,
                chamber_page_prefix=chamber,
            )
        )

    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Restatements
# ---------------------------------------------------------------------------

_RESTATEMENT_PATTERN = (
    r"(?i)"
    r"\bRestatement\s*\(\s*"
    r"(?P<series>First|Second|Third|Fourth|1st|2d|3d|4th)"
    r"\s*\)\s*of\s+"
    r"(?P<subject>[A-Z][A-Za-z\s\-,&]+?)"
    r"\s+§\s*"
    r"(?P<section>\d+[A-Z]?(?:\.\d+)?(?:\([a-zA-Z0-9]+\))*)"
    r"(?:\s+cmt\.?\s+(?P<cmt>[a-z]))?"
    r"(?:\s+illus\.?\s+(?P<illus>\d+))?"
    r"(?:\s+reporters'?\s+note(?P<rn>))?"
)


@lru_cache(maxsize=1)
def _restatement_matcher():  # type: ignore[no-untyped-def]
    return regex(_RESTATEMENT_PATTERN)


_SERIES_NORMALIZED: dict[str, RestatementSeries] = {
    "first": "First",
    "1st": "First",
    "second": "Second",
    "2d": "Second",
    "third": "Third",
    "3d": "Third",
    "fourth": "Fourth",
    "4th": "Fourth",
}


def extract_restatement_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[RestatementCitation]:
    if not text:
        return []
    out: list[RestatementCitation] = []
    for m in _restatement_matcher().find_all(text):
        # groups: [whole, series, subject, section, cmt, illus, rn]
        series_raw = (m.groups[1] or "").lower()
        series = _SERIES_NORMALIZED.get(series_raw, "Second")
        subject = (m.groups[2] or "").strip().rstrip(",")
        section = m.groups[3] or ""
        cmt = m.groups[4] if len(m.groups) > 4 else None
        illus_raw = m.groups[5] if len(m.groups) > 5 else None
        illus = _parse_int(illus_raw)
        # rn group exists in m.groups when the optional group matched
        # (returns "" for empty match), absent when no match.
        rn_raw = m.groups[6] if len(m.groups) > 6 else None
        is_rn = rn_raw is not None
        norm = f"Restatement ({series}) of {subject} § {section}"
        if cmt:
            norm = f"{norm} cmt. {cmt}"
        if illus:
            norm = f"{norm} illus. {illus}"
        if is_rn:
            norm = f"{norm} reporter's note"
        out.append(
            RestatementCitation(
                raw=m.text,
                normalized=norm,
                span=(m.start, m.end),
                source_uri=source_uri,
                series=series,
                subject=subject,
                section=section,
                comment_letter=cmt,
                illustration_number=illus,
                is_reporters_note=is_rn,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Uniform Acts / Model Codes
# ---------------------------------------------------------------------------

_UNIFORM_ACT_DEFS: tuple[tuple[str, UniformActShort, str], ...] = (
    (r"(?i)\bU\.?C\.?C\.?\s*§\s*(?P<sec>SEC_TAIL)", "U.C.C.", "U.C.C."),
    (r"(?i)\bU\.?P\.?C\.?\s*§\s*(?P<sec>SEC_TAIL)", "U.P.C.", "U.P.C."),
    (r"(?i)\bU\.?T\.?C\.?\s*§\s*(?P<sec>SEC_TAIL)", "U.T.C.", "U.T.C."),
    (r"(?i)\bU\.?A\.?A\.?\s*§\s*(?P<sec>SEC_TAIL)", "U.A.A.", "U.A.A."),
    (r"(?i)\bU\.?E\.?T\.?A\.?\s*§\s*(?P<sec>SEC_TAIL)", "U.E.T.A.", "U.E.T.A."),
    (r"(?i)\bU\.?F\.?T\.?A\.?\s*§\s*(?P<sec>SEC_TAIL)", "U.F.T.A.", "U.F.T.A."),
    (r"(?i)\bM\.?P\.?C\.?\s*§\s*(?P<sec>SEC_TAIL)", "M.P.C.", "M.P.C."),
    (r"(?i)\bM\.?B\.?C\.?A\.?\s*§\s*(?P<sec>SEC_TAIL)", "M.B.C.A.", "M.B.C.A."),
)

# Uniform-act section grammar — alphanumerics, hyphens, parens, and
# dotted segments. Substituted into the patterns above.
_UNIFORM_SECTION_TAIL = r"[\d\-A-Za-z\(\)]+(?:\.[\d\-A-Za-z\(\)]+)*"


@lru_cache(maxsize=1)
def _uniform_act_matchers() -> tuple[tuple[UniformActShort, str, RegexMatcher], ...]:
    return tuple(
        (short, display, regex(pat.replace("SEC_TAIL", _UNIFORM_SECTION_TAIL)))
        for pat, short, display in _UNIFORM_ACT_DEFS
    )


def extract_uniform_act_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[UniformActCitation]:
    if not text:
        return []
    out: list[UniformActCitation] = []
    seen: set[tuple[int, int]] = set()
    for short, display, matcher in _uniform_act_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if span in seen:
                continue
            seen.add(span)
            section = m.groups[1] if len(m.groups) > 1 else ""
            if not section:
                continue
            out.append(
                UniformActCitation(
                    raw=m.text,
                    normalized=f"{display} § {section}",
                    span=span,
                    source_uri=source_uri,
                    act_short=short,
                    section=section,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


__all__ = [
    "extract_legislative_citations",
    "extract_public_law_citations",
    "extract_restatement_citations",
    "extract_uniform_act_citations",
    "iter_public_law_matches",
]
