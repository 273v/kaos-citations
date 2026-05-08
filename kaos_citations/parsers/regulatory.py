"""Regulatory + executive parser — kaos-nlp-core, no `re`.

Coverage:

- Treasury Regulations: ``Treas. Reg. § 1.501(c)(3)-1``,
  ``Prop. Treas. Reg. § 1.482-7``, ``Temp. Treas. Reg. § 1.163-9T``
- IRS guidance: ``Rev. Rul.``, ``Rev. Proc.``, ``Notice``,
  ``Announcement``, ``Priv. Ltr. Rul.``, ``T.A.M.``, ``G.C.M.``,
  ``F.S.A.``, ``C.C.A.``, ``T.D.``, ``Internal Revenue Manual``
- Executive Orders / Proclamations / Presidential Memos / Determinations
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatcher, RegexMatchSpan, regex
from kaos_citations.model import (
    ExecutiveActionCitation,
    ExecutiveActionKind,
    IRSGuidanceCitation,
    IRSGuidanceKind,
    TreasuryRegulationCitation,
    TreasuryRegulationStatus,
)

# ---------------------------------------------------------------------------
# Treasury Regulations
# ---------------------------------------------------------------------------

_TREAS_REG_PATTERN = (
    r"(?i)"
    r"\b(?P<status>Prop\.?|Temp\.?|Proposed|Temporary)?\s*"
    r"Treas(?:ury)?\.?\s*Reg(?:ulations?)?\.?\s*"
    r"(?:§|Section\s+|sec\.?\s+)?\s*"
    r"(?P<section>"
    r"\d+\.\d+"
    r"(?:\([a-zA-Z0-9]+\))*"
    r"(?:-\d+[A-Z]*)?"
    r"(?:\([a-zA-Z0-9]+\))*"
    r")"
)


@lru_cache(maxsize=1)
def _treas_reg_matcher():  # type: ignore[no-untyped-def]
    return regex(_TREAS_REG_PATTERN)


def _classify_treas_status(status: str | None) -> TreasuryRegulationStatus:
    if status is None:
        return "final"
    s = status.lower().rstrip(".")
    if s.startswith("prop"):
        return "proposed"
    if s.startswith("temp"):
        return "temporary"
    return "final"


def iter_treasury_regulation_matches(text: str) -> Iterator[RegexMatchSpan]:
    yield from _treas_reg_matcher().find_all(text)


def _normalize_treas(section: str, status: TreasuryRegulationStatus) -> str:
    prefix = {
        "final": "Treas. Reg.",
        "proposed": "Prop. Treas. Reg.",
        "temporary": "Temp. Treas. Reg.",
    }[status]
    return f"{prefix} § {section}"


def extract_treasury_regulation_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[TreasuryRegulationCitation]:
    if not text:
        return []
    out: list[TreasuryRegulationCitation] = []
    for match in iter_treasury_regulation_matches(text):
        # groups: [whole, status, section]
        status_str = match.groups[1] if len(match.groups) > 1 and match.groups[1] else None
        section = match.groups[2] if len(match.groups) > 2 else ""
        if not section:
            continue
        status = _classify_treas_status(status_str)
        out.append(
            TreasuryRegulationCitation(
                raw=match.text,
                normalized=_normalize_treas(section, status),
                span=(match.start, match.end),
                source_uri=source_uri,
                section=section,
                status=status,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# IRS Guidance
# ---------------------------------------------------------------------------

# (pattern, IRSGuidanceKind, normalized_prefix). Order matters — longer
# prefixes (``Rev. Proc.``) must appear before shorter shared prefixes.
_IRS_PREFIX_DEFS: tuple[tuple[str, IRSGuidanceKind, str], ...] = (
    (r"(?i)\bRev\.?\s*Proc\.?\b", "rev_proc", "Rev. Proc."),
    (r"(?i)\bRev\.?\s*Rul\.?\b", "rev_rul", "Rev. Rul."),
    (r"(?i)\bNotice\b", "notice", "Notice"),
    (r"(?i)\bAnnouncement\b", "announcement", "Announcement"),
    (r"(?i)\b(?:Priv\.?\s*Ltr\.?\s*Rul\.?|PLR)\b", "plr", "Priv. Ltr. Rul."),
    (r"(?i)\b(?:Tech\.?\s*Adv\.?\s*Mem\.?|T\.?A\.?M\.?)\b", "tam", "T.A.M."),
    (r"(?i)\b(?:Gen\.?\s*Couns\.?\s*Mem\.?|G\.?C\.?M\.?)\b", "gcm", "G.C.M."),
    (r"(?i)\b(?:Field\s*Serv\.?\s*Adv\.?|F\.?S\.?A\.?)\b", "fsa", "F.S.A."),
    (r"(?i)\b(?:Chief\s*Couns\.?\s*Adv\.?|C\.?C\.?A\.?)\b", "cca", "C.C.A."),
    # T.D. requires a following digit. Rust regex has no lookahead, so
    # we capture the digit and let the caller anchor the body match.
    (r"(?i)\bT\.?D\.?", "td", "T.D."),
    (r"(?i)\bI\.?R\.?B\.?\b", "irb", "I.R.B."),
    (
        r"(?i)\bInternal\s+Revenue\s+Manual\b|\bI\.?\s*R\.?\s*M\.?\b",
        "irm",
        "I.R.M.",
    ),
)


@lru_cache(maxsize=1)
def _irs_prefix_matchers() -> tuple[tuple[IRSGuidanceKind, str, RegexMatcher], ...]:
    return tuple((kind, prefix, regex(pat)) for pat, kind, prefix in _IRS_PREFIX_DEFS)


# IRS document-number tail. Order matters: dotted-section first.
_IRS_NUMBER_PATTERN = (
    r"\.?\s*(?:§\s*|No\.?\s+|Section\s+|sec\.?\s+)?"
    r"(?P<num>"
    r"\d+(?:\.\d+){1,5}"
    r"|\d{4}-\d{1,4}(?:-\d{1,5})?"
    r"|\d{1,3}(?:,\d{3})+"
    r"|\d{4,12}"
    r")"
)

# IRM section-only fallback (no hyphen-year, just dotted numerics).
_IRM_SECTION_PATTERN = r"\s*(?:§|Section\s+|sec\.?\s+)?\s*(?P<num>\d+(?:\.\d+){0,5})"

# Year-prefix detector for IRS numbers like ``2019-11``.
_IRS_YEAR_PATTERN = r"\A(?P<y>\d{4})[-,]"


@lru_cache(maxsize=1)
def _irs_number_matcher():  # type: ignore[no-untyped-def]
    return regex(_IRS_NUMBER_PATTERN)


@lru_cache(maxsize=1)
def _irm_section_matcher():  # type: ignore[no-untyped-def]
    return regex(_IRM_SECTION_PATTERN)


@lru_cache(maxsize=1)
def _irs_year_matcher():  # type: ignore[no-untyped-def]
    return regex(_IRS_YEAR_PATTERN)


def _parse_irs_year(num: str) -> int | None:
    if not num:
        return None
    hit = _irs_year_matcher().find_first(num)
    if hit is None:
        return None
    year_str = hit.groups[1] if len(hit.groups) > 1 else None
    if not year_str:
        return None
    try:
        year = int(year_str)
    except ValueError:
        return None
    if 1900 <= year <= 2200:
        return year
    return None


def _match_at(matcher: RegexMatcher, text: str, pos: int) -> RegexMatchSpan | None:
    """Anchored match: run ``matcher`` against ``text[pos:]`` and require
    the hit to start at offset 0. Returns ``None`` otherwise."""
    sub = text[pos:]
    if not sub:
        return None
    hit = matcher.find_first(sub)
    if hit is None or hit.start != 0:
        return None
    return hit


def extract_irs_guidance_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[IRSGuidanceCitation]:
    if not text:
        return []
    out: list[IRSGuidanceCitation] = []
    seen: set[tuple[int, int]] = set()
    num_matcher = _irs_number_matcher()
    irm_section_matcher = _irm_section_matcher()

    for kind, normalized_prefix, prefix_matcher in _irs_prefix_matchers():
        for prefix_match in prefix_matcher.find_all(text):
            num_hit = _match_at(num_matcher, text, prefix_match.end)
            if num_hit is None:
                if kind == "irm":
                    sect_hit = _match_at(irm_section_matcher, text, prefix_match.end)
                    if sect_hit is None:
                        continue
                    abs_start = prefix_match.start
                    abs_end = prefix_match.end + sect_hit.end
                    span = (abs_start, abs_end)
                    if span in seen:
                        continue
                    seen.add(span)
                    num = sect_hit.groups[1] if len(sect_hit.groups) > 1 else ""
                    if not num:
                        continue
                    out.append(
                        IRSGuidanceCitation(
                            raw=text[abs_start:abs_end],
                            normalized=f"{normalized_prefix} § {num}",
                            span=span,
                            source_uri=source_uri,
                            guidance_kind=kind,
                            number=num,
                        )
                    )
                continue
            num = num_hit.groups[1] if len(num_hit.groups) > 1 else ""
            if not num:
                continue
            abs_start = prefix_match.start
            abs_end = prefix_match.end + num_hit.end
            span = (abs_start, abs_end)
            if span in seen:
                continue
            seen.add(span)
            year = _parse_irs_year(num)
            normalized = (
                f"{normalized_prefix} § {num}" if kind == "irm" else f"{normalized_prefix} {num}"
            )
            out.append(
                IRSGuidanceCitation(
                    raw=text[abs_start:abs_end],
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    guidance_kind=kind,
                    year=year,
                    number=num,
                )
            )

    out.sort(key=lambda c: c.span[0])
    return _dedupe_overlapping_irs(out)


def _dedupe_overlapping_irs(
    cites: list[IRSGuidanceCitation],
) -> list[IRSGuidanceCitation]:
    out: list[IRSGuidanceCitation] = []
    for c in cites:
        if any(p.span[0] <= c.span[0] and c.span[1] <= p.span[1] for p in out if p is not c):
            continue
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# Executive Orders / Proclamations / Memos / Determinations
# ---------------------------------------------------------------------------

# Order numbers: ``14,028`` (comma-thousands) OR ``13769`` (4-6 digits)
# OR ``137`` (1-3 digits, fallback for short legacy numbers).
_EO_PROC_NUMBER = r"\d{1,3},\d{3}|\d{4,6}|\d{1,3}"

_EXEC_ORDER_PATTERN = (
    r"(?i)"
    r"\b(?:Exec(?:utive)?\.?\s*Order|E\.?O\.?)"
    r"\s*(?:No\.?|Number|\#)?\s*"
    r"(?P<num>" + _EO_PROC_NUMBER + r")"
)

_PROCLAMATION_PATTERN = (
    r"(?i)"
    r"\bProc(?:lamation)?\.?"
    r"\s*(?:No\.?|Number|\#)?\s*"
    r"(?P<num>" + _EO_PROC_NUMBER + r")"
)

# Memorandum: capture title up to a terminator. Rust regex has no
# lookahead, so we capture the terminator and trim from the matched
# span. The title group is non-greedy and capped at 80 chars.
_MEMORANDUM_PATTERN = (
    r"\b(?:Presidential\s+)?Memorandum"
    r"(?:\s+(?:on|of|for|to)\s+(?P<title>[A-Z][^.,;\n]{2,80}))?"
    r"(?P<terminator>[.,;\n])?"
)

_DETERMINATION_PATTERN = r"(?i)\bPresidential\s+Determination\s+No\.?\s*(?P<num>\d{2,4}-\d{1,4})\b"


@lru_cache(maxsize=1)
def _exec_order_matcher():  # type: ignore[no-untyped-def]
    return regex(_EXEC_ORDER_PATTERN)


@lru_cache(maxsize=1)
def _proclamation_matcher():  # type: ignore[no-untyped-def]
    return regex(_PROCLAMATION_PATTERN)


@lru_cache(maxsize=1)
def _memorandum_matcher():  # type: ignore[no-untyped-def]
    return regex(_MEMORANDUM_PATTERN)


@lru_cache(maxsize=1)
def _determination_matcher():  # type: ignore[no-untyped-def]
    return regex(_DETERMINATION_PATTERN)


def extract_executive_action_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[ExecutiveActionCitation]:
    if not text:
        return []
    out: list[ExecutiveActionCitation] = []

    for match in _exec_order_matcher().find_all(text):
        num = match.groups[1] if len(match.groups) > 1 else ""
        if not num:
            continue
        out.append(
            ExecutiveActionCitation(
                raw=match.text,
                normalized=f"Exec. Order No. {num}",
                span=(match.start, match.end),
                source_uri=source_uri,
                action_kind="executive_order",
                number=num,
            )
        )

    for match in _proclamation_matcher().find_all(text):
        num = match.groups[1] if len(match.groups) > 1 else ""
        if not num:
            continue
        out.append(
            ExecutiveActionCitation(
                raw=match.text,
                normalized=f"Proclamation No. {num}",
                span=(match.start, match.end),
                source_uri=source_uri,
                action_kind="proclamation",
                number=num,
            )
        )

    for match in _memorandum_matcher().find_all(text):
        # groups: [whole, title, terminator]
        title = match.groups[1] if len(match.groups) > 1 else None
        terminator = match.groups[2] if len(match.groups) > 2 else None
        # Adjust end to drop the captured terminator from the span.
        end = match.end
        if terminator and match.text.endswith(terminator):
            end = match.end - len(terminator)
        title_clean = title.strip() if title else None
        out.append(
            ExecutiveActionCitation(
                raw=text[match.start : end],
                normalized=(
                    f"Presidential Memorandum on {title_clean}"
                    if title_clean
                    else "Presidential Memorandum"
                ),
                span=(match.start, end),
                source_uri=source_uri,
                action_kind="memorandum",
                title=title_clean,
            )
        )

    for match in _determination_matcher().find_all(text):
        num = match.groups[1] if len(match.groups) > 1 else ""
        if not num:
            continue
        out.append(
            ExecutiveActionCitation(
                raw=match.text,
                normalized=f"Presidential Determination No. {num}",
                span=(match.start, match.end),
                source_uri=source_uri,
                action_kind="determination",
                number=num,
            )
        )

    out.sort(key=lambda c: c.span[0])
    return _dedupe_overlapping_exec(out)


def _dedupe_overlapping_exec(
    cites: list[ExecutiveActionCitation],
) -> list[ExecutiveActionCitation]:
    out: list[ExecutiveActionCitation] = []
    for c in cites:
        if any(p.span[0] <= c.span[0] and c.span[1] <= p.span[1] and p is not c for p in out):
            continue
        out.append(c)
    return out


__all__ = [
    "ExecutiveActionKind",
    "IRSGuidanceKind",
    "TreasuryRegulationStatus",
    "extract_executive_action_citations",
    "extract_irs_guidance_citations",
    "extract_treasury_regulation_citations",
    "iter_treasury_regulation_matches",
]
