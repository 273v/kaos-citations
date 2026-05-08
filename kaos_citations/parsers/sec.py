"""SEC + FINRA + exchange + banking + CFTC + NAIC + intl finance parser.

kaos-nlp-core RegexMatcher only — no `re`. Covers Phase 3 financial
families enumerated in ``docs/CITATION_TAXONOMY.md``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, cast

from kaos_citations.matchers import RegexMatcher, regex
from kaos_citations.model import (
    BaselFrameworkCitation,
    CFPBDocKind,
    CFPBDocumentCitation,
    CFTCDocKind,
    CFTCDocumentCitation,
    ExchangeRuleCitation,
    FDICDocumentCitation,
    FedReserveLetterCitation,
    FedReserveLetterKind,
    FedReserveRegulationCitation,
    FFIECCallReportCitation,
    FINRADisciplinaryCitation,
    FINRARegulatoryNoticeCitation,
    FINRARuleCitation,
    InternationalFinancialCitation,
    NAICCitation,
    NCUALetterCitation,
    OCCDocumentCitation,
    SECAct,
    SECFilingCitation,
    SECFilingForm,
    SECRegulationCitation,
    SECRegulationKind,
    SECReleaseCitation,
    SECStaffGuidanceCitation,
    SecuritiesExchange,
)


def _parse_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return None


_SUBDIV_PATTERN = r"\(([^)]+)\)"


@lru_cache(maxsize=1)
def _subdiv_matcher():  # type: ignore[no-untyped-def]
    return regex(_SUBDIV_PATTERN)


def _split_subdivisions(subs: str) -> tuple[str, ...]:
    if not subs:
        return ()
    parts: list[str] = []
    for m in _subdiv_matcher().find_all(subs):
        inner = m.groups[1] if len(m.groups) > 1 else ""
        if inner.strip():
            parts.append(inner.strip())
    return tuple(parts)


# ---------------------------------------------------------------------------
# SEC Filings
# ---------------------------------------------------------------------------

# SEC form alternation — order matters; longer (e.g. ``10-K/A``) first.
_SEC_FORMS: tuple[SECFilingForm, ...] = (
    "10-K/A",
    "10-Q/A",
    "8-K/A",
    "10-K",
    "10-Q",
    "8-K",
    "S-1",
    "S-3",
    "S-4",
    "S-8",
    "S-11",
    "F-1",
    "F-3",
    "F-4",
    "20-F",
    "40-F",
    "13D",
    "13G",
    "13F-HR",
    "13F-NT",
    "14A",
    "14C",
    "ADV",
    "144",
    "N-1A",
    "N-CSR",
    "N-PORT",
    "N-Q",
    "N-2",
    "D",
    "3",
    "4",
    "5",
)


def _escape_pattern(s: str) -> str:
    """Escape regex metacharacters for a literal string. Rust regex
    needs the same escaping conventions as Python's ``re`` for the
    common metas; this hand-rolled version covers the chars present
    in our SEC form names."""
    out: list[str] = []
    for ch in s:
        if ch in r".+*?^$()[]{}|\\":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


_SEC_FORM_ALT = "|".join(_escape_pattern(f) for f in _SEC_FORMS)

_SEC_FILING_PATTERN = (
    r"(?i)"
    r"\b(?:Form|Schedule)\s+"
    r"(?P<form>" + _SEC_FORM_ALT + r")"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)


@lru_cache(maxsize=1)
def _sec_filing_matcher():  # type: ignore[no-untyped-def]
    return regex(_SEC_FILING_PATTERN)


def extract_sec_filing_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[SECFilingCitation]:
    if not text:
        return []
    out: list[SECFilingCitation] = []
    for m in _sec_filing_matcher().find_all(text):
        # groups: [whole, form, date]
        form_raw = m.groups[1] if len(m.groups) > 1 else ""
        if not form_raw:
            continue
        form: SECFilingForm = cast("SECFilingForm", form_raw.upper())
        date = m.groups[2] if len(m.groups) > 2 else None
        normalized = f"Form {form}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            SECFilingCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                form=form,
                filing_date=date,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# SEC Releases (33-/34-/IC-/IA-/TIA-)
# ---------------------------------------------------------------------------

_SEC_RELEASE_PATTERN = (
    r"(?i)"
    r"\b(?:"
    r"(?:(?:Securities|Sec\.?)\s+Act|Securities\s+Exchange|Exchange|Exch\.?)\s+Act"
    r"|Investment\s+(?:Company|Adviser?s?)\s+Act"
    r"|Trust\s+Indenture\s+Act"
    r"|(?:SEC\s+)?Release"
    r")"
    r"\s+(?:Release\s+)?No\.?\s*"
    r"(?P<act>33|34|IC|IA|TIA)"
    r"-(?P<num>\d{1,6}[A-Z]?)"
)

_ACT_NORMALIZED: dict[str, str] = {
    "33": "Securities Act Release",
    "34": "Exchange Act Release",
    "IC": "Investment Company Act Release",
    "IA": "Investment Advisers Act Release",
    "TIA": "Trust Indenture Act Release",
}


@lru_cache(maxsize=1)
def _sec_release_matcher():  # type: ignore[no-untyped-def]
    return regex(_SEC_RELEASE_PATTERN)


def extract_sec_release_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[SECReleaseCitation]:
    if not text:
        return []
    out: list[SECReleaseCitation] = []
    for m in _sec_release_matcher().find_all(text):
        # groups: [whole, act, num]
        act_str = (m.groups[1] or "").upper() if len(m.groups) > 1 else ""
        num = m.groups[2] if len(m.groups) > 2 else ""
        if not act_str or not num:
            continue
        act: SECAct = cast("SECAct", act_str)
        release_number = f"{act_str}-{num}"
        prefix = _ACT_NORMALIZED.get(act_str, "Release")
        out.append(
            SECReleaseCitation(
                raw=m.text,
                normalized=f"{prefix} No. {release_number}",
                span=(m.start, m.end),
                source_uri=source_uri,
                act=act,
                release_number=release_number,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# SEC Staff Guidance: SAB / SLB / C&DI / no-action
# ---------------------------------------------------------------------------

_SAB_PATTERN = (
    r"(?i)\b(?:SEC\s+)?(?:Staff\s+Accounting\s+Bulletin|SAB)\s*(?:No\.?\s*)?"
    r"(?P<num>\d{1,4}[A-Z]?)"
)
_SLB_PATTERN = (
    r"(?i)\b(?:SEC\s+)?(?:Staff\s+Legal\s+Bulletin|SLB)\s*(?:No\.?\s*)?"
    r"(?P<num>\d{1,4}[A-Z]?)"
)
_CDI_PATTERN = r"(?i)\bC\s*&\s*DI\s+(?:Question\s+)?(?P<num>\d{2,4}\.\d{1,4})"

# No-action letter — Rust regex has no lookahead. We capture the
# trailing context terminator but trim it from the matched span.
_NO_ACTION_PATTERN = (
    r"(?i)"
    r"\bSEC\s+No-Action\s+Letter"
    r"(?:\s*,?\s*(?:to|from)\s+(?P<requestor>[A-Z][^,()\n]{1,80}?))?"
    r"(?P<terminator>(?:\s*[,(\n]|\s+\d{4}|$))"
)


@lru_cache(maxsize=1)
def _sab_matcher():  # type: ignore[no-untyped-def]
    return regex(_SAB_PATTERN)


@lru_cache(maxsize=1)
def _slb_matcher():  # type: ignore[no-untyped-def]
    return regex(_SLB_PATTERN)


@lru_cache(maxsize=1)
def _cdi_matcher():  # type: ignore[no-untyped-def]
    return regex(_CDI_PATTERN)


@lru_cache(maxsize=1)
def _no_action_matcher():  # type: ignore[no-untyped-def]
    return regex(_NO_ACTION_PATTERN)


def extract_sec_staff_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[SECStaffGuidanceCitation]:
    if not text:
        return []
    out: list[SECStaffGuidanceCitation] = []
    seen: set[tuple[int, int]] = set()

    for m in _sab_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            SECStaffGuidanceCitation(
                raw=m.text,
                normalized=f"Staff Accounting Bulletin No. {num}",
                span=span,
                source_uri=source_uri,
                doc_kind="sab",
                number=num,
            )
        )
    for m in _slb_matcher().find_all(text):
        span = (m.start, m.end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            SECStaffGuidanceCitation(
                raw=m.text,
                normalized=f"Staff Legal Bulletin No. {num}",
                span=span,
                source_uri=source_uri,
                doc_kind="slb",
                number=num,
            )
        )
    for m in _cdi_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            SECStaffGuidanceCitation(
                raw=m.text,
                normalized=f"C&DI Question {num}",
                span=span,
                source_uri=source_uri,
                doc_kind="cdi",
                question=num,
            )
        )
    for m in _no_action_matcher().find_all(text):
        # groups: [whole, requestor, terminator]
        requestor = m.groups[1] if len(m.groups) > 1 else None
        terminator = m.groups[2] if len(m.groups) > 2 else ""
        end = m.end - len(terminator) if terminator else m.end
        span = (m.start, end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        normalized = "SEC No-Action Letter"
        if requestor:
            normalized = f"SEC No-Action Letter to {requestor.strip()}"
        out.append(
            SECStaffGuidanceCitation(
                raw=text[span[0] : span[1]],
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind="no_action",
                requestor=requestor.strip() if requestor else None,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# SEC Regulations by name
# ---------------------------------------------------------------------------

_SEC_REG_PATTERN = (
    r"(?i)"
    r"\b(?:Reg(?:ulation)?\.?)\s+"
    r"(?P<reg>S-X|S-K|S-T|AB|FD|BTR|G|M)"
    r"(?:\s*(?:§|Section\s+)?\s*(?P<sect>\d+(?:\.\d+)*(?:-\d+)?))?"
    r"(?:\s*,?\s*Item\s+(?P<item>\d+(?:\(\w+\))?))?"
)


@lru_cache(maxsize=1)
def _sec_reg_matcher():  # type: ignore[no-untyped-def]
    return regex(_SEC_REG_PATTERN)


def extract_sec_regulation_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[SECRegulationCitation]:
    if not text:
        return []
    out: list[SECRegulationCitation] = []
    for m in _sec_reg_matcher().find_all(text):
        # groups: [whole, reg, sect, item]
        reg_raw = (m.groups[1] or "").upper() if len(m.groups) > 1 else ""
        if not reg_raw:
            continue
        reg: SECRegulationKind = cast("SECRegulationKind", reg_raw)
        sect = m.groups[2] if len(m.groups) > 2 else None
        item = m.groups[3] if len(m.groups) > 3 else None
        normalized = f"Reg. {reg_raw}"
        if sect:
            normalized = f"{normalized} § {sect}"
        if item:
            normalized = f"{normalized}, Item {item}"
        out.append(
            SECRegulationCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                regulation=reg,
                cfr_section=sect,
                item=item,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# FINRA + Exchange Rules
# ---------------------------------------------------------------------------

_FINRA_RULE_PATTERN = (
    r"(?i)"
    r"\bFINRA\s+Rule\s+(?P<num>\d{3,5})"
    r"(?P<subs>(?:\([^)]{1,12}\)){0,4})"
)

_FINRA_NOTICE_PATTERN = (
    r"(?i)"
    r"\bFINRA\s+(?:Regulatory\s+)?Notice\s+(?P<num>\d{2}-\d{1,4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{4}|\d{1,2}\s+[A-Za-z\.]+\s+\d{4}|\d{4}-\d{2}-\d{2})\s*\))?"
)

_FINRA_DISCIPLINARY_PATTERN = (
    r"(?i)"
    r"\bFINRA\s+Disciplinary\s+Proceeding\s+No\.?\s+(?P<num>\d{6,15})"
    r"(?:\s*\(\s*(?P<auth>OHO|NAC)\b"
    r"(?:\s+(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4}))?"
    r"\s*\))?"
)


@lru_cache(maxsize=1)
def _finra_rule_matcher():  # type: ignore[no-untyped-def]
    return regex(_FINRA_RULE_PATTERN)


@lru_cache(maxsize=1)
def _finra_notice_matcher():  # type: ignore[no-untyped-def]
    return regex(_FINRA_NOTICE_PATTERN)


@lru_cache(maxsize=1)
def _finra_disciplinary_matcher():  # type: ignore[no-untyped-def]
    return regex(_FINRA_DISCIPLINARY_PATTERN)


def extract_finra_rule_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FINRARuleCitation]:
    if not text:
        return []
    out: list[FINRARuleCitation] = []
    for m in _finra_rule_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        subs_raw = m.groups[2] if len(m.groups) > 2 else ""
        subs = _split_subdivisions(subs_raw)
        normalized = f"FINRA Rule {num}{''.join(f'({s})' for s in subs)}"
        out.append(
            FINRARuleCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                rule_number=num,
                subdivisions=subs,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


def extract_finra_notice_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FINRARegulatoryNoticeCitation]:
    if not text:
        return []
    out: list[FINRARegulatoryNoticeCitation] = []
    for m in _finra_notice_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        date = m.groups[2] if len(m.groups) > 2 else None
        normalized = f"FINRA Regulatory Notice {num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            FINRARegulatoryNoticeCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                notice_number=num,
                exact_date=date,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


def extract_finra_disciplinary_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FINRADisciplinaryCitation]:
    if not text:
        return []
    out: list[FINRADisciplinaryCitation] = []
    for m in _finra_disciplinary_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        auth_raw = m.groups[2] if len(m.groups) > 2 else None
        date = m.groups[3] if len(m.groups) > 3 else None
        auth: Literal["OHO", "NAC", "OTHER"] | None = (
            cast(Literal["OHO", "NAC", "OTHER"], auth_raw.upper()) if auth_raw else None
        )
        normalized = f"FINRA Disciplinary Proceeding No. {num}"
        if auth_raw or date:
            tail = " ".join(filter(None, [auth_raw, date])).strip()
            normalized = f"{normalized} ({tail})"
        out.append(
            FINRADisciplinaryCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                proceeding_number=num,
                decision_authority=auth,
                exact_date=date,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# Exchange/SRO rules: NYSE / Nasdaq / Cboe / MSRB / OCC.
_EXCHANGE_PATTERN_DEFS: tuple[tuple[str, SecuritiesExchange], ...] = (
    (r"(?i)\bMSRB\s+Rule\s+(?P<num>[A-Z]?-?\d+(?:\.\d+)?)", "MSRB"),
    (r"(?i)\bNYSE\s+Rule\s+(?P<num>\d{1,5}(?:\.\d+)?)", "NYSE"),
    (r"(?i)\bNasdaq\s+Rule\s+(?P<num>\d{1,5}(?:\.\d+)?)", "Nasdaq"),
    (r"(?i)\bCboe\s+Rule\s+(?P<num>\d{1,5}(?:\.\d+)?)", "Cboe"),
    (r"(?i)\bOCC\s+Rule\s+(?P<num>\d{1,5}(?:\.\d+)?)", "OCC"),
)


@lru_cache(maxsize=1)
def _exchange_matchers() -> tuple[tuple[SecuritiesExchange, RegexMatcher], ...]:
    return tuple((exch, regex(pat)) for pat, exch in _EXCHANGE_PATTERN_DEFS)


_EXCHANGE_SUBDIV_PATTERN = r"(?P<subs>(?:\([^)]{1,12}\)){0,4})"


@lru_cache(maxsize=1)
def _exchange_subdiv_matcher():  # type: ignore[no-untyped-def]
    return regex(_EXCHANGE_SUBDIV_PATTERN)


def extract_exchange_rule_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[ExchangeRuleCitation]:
    if not text:
        return []
    out: list[ExchangeRuleCitation] = []
    seen: set[tuple[int, int]] = set()
    sub_matcher = _exchange_subdiv_matcher()
    for exchange, matcher in _exchange_matchers():
        for m in matcher.find_all(text):
            num = m.groups[1] or ""
            if not num:
                continue
            # Anchor the subdiv matcher at m.end against the document.
            tail = text[m.end :]
            sub_hit = sub_matcher.find_first(tail)
            subs_raw = ""
            extra_len = 0
            if sub_hit is not None and sub_hit.start == 0:
                subs_raw = sub_hit.groups[1] if len(sub_hit.groups) > 1 else ""
                extra_len = sub_hit.end
            subs = _split_subdivisions(subs_raw)
            end = m.end + extra_len
            span = (m.start, end)
            if span in seen:
                continue
            seen.add(span)
            normalized = (
                f"{exchange} Rule {num}{''.join(f'({s})' for s in subs)}"
                if exchange != "MSRB"
                else f"MSRB Rule {num}"
            )
            out.append(
                ExchangeRuleCitation(
                    raw=text[span[0] : span[1]],
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    exchange=exchange,
                    rule_number=num,
                    subdivisions=subs,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Federal Reserve regs + letters
# ---------------------------------------------------------------------------

_FED_RESERVE_REG_PATTERN = (
    r"(?i)"
    r"\b(?:Reg(?:ulation)?\.?)\s+"
    r"(?P<letter>[A-Z]{1,2})"
    r"\b"
    r"(?:\s*,?\s*(?P<cfr_title>\d{1,2})\s*C\.?F\.?R\.?\s*"
    r"(?:pt\.?\s*|part\s+|§\s*)?"
    r"(?P<cfr_part>\d+(?:\.\d+)?))?"
)

# Allowed Fed Reserve regulation letters.
_FED_RESERVE_LETTERS: frozenset[str] = frozenset(
    {
        *(chr(c) for c in range(ord("A"), ord("Z") + 1)),
        "AA",
        "BB",
        "CC",
        "DD",
        "EE",
        "FF",
        "GG",
        "HH",
        "II",
        "JJ",
        "KK",
        "LL",
        "MM",
        "NN",
        "OO",
        "PP",
        "QQ",
        "RR",
        "SS",
        "TT",
        "UU",
        "VV",
        "WW",
        "XX",
        "YY",
        "ZZ",
    }
)

# ``SR 23-04`` / ``CA 23-01`` — case-sensitive (the kinds are uppercase).
_FED_RESERVE_LETTER_PATTERN = (
    r"\b(?P<kind>SR|CA|OP)"
    r"\s+(?P<num>\d{2}-\d{1,4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)


@lru_cache(maxsize=1)
def _fed_reserve_reg_matcher():  # type: ignore[no-untyped-def]
    return regex(_FED_RESERVE_REG_PATTERN)


@lru_cache(maxsize=1)
def _fed_reserve_letter_matcher():  # type: ignore[no-untyped-def]
    return regex(_FED_RESERVE_LETTER_PATTERN)


def extract_fed_reserve_regulation_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FedReserveRegulationCitation]:
    if not text:
        return []
    out: list[FedReserveRegulationCitation] = []
    seen: set[tuple[int, int]] = set()
    for m in _fed_reserve_reg_matcher().find_all(text):
        # groups: [whole, letter, cfr_title, cfr_part]
        letter = (m.groups[1] or "").upper() if len(m.groups) > 1 else ""
        if letter not in _FED_RESERVE_LETTERS:
            continue
        # Skip ``S-K``/``S-X`` (SEC reg, not Fed Reserve) — they have a hyphen.
        if "-" in m.text:
            continue
        cfr_title = _parse_int(m.groups[2] if len(m.groups) > 2 else None)
        cfr_part = m.groups[3] if len(m.groups) > 3 else None
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        normalized = f"Reg. {letter}"
        if cfr_title and cfr_part:
            normalized = f"{normalized}, {cfr_title} C.F.R. pt. {cfr_part}"
        out.append(
            FedReserveRegulationCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                reg_letter=letter,
                cfr_title=cfr_title,
                cfr_part=cfr_part,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


def extract_fed_reserve_letter_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FedReserveLetterCitation]:
    if not text:
        return []
    out: list[FedReserveLetterCitation] = []
    for m in _fed_reserve_letter_matcher().find_all(text):
        kind_str = m.groups[1] if len(m.groups) > 1 else ""
        num = m.groups[2] if len(m.groups) > 2 else ""
        date = m.groups[3] if len(m.groups) > 3 else None
        if not kind_str or not num:
            continue
        kind: FedReserveLetterKind = cast("FedReserveLetterKind", kind_str)
        try:
            year_2 = int(num.split("-")[0])
            year: int | None = 2000 + year_2 if year_2 < 80 else 1900 + year_2
        except ValueError:
            year = None
        normalized = f"{kind_str} {num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            FedReserveLetterCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                letter_kind=kind,
                number=num,
                year=year,
                exact_date=date,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# FDIC / OCC / CFPB / NCUA
# ---------------------------------------------------------------------------

_FDIC_FIL_PATTERN = (
    r"(?i)"
    r"\bFIL-(?P<num>\d{1,4}-\d{4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)
_OCC_BULLETIN_PATTERN = (
    r"(?i)"
    r"\bOCC\s+Bulletin\s+(?P<num>\d{4}-\d{1,4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)
_OCC_INTERP_PATTERN = (
    r"(?i)"
    r"\bOCC\s+Interp(?:retive)?\.?\s+(?:Ltr\.?|Letter)\s+(?P<num>\d{1,4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)
_OCC_CONDITIONAL_PATTERN = (
    r"(?i)"
    r"\bOCC\s+Conditional\s+Approval\s+(?:No\.?\s+)?(?P<num>\d{1,4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)


@lru_cache(maxsize=1)
def _fdic_fil_matcher():  # type: ignore[no-untyped-def]
    return regex(_FDIC_FIL_PATTERN)


@lru_cache(maxsize=1)
def _occ_bulletin_matcher():  # type: ignore[no-untyped-def]
    return regex(_OCC_BULLETIN_PATTERN)


@lru_cache(maxsize=1)
def _occ_interp_matcher():  # type: ignore[no-untyped-def]
    return regex(_OCC_INTERP_PATTERN)


@lru_cache(maxsize=1)
def _occ_conditional_matcher():  # type: ignore[no-untyped-def]
    return regex(_OCC_CONDITIONAL_PATTERN)


def extract_fdic_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FDICDocumentCitation]:
    if not text:
        return []
    out: list[FDICDocumentCitation] = []
    for m in _fdic_fil_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        if not num:
            continue
        year = _parse_int(num.split("-")[1]) if "-" in num else None
        date = m.groups[2] if len(m.groups) > 2 else None
        normalized = f"FIL-{num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            FDICDocumentCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                doc_kind="FIL",
                number=num,
                year=year,
                exact_date=date,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


def extract_occ_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[OCCDocumentCitation]:
    if not text:
        return []
    out: list[OCCDocumentCitation] = []
    seen: set[tuple[int, int]] = set()
    for m in _occ_bulletin_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        year = _parse_int(num.split("-")[0]) if num else None
        date = m.groups[2] if len(m.groups) > 2 else None
        normalized = f"OCC Bulletin {num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            OCCDocumentCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind="BULLETIN",
                number=num,
                year=year,
                exact_date=date,
            )
        )
    for m in _occ_interp_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        date = m.groups[2] if len(m.groups) > 2 else None
        normalized = f"OCC Interp. Ltr. {num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            OCCDocumentCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind="INTERPRETIVE_LETTER",
                number=num,
                exact_date=date,
            )
        )
    for m in _occ_conditional_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        date = m.groups[2] if len(m.groups) > 2 else None
        normalized = f"OCC Conditional Approval No. {num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            OCCDocumentCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind="CONDITIONAL_APPROVAL",
                number=num,
                exact_date=date,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


_CFPB_PATTERN_DEFS: tuple[tuple[str, CFPBDocKind, str], ...] = (
    (
        r"(?i)\bCFPB\s+Compliance\s+Bulletin\s+(?P<num>\d{4}-\d{1,4})",
        "COMPLIANCE_BULLETIN",
        "CFPB Compliance Bulletin",
    ),
    (
        r"(?i)\bCFPB\s+Bulletin\s+(?P<num>\d{4}-\d{1,4})",
        "BULLETIN",
        "CFPB Bulletin",
    ),
    (
        r"(?i)\bCFPB\s+Circular\s+(?P<num>\d{4}-\d{1,4})",
        "CIRCULAR",
        "CFPB Circular",
    ),
    (
        r"(?i)\bCFPB\s+Advisory\s+Opinion\b",
        "ADVISORY_OPINION",
        "CFPB Advisory Opinion",
    ),
)


@lru_cache(maxsize=1)
def _cfpb_matchers() -> tuple[tuple[CFPBDocKind, str, RegexMatcher], ...]:
    return tuple((kind, prefix, regex(pat)) for pat, kind, prefix in _CFPB_PATTERN_DEFS)


def extract_cfpb_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[CFPBDocumentCitation]:
    if not text:
        return []
    out: list[CFPBDocumentCitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, normalized_prefix, matcher in _cfpb_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            num: str | None = m.groups[1] if len(m.groups) > 1 else None
            year = _parse_int(num.split("-")[0]) if num else None
            normalized = f"{normalized_prefix} {num}" if num else normalized_prefix
            out.append(
                CFPBDocumentCitation(
                    raw=m.text,
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    doc_kind=kind,
                    number=num,
                    year=year,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


_NCUA_LETTER_PATTERN = (
    r"(?i)"
    r"\bNCUA\s+(?:Letter\s+to\s+(?:Credit\s+Unions|Federal\s+Credit\s+Unions)\s+)?"
    r"(?P<num>\d{2}-\d{1,4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)


@lru_cache(maxsize=1)
def _ncua_matcher():  # type: ignore[no-untyped-def]
    return regex(_NCUA_LETTER_PATTERN)


def extract_ncua_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[NCUALetterCitation]:
    if not text:
        return []
    out: list[NCUALetterCitation] = []
    for m in _ncua_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        if not num:
            continue
        date = m.groups[2] if len(m.groups) > 2 else None
        try:
            year_2 = int(num.split("-")[0])
            year: int | None = 2000 + year_2 if year_2 < 80 else 1900 + year_2
        except ValueError:
            year = None
        normalized = f"NCUA Letter to Credit Unions {num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            NCUALetterCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                number=num,
                year=year,
                exact_date=date,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Basel framework
# ---------------------------------------------------------------------------

_BASEL_PATTERN = (
    r"\b(?:BCBS\s+)?(?:d|D)(?P<num>\d{2,4})\b"
    r"|\bBasel\s+(?P<level>I{1,3}|IV)"
)


@lru_cache(maxsize=1)
def _basel_matcher():  # type: ignore[no-untyped-def]
    return regex(_BASEL_PATTERN)


def extract_basel_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[BaselFrameworkCitation]:
    if not text:
        return []
    out: list[BaselFrameworkCitation] = []
    for m in _basel_matcher().find_all(text):
        # groups: [whole, num, level]
        num = m.groups[1] if len(m.groups) > 1 else None
        level = m.groups[2] if len(m.groups) > 2 else None
        if num:
            doc_id = f"d{num}"
            normalized = f"BCBS {doc_id}"
        elif level:
            doc_id = f"Basel {level}"
            normalized = f"Basel {level}"
        else:
            continue
        out.append(
            BaselFrameworkCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                document_id=doc_id,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# CFTC
# ---------------------------------------------------------------------------

_CFTC_PATTERN_DEFS: tuple[tuple[str, CFTCDocKind, str], ...] = (
    (
        r"(?i)\bCFTC\s+Interp(?:retive)?\.?\s+(?:Ltr\.?|Letter)\s+(?P<num>\d{2}-\d{1,4})",
        "INTERP_LETTER",
        "CFTC Interpretive Letter",
    ),
    (
        r"(?i)\bCFTC\s+No-Action\s+Letter\s+(?P<num>\d{2}-\d{1,4})",
        "NO_ACTION",
        "CFTC No-Action Letter",
    ),
    (
        r"(?i)\bCFTC\s+Advisory\s+(?P<num>\d{2}-\d{1,4})",
        "ADVISORY",
        "CFTC Advisory",
    ),
    (
        r"(?i)\bCFTC\s+Docket\s+No\.?\s+(?P<num>\d{2}-\d{1,4})",
        "ORDER",
        "CFTC Docket No.",
    ),
)


@lru_cache(maxsize=1)
def _cftc_matchers() -> tuple[tuple[CFTCDocKind, str, RegexMatcher], ...]:
    return tuple((kind, prefix, regex(pat)) for pat, kind, prefix in _CFTC_PATTERN_DEFS)


def extract_cftc_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[CFTCDocumentCitation]:
    if not text:
        return []
    out: list[CFTCDocumentCitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, normalized_prefix, matcher in _cftc_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if span in seen:
                continue
            seen.add(span)
            num = m.groups[1] if len(m.groups) > 1 else ""
            if not num:
                continue
            try:
                year_2 = int(num.split("-")[0])
                year: int | None = 2000 + year_2 if year_2 < 80 else 1900 + year_2
            except ValueError:
                year = None
            normalized = f"{normalized_prefix} {num}"
            out.append(
                CFTCDocumentCitation(
                    raw=m.text,
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    doc_kind=kind,
                    number=num,
                    year=year,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# NAIC
# ---------------------------------------------------------------------------

_NAIC_BULLETIN_PATTERN = (
    r"(?i)"
    r"\bNAIC\s+Bulletin\s+(?P<num>\d{4}-\d{1,4})"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{1,2},?\s+\d{4})\s*\))?"
)
_NAIC_MODEL_PATTERN = (
    r"(?i)"
    r"\bNAIC\s+(?P<title>[^.\n]{4,80}?)\s+Model\s+Act"
    r"(?:\s*\(\s*(?P<year>\d{4})\s*\))?"
)


@lru_cache(maxsize=1)
def _naic_bulletin_matcher():  # type: ignore[no-untyped-def]
    return regex(_NAIC_BULLETIN_PATTERN)


@lru_cache(maxsize=1)
def _naic_model_matcher():  # type: ignore[no-untyped-def]
    return regex(_NAIC_MODEL_PATTERN)


def extract_naic_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[NAICCitation]:
    if not text:
        return []
    out: list[NAICCitation] = []
    seen: set[tuple[int, int]] = set()
    for m in _naic_bulletin_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        date = m.groups[2] if len(m.groups) > 2 else None
        year = _parse_int(num.split("-")[0]) if num else None
        normalized = f"NAIC Bulletin {num}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            NAICCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind="BULLETIN",
                number=num,
                year=year,
                exact_date=date,
            )
        )
    for m in _naic_model_matcher().find_all(text):
        span = (m.start, m.end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        title = (m.groups[1] or "").strip() if len(m.groups) > 1 else ""
        year = _parse_int(m.groups[2] if len(m.groups) > 2 else None)
        normalized = f"NAIC {title} Model Act"
        if year:
            normalized = f"{normalized} ({year})"
        out.append(
            NAICCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind="MODEL_ACT",
                title=title,
                year=year,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# International financial bodies
# ---------------------------------------------------------------------------

_FATF_PATTERN = (
    r"(?i)"
    r"\bFATF\s+Recommendation\s+(?P<num>\d{1,3}[A-Z]?)"
    r"(?:\s*\(\s*(?P<year>\d{4})\s*\))?"
)
_IOSCO_PATTERN = (
    r"(?i)"
    r"\bIOSCO\s+(?:Final\s+Report|Report|Standard)\s*,?\s*"
    r"(?P<id>FR\s*\d{1,3}[-/]\d{4}|\d{4}/\d{1,3})?"
)


@lru_cache(maxsize=1)
def _fatf_matcher():  # type: ignore[no-untyped-def]
    return regex(_FATF_PATTERN)


@lru_cache(maxsize=1)
def _iosco_matcher():  # type: ignore[no-untyped-def]
    return regex(_IOSCO_PATTERN)


def extract_international_finance_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[InternationalFinancialCitation]:
    if not text:
        return []
    out: list[InternationalFinancialCitation] = []

    for m in _fatf_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        if not num:
            continue
        year = _parse_int(m.groups[2] if len(m.groups) > 2 else None)
        normalized = f"FATF Recommendation {num}"
        if year:
            normalized = f"{normalized} ({year})"
        out.append(
            InternationalFinancialCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                body="FATF",
                recommendation_number=num,
                year=year,
            )
        )

    for m in _iosco_matcher().find_all(text):
        doc_id = m.groups[1] if len(m.groups) > 1 else None
        normalized = f"IOSCO Final Report {doc_id}" if doc_id else "IOSCO Final Report"
        out.append(
            InternationalFinancialCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                body="IOSCO",
                document_id=doc_id,
            )
        )

    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# FFIEC Call Reports
# ---------------------------------------------------------------------------

_FFIEC_PATTERN = (
    r"(?i)"
    r"\bFFIEC\s+(?P<num>031|041|051)"
    r"(?:\s*,?\s*Schedule\s+(?P<sched>[A-Z]{1,3}-?[A-Z]?))?"
    r"(?:\s*,?\s*item\s+(?P<item>[\dA-Za-z\.\(\)]+))?"
)


@lru_cache(maxsize=1)
def _ffiec_matcher():  # type: ignore[no-untyped-def]
    return regex(_FFIEC_PATTERN)


def extract_ffiec_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FFIECCallReportCitation]:
    if not text:
        return []
    out: list[FFIECCallReportCitation] = []
    for m in _ffiec_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        if not num:
            continue
        sched = m.groups[2] if len(m.groups) > 2 else None
        item = m.groups[3] if len(m.groups) > 3 else None
        normalized = f"FFIEC {num}"
        if sched:
            normalized = f"{normalized}, Schedule {sched}"
        if item:
            normalized = f"{normalized}, item {item}"
        out.append(
            FFIECCallReportCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                form_number=num,
                schedule=sched,
                item=item,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


__all__ = [
    "extract_basel_citations",
    "extract_cfpb_citations",
    "extract_cftc_citations",
    "extract_exchange_rule_citations",
    "extract_fdic_citations",
    "extract_fed_reserve_letter_citations",
    "extract_fed_reserve_regulation_citations",
    "extract_ffiec_citations",
    "extract_finra_disciplinary_citations",
    "extract_finra_notice_citations",
    "extract_finra_rule_citations",
    "extract_international_finance_citations",
    "extract_naic_citations",
    "extract_ncua_citations",
    "extract_occ_citations",
    "extract_sec_filing_citations",
    "extract_sec_regulation_citations",
    "extract_sec_release_citations",
    "extract_sec_staff_citations",
]
