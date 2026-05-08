"""Accounting + auditing + sustainability parser — kaos-nlp-core, no `re`.

Covers Phase 4 of the citation taxonomy: FASB ASC + ASU + legacy FASB,
PCAOB, AICPA, IFRS, IAASB, IESBA, GASB, FASAB, government audit, NAIC
SAP, sustainability frameworks.
"""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from kaos_citations.matchers import RegexMatcher, regex
from kaos_citations.model import (
    AICPACitation,
    AICPADocKind,
    ASCCitation,
    ASUCitation,
    FASABCitation,
    FASABDocKind,
    GASBCitation,
    GASBDocKind,
    GovernmentAuditCitation,
    IAASBCitation,
    IAASBStandardKind,
    IESBACodeCitation,
    IFRSCitation,
    IFRSStandardKind,
    LegacyFASBCitation,
    LegacyFASBStatementKind,
    NAICAccountingCitation,
    PCAOBCitation,
    PCAOBDocKind,
    SustainabilityCitation,
)


def _parse_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# FASB ASC
# ---------------------------------------------------------------------------

_ASC_PATTERN = (
    r"(?i)"
    r"\b(?:FASB\s+)?ASC\s+"
    r"(?P<topic>\d{3})"
    r"(?:-(?P<subtopic>\d{1,3})"
    r"(?:-(?P<section>\d{1,3})"
    r"(?:-(?P<paragraph>\d{1,3}[A-Z]?))?"
    r")?"
    r")?"
)


@lru_cache(maxsize=1)
def _asc_matcher():  # type: ignore[no-untyped-def]
    return regex(_ASC_PATTERN)


def extract_asc_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[ASCCitation]:
    if not text:
        return []
    out: list[ASCCitation] = []
    for m in _asc_matcher().find_all(text):
        # groups: [whole, topic, subtopic, section, paragraph]
        topic = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        if topic is None:
            continue
        subtopic = _parse_int(m.groups[2] if len(m.groups) > 2 else None)
        section = _parse_int(m.groups[3] if len(m.groups) > 3 else None)
        paragraph = m.groups[4] if len(m.groups) > 4 else None
        parts: list[str] = [str(topic)]
        if subtopic is not None:
            parts.append(str(subtopic))
        if section is not None:
            parts.append(str(section))
        if paragraph:
            parts.append(paragraph)
        normalized = f"FASB ASC {'-'.join(parts)}"
        out.append(
            ASCCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                topic=topic,
                subtopic=subtopic,
                section=section,
                paragraph=paragraph,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Accounting Standards Updates (ASU YYYY-NN)
# ---------------------------------------------------------------------------

# Capture the terminator instead of using lookahead.
_ASU_PATTERN = (
    r"(?i)"
    r"\bASU\s+(?P<year>\d{4})-(?P<seq>\d{1,3})"
    r"(?:\s*,?\s*(?P<title>[A-Z][^.\n]{2,120}?))?"
    r"(?P<terminator>\s*(?:\(|\.|;|\n|$))"
)


@lru_cache(maxsize=1)
def _asu_matcher():  # type: ignore[no-untyped-def]
    return regex(_ASU_PATTERN)


def extract_asu_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[ASUCitation]:
    if not text:
        return []
    out: list[ASUCitation] = []
    for m in _asu_matcher().find_all(text):
        # groups: [whole, year, seq, title, terminator]
        year = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        seq = _parse_int(m.groups[2] if len(m.groups) > 2 else None)
        if year is None or seq is None:
            continue
        if not (2009 <= year <= 2200):
            continue
        title = m.groups[3] if len(m.groups) > 3 else None
        terminator = m.groups[4] if len(m.groups) > 4 else ""
        if title:
            title = title.strip().rstrip(",")
        end = m.end - len(terminator) if terminator else m.end
        normalized = f"ASU {year}-{seq:02d}"
        if title:
            normalized = f"{normalized}, {title}"
        out.append(
            ASUCitation(
                raw=text[m.start : end],
                normalized=normalized,
                span=(m.start, end),
                source_uri=source_uri,
                year=year,
                sequence=seq,
                title=title,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Legacy FASB / APB / ARB
# ---------------------------------------------------------------------------

_LEGACY_FASB_DEFS: tuple[tuple[str, LegacyFASBStatementKind, str], ...] = (
    (r"(?i)\bEITF\s+(?:Issue\s+)?(?P<num>\d{2}-\d{1,3})", "EITF", "EITF Issue"),
    (r"(?i)\bEITF\s+Topic\s+(?P<num>[A-Z]-\d{1,4})", "EITF", "EITF Topic"),
    (r"(?i)\bFSP\s+(?:FAS\s+)?(?P<num>\d{1,4}-\d{1,3})", "FSP", "FSP"),
    (
        r"(?i)\b(?:FASB\s+)?(?:Tech(?:nical)?\.?\s*Bull(?:etin)?\.?|TB)\s+"
        r"(?P<num>\d{2}-\d{1,3})",
        "TB",
        "FASB Technical Bulletin",
    ),
    (r"(?i)\b(?:FASB\s+)?CON\s+(?P<num>\d{1,3})", "CON", "FASB Concepts Statement No."),
    (r"(?i)\bFIN\s+(?P<num>\d{1,3})", "FIN", "FIN"),
    (r"(?i)\bFAS\s+(?P<num>\d{1,3})", "FAS", "FAS"),
    (r"(?i)\bAPB\s+Op(?:inion)?\.?\s+(?P<num>\d{1,3})", "APB", "APB Op."),
    (r"(?i)\bAPB\s+(?P<num>\d{1,3})\b", "APB", "APB"),
    (r"(?i)\bARB\s+(?P<num>\d{1,3})", "ARB", "ARB"),
)


@lru_cache(maxsize=1)
def _legacy_fasb_matchers() -> tuple[tuple[LegacyFASBStatementKind, str, RegexMatcher], ...]:
    return tuple((kind, prefix, regex(pat)) for pat, kind, prefix in _LEGACY_FASB_DEFS)


def extract_legacy_fasb_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[LegacyFASBCitation]:
    if not text:
        return []
    out: list[LegacyFASBCitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, normalized_prefix, matcher in _legacy_fasb_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            num = m.groups[1] if len(m.groups) > 1 else ""
            if not num:
                continue
            normalized = f"{normalized_prefix} {num}"
            out.append(
                LegacyFASBCitation(
                    raw=m.text,
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    statement_kind=kind,
                    number=num,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# PCAOB
# ---------------------------------------------------------------------------

_PCAOB_DEFS: tuple[tuple[str, PCAOBDocKind, str], ...] = (
    (
        r"(?i)\bPCAOB\s+(?:Auditing\s+Standard|AS)\s+(?P<num>\d{4})",
        "AS",
        "PCAOB AS",
    ),
    (
        r"(?i)\bPCAOB\s+Staff\s+Audit\s+Practice\s+Alert\s+(?:No\.?\s+)?(?P<num>\d{1,3})",
        "PRACTICE_ALERT",
        "PCAOB Staff Audit Practice Alert No.",
    ),
    (
        r"(?i)\bPCAOB\s+Release\s+(?:No\.?\s+)?(?P<num>\d{4}-\d{1,4})",
        "RELEASE",
        "PCAOB Release No.",
    ),
    (
        r"(?i)\bPCAOB\s+Rule\s+(?P<num>\d{3,5})",
        "RULE",
        "PCAOB Rule",
    ),
)


@lru_cache(maxsize=1)
def _pcaob_matchers() -> tuple[tuple[PCAOBDocKind, str, RegexMatcher], ...]:
    return tuple((kind, prefix, regex(pat)) for pat, kind, prefix in _PCAOB_DEFS)


def extract_pcaob_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[PCAOBCitation]:
    if not text:
        return []
    out: list[PCAOBCitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, normalized_prefix, matcher in _pcaob_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            num = m.groups[1] if len(m.groups) > 1 else ""
            if not num:
                continue
            normalized = f"{normalized_prefix} {num}"
            out.append(
                PCAOBCitation(
                    raw=m.text,
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    doc_kind=kind,
                    number=num,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# AICPA
# ---------------------------------------------------------------------------

_AICPA_DEFS: tuple[tuple[str, AICPADocKind, str], ...] = (
    (r"(?i)\bAICPA\s+SAS\s+(?:No\.?\s+)?(?P<num>\d{1,4})", "SAS", "AICPA SAS"),
    (r"(?i)\bAICPA\s+SSAE\s+(?:No\.?\s+)?(?P<num>\d{1,3})", "SSAE", "AICPA SSAE"),
    (r"(?i)\bAICPA\s+SSARS\s+(?:No\.?\s+)?(?P<num>\d{1,3})", "SSARS", "AICPA SSARS"),
    (r"(?i)\bAICPA\s+SOP\s+(?P<num>\d{2}-\d{1,3})", "SOP", "AICPA SOP"),
    (r"(?i)\bAICPA\s+TQA\s+(?P<num>\d{4}\.\d{1,3})", "TQA", "AICPA TQA"),
    (
        r"(?i)\bAICPA\s+Code\s+of\s+Pro(?:fessional)?\.?\s+Conduct"
        r"(?:\s*,?\s*ET\s*§\s*(?P<num>\d+(?:\.\d+)*))?",
        "CODE",
        "AICPA Code of Professional Conduct",
    ),
)


@lru_cache(maxsize=1)
def _aicpa_matchers() -> tuple[tuple[AICPADocKind, str, RegexMatcher], ...]:
    return tuple((kind, prefix, regex(pat)) for pat, kind, prefix in _AICPA_DEFS)


def extract_aicpa_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[AICPACitation]:
    if not text:
        return []
    out: list[AICPACitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, normalized_prefix, matcher in _aicpa_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            num: str | None = m.groups[1] if len(m.groups) > 1 else None
            if kind == "CODE":
                normalized = f"{normalized_prefix}, ET § {num}" if num else normalized_prefix
                out.append(
                    AICPACitation(
                        raw=m.text,
                        normalized=normalized,
                        span=span,
                        source_uri=source_uri,
                        doc_kind=kind,
                        section=num,
                    )
                )
            else:
                normalized = f"{normalized_prefix} {num}" if num else normalized_prefix
                out.append(
                    AICPACitation(
                        raw=m.text,
                        normalized=normalized,
                        span=span,
                        source_uri=source_uri,
                        doc_kind=kind,
                        number=num,
                    )
                )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# IFRS / IAS / IFRIC / SIC / Practice Statement / Conceptual Framework
# ---------------------------------------------------------------------------

# Each entry: (pattern, kind). Note the group index of ``num`` /
# ``sym`` / ``para`` varies by pattern — so we capture each group's
# position metadata when registering.
_IFRS_PATTERN_DEFS: tuple[tuple[str, IFRSStandardKind, tuple[str, ...]], ...] = (
    (
        r"(?i)\bIFRS\s+Practice\s+Statement\s+(?P<num>\d{1,2})"
        r"(?:\.(?P<para>\d+[A-Z]?))?",
        "PS",
        ("num", "para"),
    ),
    (
        r"(?i)\bIFRS\s+Conceptual\s+Framework"
        r"(?:\s*(?:¶|para\.?|paragraph)\s*(?P<para>\d+(?:\.\d+)*[A-Z]?))?",
        "CF",
        ("para",),
    ),
    (
        r"(?i)\bIFRIC\s+(?P<num>\d{1,3})(?:\.(?P<para>\d+[A-Z]?))?",
        "IFRIC",
        ("num", "para"),
    ),
    (
        r"(?i)\bSIC[-\s]+(?P<num>\d{1,3})(?:\.(?P<para>\d+[A-Z]?))?",
        "SIC",
        ("num", "para"),
    ),
    (
        r"(?i)\bIFRS\s+(?P<sym>S?\d{1,3})(?:\.(?P<para>\d+[A-Z]?))?",
        "IFRS",
        ("sym", "para"),
    ),
    (
        r"(?i)\bIAS\s+(?P<num>\d{1,3})(?:\.(?P<para>\d+[A-Z]?))?",
        "IAS",
        ("num", "para"),
    ),
)


@lru_cache(maxsize=1)
def _ifrs_matchers() -> tuple[tuple[IFRSStandardKind, tuple[str, ...], RegexMatcher], ...]:
    return tuple((kind, names, regex(pat)) for pat, kind, names in _IFRS_PATTERN_DEFS)


def extract_ifrs_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[IFRSCitation]:
    if not text:
        return []
    out: list[IFRSCitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, names, matcher in _ifrs_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            # Map names → group index (1-indexed since groups[0] is whole).
            idx = {n: i + 1 for i, n in enumerate(names)}
            num: str | None
            if "num" in idx:
                num = m.groups[idx["num"]] if idx["num"] < len(m.groups) else None
            elif "sym" in idx:
                num = m.groups[idx["sym"]] if idx["sym"] < len(m.groups) else None
            else:
                num = None
            paragraph: str | None = (
                m.groups[idx["para"]] if "para" in idx and idx["para"] < len(m.groups) else None
            )
            if not num and kind != "CF":
                continue
            seen.add(span)
            if kind == "CF":
                normalized = "IFRS Conceptual Framework"
                if paragraph:
                    normalized = f"{normalized} ¶ {paragraph}"
            else:
                base = {
                    "IFRS": "IFRS",
                    "IAS": "IAS",
                    "IFRIC": "IFRIC",
                    "SIC": "SIC-",
                    "PS": "IFRS Practice Statement",
                }[kind]
                normalized = f"{base}{num}" if kind == "SIC" else f"{base} {num}"
                if paragraph:
                    normalized = f"{normalized}.{paragraph}"
            out.append(
                IFRSCitation(
                    raw=m.text,
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    standard_kind=kind,
                    number=num or "0",
                    paragraph=paragraph,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# IAASB
# ---------------------------------------------------------------------------

_IAASB_KINDS: tuple[str, ...] = ("ISA", "ISAE", "ISRE", "ISRS", "ISQM", "ISQC")
_IAASB_PATTERN = (
    r"\b(?P<kind>" + "|".join(_IAASB_KINDS) + r")\s+"
    r"(?P<num>\d{1,4})"
    r"(?:\s*\(\s*(?:Revised(?:\s+(?P<rev>\d{4}))?)\s*\))?"
)


@lru_cache(maxsize=1)
def _iaasb_matcher():  # type: ignore[no-untyped-def]
    return regex(_IAASB_PATTERN)


def extract_iaasb_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[IAASBCitation]:
    if not text:
        return []
    out: list[IAASBCitation] = []
    for m in _iaasb_matcher().find_all(text):
        # groups: [whole, kind, num, rev]
        kind_str = m.groups[1] if len(m.groups) > 1 else ""
        num = m.groups[2] if len(m.groups) > 2 else ""
        rev = m.groups[3] if len(m.groups) > 3 else None
        if not kind_str or not num:
            continue
        kind: IAASBStandardKind = cast("IAASBStandardKind", kind_str)
        normalized = f"{kind_str} {num}"
        if rev:
            normalized = f"{normalized} (Revised {rev})"
        out.append(
            IAASBCitation(
                raw=m.text,
                normalized=normalized,
                span=(m.start, m.end),
                source_uri=source_uri,
                standard_kind=kind,
                number=num,
                revision=f"Revised {rev}" if rev else None,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# IESBA Code
# ---------------------------------------------------------------------------

_IESBA_PATTERN = (
    r"(?i)"
    r"\bIESBA\s+Code(?:\s+of\s+Ethics(?:\s+for\s+Pro(?:fessional)?\.?\s+Accountants)?)?"
    r"\s*§\s*(?P<num>\d+(?:\.\d+)*)"
)


@lru_cache(maxsize=1)
def _iesba_matcher():  # type: ignore[no-untyped-def]
    return regex(_IESBA_PATTERN)


def extract_iesba_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[IESBACodeCitation]:
    if not text:
        return []
    out: list[IESBACodeCitation] = []
    for m in _iesba_matcher().find_all(text):
        num = m.groups[1] if len(m.groups) > 1 else ""
        if not num:
            continue
        out.append(
            IESBACodeCitation(
                raw=m.text,
                normalized=f"IESBA Code § {num}",
                span=(m.start, m.end),
                source_uri=source_uri,
                section=num,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# GASB
# ---------------------------------------------------------------------------

# (pattern, kind, prefix, group_names_in_order_after_whole)
_GASB_DEFS: tuple[tuple[str, GASBDocKind, str, tuple[str, ...]], ...] = (
    (
        r"(?i)\bGASB\s+Implementation\s+Guide\s+(?P<num>\d{4}-\d{1,3})",
        "IMPLEMENTATION_GUIDE",
        "GASB Implementation Guide",
        ("num",),
    ),
    (
        r"(?i)\bGASB\s+Concepts?\s+Statement\s+(?:No\.?\s+)?(?P<num>\d{1,3})",
        "CONCEPTS_STATEMENT",
        "GASB Concepts Statement No.",
        ("num",),
    ),
    (
        r"(?i)\bGASB\s+Tech(?:nical)?\.?\s*Bull(?:etin)?\.?\s+(?P<num>\d{4}-\d{1,3})",
        "TECHNICAL_BULLETIN",
        "GASB Technical Bulletin",
        ("num",),
    ),
    (
        r"(?i)\bGASB\s+Interpretation\s+(?:No\.?\s+)?(?P<num>\d{1,3})",
        "INTERPRETATION",
        "GASB Interpretation No.",
        ("num",),
    ),
    (
        r"(?i)\bGASB\s+Statement\s+(?:No\.?\s+)?(?P<num>\d{1,3})"
        r"(?:\s*,?\s*(?:¶|paragraph|para\.?)\s*(?P<para>\d+[A-Z]?))?",
        "STATEMENT",
        "GASB Statement No.",
        ("num", "para"),
    ),
)


@lru_cache(maxsize=1)
def _gasb_matchers() -> tuple[tuple[GASBDocKind, str, tuple[str, ...], RegexMatcher], ...]:
    return tuple((kind, prefix, names, regex(pat)) for pat, kind, prefix, names in _GASB_DEFS)


def extract_gasb_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[GASBCitation]:
    if not text:
        return []
    out: list[GASBCitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, prefix, names, matcher in _gasb_matchers():
        idx = {n: i + 1 for i, n in enumerate(names)}
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            num = m.groups[idx["num"]] if "num" in idx and idx["num"] < len(m.groups) else ""
            paragraph: str | None = (
                m.groups[idx["para"]] if "para" in idx and idx["para"] < len(m.groups) else None
            )
            if not num:
                continue
            normalized = f"{prefix} {num}"
            if paragraph:
                normalized = f"{normalized} ¶ {paragraph}"
            out.append(
                GASBCitation(
                    raw=m.text,
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    doc_kind=kind,
                    number=num,
                    paragraph=paragraph,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# FASAB
# ---------------------------------------------------------------------------

_FASAB_DEFS: tuple[tuple[str, FASABDocKind, str], ...] = (
    (
        r"(?i)\bFASAB\s+SFFAS\s+(?:No\.?\s+)?(?P<num>\d{1,3})",
        "SFFAS",
        "FASAB SFFAS",
    ),
    (
        r"(?i)\bFASAB\s+Concepts?\s+Statement\s+(?:No\.?\s+)?(?P<num>\d{1,3})",
        "CONCEPTS_STATEMENT",
        "FASAB Concepts Statement",
    ),
    (
        r"(?i)\bFASAB\s+Interpretation\s+(?:No\.?\s+)?(?P<num>\d{1,3})",
        "INTERPRETATION",
        "FASAB Interpretation",
    ),
    (
        r"(?i)\bFASAB\s+Tech(?:nical)?\.?\s*Bull(?:etin)?\.?\s+(?P<num>\d{4}-\d{1,3})",
        "TECHNICAL_BULLETIN",
        "FASAB Technical Bulletin",
    ),
)


@lru_cache(maxsize=1)
def _fasab_matchers() -> tuple[tuple[FASABDocKind, str, RegexMatcher], ...]:
    return tuple((kind, prefix, regex(pat)) for pat, kind, prefix in _FASAB_DEFS)


def extract_fasab_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FASABCitation]:
    if not text:
        return []
    out: list[FASABCitation] = []
    seen: set[tuple[int, int]] = set()
    for kind, prefix, matcher in _fasab_matchers():
        for m in matcher.find_all(text):
            span = (m.start, m.end)
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
                continue
            seen.add(span)
            num = m.groups[1] if len(m.groups) > 1 else ""
            if not num:
                continue
            normalized = f"{prefix} {num}"
            out.append(
                FASABCitation(
                    raw=m.text,
                    normalized=normalized,
                    span=span,
                    source_uri=source_uri,
                    doc_kind=kind,
                    number=num,
                )
            )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Government audit (OMB Circulars + GAO Yellow Book / Reports)
# ---------------------------------------------------------------------------

_OMB_CIRCULAR_PATTERN = r"(?i)\bOMB\s+Circular\s+(?P<id>[A-Z]-\d{1,4})"
_OMB_MEMO_PATTERN = r"(?i)\bOMB\s+(?:Memorandum|Memo)\s+M-(?P<id>\d{2}-\d{1,4})"
_GAO_REPORT_PATTERN = r"(?i)\bGAO[-/](?P<id>\d{2,3}-\d{1,7})\b"
_YELLOW_BOOK_PATTERN = (
    r"(?i)"
    r"\b(?:GAO\s+Yellow\s+Book|Yellow\s+Book|Government\s+Auditing\s+Standards)"
    r"(?:\s*\(\s*(?P<year>\d{4})(?:\s+Rev\.?)?\s*\))?"
)


@lru_cache(maxsize=1)
def _omb_circular_matcher():  # type: ignore[no-untyped-def]
    return regex(_OMB_CIRCULAR_PATTERN)


@lru_cache(maxsize=1)
def _omb_memo_matcher():  # type: ignore[no-untyped-def]
    return regex(_OMB_MEMO_PATTERN)


@lru_cache(maxsize=1)
def _gao_report_matcher():  # type: ignore[no-untyped-def]
    return regex(_GAO_REPORT_PATTERN)


@lru_cache(maxsize=1)
def _yellow_book_matcher():  # type: ignore[no-untyped-def]
    return regex(_YELLOW_BOOK_PATTERN)


def extract_government_audit_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[GovernmentAuditCitation]:
    if not text:
        return []
    out: list[GovernmentAuditCitation] = []
    seen: set[tuple[int, int]] = set()

    for m in _omb_circular_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        doc_id = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            GovernmentAuditCitation(
                raw=m.text,
                normalized=f"OMB Circular {doc_id}",
                span=span,
                source_uri=source_uri,
                doc_kind="OMB_CIRCULAR",
                document_id=doc_id,
            )
        )
    for m in _omb_memo_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        doc_id = f"M-{m.groups[1] if len(m.groups) > 1 else ''}"
        out.append(
            GovernmentAuditCitation(
                raw=m.text,
                normalized=f"OMB Memorandum {doc_id}",
                span=span,
                source_uri=source_uri,
                doc_kind="OMB_MEMORANDUM",
                document_id=doc_id,
            )
        )
    for m in _gao_report_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        doc_id = f"GAO-{m.groups[1] if len(m.groups) > 1 else ''}"
        out.append(
            GovernmentAuditCitation(
                raw=m.text,
                normalized=doc_id,
                span=span,
                source_uri=source_uri,
                doc_kind="GAO_REPORT",
                document_id=doc_id,
            )
        )
    for m in _yellow_book_matcher().find_all(text):
        span = (m.start, m.end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        year = _parse_int(m.groups[1] if len(m.groups) > 1 else None)
        normalized = "Government Auditing Standards"
        if year:
            normalized = f"{normalized} ({year} Rev.)"
        out.append(
            GovernmentAuditCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                doc_kind="GAO_YELLOWBOOK",
                revision_year=year,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# NAIC SAP/SSAP
# ---------------------------------------------------------------------------

_NAIC_SAP_PATTERN = (
    r"(?i)"
    r"\bNAIC\s+SSAP\s+(?:No\.?\s+)?(?P<num>\d{1,3}[A-Z]?)"
    r"(?:\s*,?\s*(?P<title>[A-Z][^.\n]{2,80}?))?"
    r"(?P<terminator>\s*(?:\(|\.|;|,|\n|$))"
)


@lru_cache(maxsize=1)
def _naic_sap_matcher():  # type: ignore[no-untyped-def]
    return regex(_NAIC_SAP_PATTERN)


def extract_naic_accounting_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[NAICAccountingCitation]:
    if not text:
        return []
    out: list[NAICAccountingCitation] = []
    for m in _naic_sap_matcher().find_all(text):
        # groups: [whole, num, title, terminator]
        num = m.groups[1] if len(m.groups) > 1 else ""
        title = m.groups[2] if len(m.groups) > 2 else None
        terminator = m.groups[3] if len(m.groups) > 3 else ""
        if not num:
            continue
        if title:
            title = title.strip().rstrip(",")
        end = m.end - len(terminator) if terminator else m.end
        normalized = f"NAIC SSAP No. {num}"
        if title:
            normalized = f"{normalized}, {title}"
        out.append(
            NAICAccountingCitation(
                raw=text[m.start : end],
                normalized=normalized,
                span=(m.start, end),
                source_uri=source_uri,
                ssap_number=num,
                title=title,
            )
        )
    out.sort(key=lambda c: c.span[0])
    return out


# ---------------------------------------------------------------------------
# Sustainability / ESG
# ---------------------------------------------------------------------------

_GRI_PATTERN = (
    r"(?i)"
    r"\bGRI\s+(?P<num>\d{1,4}(?:-\d{1,3})?)"
    r"(?:\s*[:\-]\s*(?P<title>[A-Z][^,\n]{2,60}?))?"
    r"(?:\s+(?P<year>\d{4}))?"
    r"(?P<terminator>\s*(?:\.|;|,|\)|\n|$))"
)
_SASB_PATTERN = r"\b(?:SASB\s+)?(?P<code>[A-Z]{2}-[A-Z]{2}-\d{2,3}[a-z]?\.\d+)"
_TCFD_PATTERN = (
    r"(?i)"
    r"\bTCFD(?:\s+(?P<title>(?:Recommended\s+)?Disclosures))?"
    r"(?:\s*\(\s*(?P<date>[A-Za-z\.]+\s+\d{4}|\d{4}-\d{2}-\d{2})\s*\))?"
)
_ISSB_PATTERN = (
    r"(?i)"
    r"\bIFRS\s+(?P<num>S[12])"
    r"(?:\.(?P<para>\d+[A-Z]?))?"
)
_ESRS_PATTERN = r"(?i)\bESRS\s+(?P<code>[A-Z]?\d{1,3})"


@lru_cache(maxsize=1)
def _gri_matcher():  # type: ignore[no-untyped-def]
    return regex(_GRI_PATTERN)


@lru_cache(maxsize=1)
def _sasb_matcher():  # type: ignore[no-untyped-def]
    return regex(_SASB_PATTERN)


@lru_cache(maxsize=1)
def _tcfd_matcher():  # type: ignore[no-untyped-def]
    return regex(_TCFD_PATTERN)


@lru_cache(maxsize=1)
def _issb_matcher():  # type: ignore[no-untyped-def]
    return regex(_ISSB_PATTERN)


@lru_cache(maxsize=1)
def _esrs_matcher():  # type: ignore[no-untyped-def]
    return regex(_ESRS_PATTERN)


def extract_sustainability_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[SustainabilityCitation]:
    if not text:
        return []
    out: list[SustainabilityCitation] = []
    seen: set[tuple[int, int]] = set()

    # GRI: groups [whole, num, title, year, terminator]
    for m in _gri_matcher().find_all(text):
        # Compute span without the terminator.
        terminator = m.groups[4] if len(m.groups) > 4 else ""
        end = m.end - len(terminator) if terminator else m.end
        span = (m.start, end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        num = m.groups[1] if len(m.groups) > 1 else ""
        title = m.groups[2] if len(m.groups) > 2 else None
        if title:
            title = title.strip()
        year = _parse_int(m.groups[3] if len(m.groups) > 3 else None)
        normalized = f"GRI {num}"
        if title:
            normalized = f"{normalized}: {title}"
        if year:
            normalized = f"{normalized} {year}"
        out.append(
            SustainabilityCitation(
                raw=text[m.start : end],
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                framework="GRI",
                standard_id=num,
                title=title,
                version_year=year,
            )
        )

    for m in _sasb_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        code = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            SustainabilityCitation(
                raw=m.text,
                normalized=f"SASB {code}",
                span=span,
                source_uri=source_uri,
                framework="SASB",
                standard_id=code,
            )
        )

    for m in _issb_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        num = (m.groups[1] or "").upper() if len(m.groups) > 1 else ""
        para = m.groups[2] if len(m.groups) > 2 else None
        normalized = f"IFRS {num}"
        if para:
            normalized = f"{normalized}.{para}"
        out.append(
            SustainabilityCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                framework="ISSB",
                standard_id=num,
            )
        )

    for m in _esrs_matcher().find_all(text):
        span = (m.start, m.end)
        if span in seen:
            continue
        seen.add(span)
        code = m.groups[1] if len(m.groups) > 1 else ""
        out.append(
            SustainabilityCitation(
                raw=m.text,
                normalized=f"ESRS {code}",
                span=span,
                source_uri=source_uri,
                framework="ESRS",
                standard_id=code,
            )
        )

    for m in _tcfd_matcher().find_all(text):
        span = (m.start, m.end)
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen):
            continue
        seen.add(span)
        title = m.groups[1] if len(m.groups) > 1 else None
        date = m.groups[2] if len(m.groups) > 2 else None
        normalized = "TCFD"
        if title:
            normalized = f"{normalized} {title.strip()}"
        if date:
            normalized = f"{normalized} ({date})"
        out.append(
            SustainabilityCitation(
                raw=m.text,
                normalized=normalized,
                span=span,
                source_uri=source_uri,
                framework="TCFD",
                title=title.strip() if title else None,
                exact_date=date,
            )
        )

    out.sort(key=lambda c: c.span[0])
    return out


__all__ = [
    "extract_aicpa_citations",
    "extract_asc_citations",
    "extract_asu_citations",
    "extract_fasab_citations",
    "extract_gasb_citations",
    "extract_government_audit_citations",
    "extract_iaasb_citations",
    "extract_iesba_citations",
    "extract_ifrs_citations",
    "extract_legacy_fasb_citations",
    "extract_naic_accounting_citations",
    "extract_pcaob_citations",
    "extract_sustainability_citations",
]
