"""Federal Rules + Supreme Court Rules + USSG parser — kaos-nlp-core, no `re`.

Coverage:
- Fed. R. Civ. P. / Crim. P. / Evid. / App. P. / Bankr. P.
- Sup. Ct. R.
- U.S.S.G. § ...
- FRCP / FRE / FRAP / FRBP shorthand forms
- Advisory-committee notes
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from functools import lru_cache
from typing import cast

from kaos_citations.matchers import RegexMatcher, RegexMatchSpan, regex
from kaos_citations.model import FederalRuleCitation, FederalRuleSet, USSGCitation

# ---------------------------------------------------------------------------
# Federal rule prefixes → rule set
# ---------------------------------------------------------------------------

# Each entry: (pattern_string, rule_set_tag). Rust regex; case-insensitive
# via inline ``(?i)`` where needed. Order matters: longer prefixes first.
_FED_RULE_PATTERN_DEFS: tuple[tuple[str, FederalRuleSet], ...] = (
    (r"(?i)\bFed\.?\s*R\.?\s*Civ\.?\s*P\.?\b", "FRCP"),
    (r"\bFRCP\b", "FRCP"),
    (r"(?i)\bFed\.?\s*R\.?\s*Crim\.?\s*P\.?\b", "FRCRMP"),
    (r"(?i)\bFRCrimP\b", "FRCRMP"),
    (r"(?i)\bFed\.?\s*R\.?\s*Evid\.?\b", "FRE"),
    (r"\bFRE\b", "FRE"),
    (r"(?i)\bFed\.?\s*R\.?\s*App\.?\s*P\.?\b", "FRAP"),
    (r"\bFRAP\b", "FRAP"),
    (r"(?i)\bFed\.?\s*R\.?\s*Bankr\.?\s*P\.?\b", "FRBP"),
    (r"\bFRBP\b", "FRBP"),
    (r"(?i)\bSup\.?\s*Ct\.?\s*R\.?\b", "SCT"),
)


@lru_cache(maxsize=1)
def _fed_rule_matchers() -> tuple[tuple[FederalRuleSet, RegexMatcher], ...]:
    """Compile every prefix pattern once. Returns (rule_set,
    RegexMatcher) pairs keyed by declaration order so we can recover
    the rule_set tag from the matcher."""
    return tuple((rs, regex(p)) for p, rs in _FED_RULE_PATTERN_DEFS)


# Rule body grammar — matches at the position just after the prefix.
# Includes a leading ``\.?`` so we swallow a trailing prefix dot
# that fell off the prefix's ``\b`` anchor.
_RULE_BODY_PATTERN = (
    r"(?i)"
    r"\.?\s*"
    r"(?:Rule\s+|§\s*|R\.\s+|R\.?\s*)?"
    r"(?P<rule>\d+(?:\.\d+)?(?:[a-z])?)"
    r"(?P<subs>(?:\([^)]{1,12}\)){0,8})"
)

_ACN_PATTERN = r"(?i)\s*advisory\s+committee'?s?\s+note(?:\s+to\s+(?P<year>\d{4})\s+amendment)?"

_SUBDIV_SPLIT_PATTERN = r"\(([^)]+)\)"

_USSG_PATTERN = (
    r"(?i)"
    r"\b(?:"
    r"U\.?\s*S\.?\s*S\.?\s*G\.?"
    r"|USSG"
    r"|(?:U\.?\s*S\.?\s*)?Sentencing\s+Guidelines?"
    r")"
    r"\s*(?:§\s*|Section\s+|sec\.?\s+)?"
    r"(?P<section>\d+[A-Z]?\d+(?:\.\d+)?)"
    r"(?P<subs>(?:\([^)]{1,12}\)){0,6})"
)


@lru_cache(maxsize=1)
def _rule_body_matcher():  # type: ignore[no-untyped-def]
    return regex(_RULE_BODY_PATTERN)


@lru_cache(maxsize=1)
def _acn_matcher():  # type: ignore[no-untyped-def]
    return regex(_ACN_PATTERN)


@lru_cache(maxsize=1)
def _subdiv_split_matcher():  # type: ignore[no-untyped-def]
    return regex(_SUBDIV_SPLIT_PATTERN)


@lru_cache(maxsize=1)
def _ussg_matcher():  # type: ignore[no-untyped-def]
    return regex(_USSG_PATTERN)


def _split_subdivisions(subs: str | None) -> tuple[str, ...]:
    """Split ``(c)(1)(A)`` into ``("c", "1", "A")`` via Rust regex."""
    if not subs:
        return ()
    parts: list[str] = []
    for match in _subdiv_split_matcher().find_all(subs):
        # groups[0] = whole, groups[1] = inner
        inner = match.groups[1] if len(match.groups) > 1 else ""
        if inner.strip():
            parts.append(inner.strip())
    return tuple(parts)


class _AbsoluteSpan:
    """Adapter that translates a relative RegexMatchSpan into one
    whose ``start`` / ``end`` are document-absolute offsets."""

    def __init__(self, inner: RegexMatchSpan, base: int) -> None:
        self._inner = inner
        self._base = base

    @property
    def start(self) -> int:
        return self._inner.start + self._base

    @property
    def end(self) -> int:
        return self._inner.end + self._base

    @property
    def text(self) -> str:
        return self._inner.text

    @property
    def groups(self) -> list[str | None]:
        return self._inner.groups


def _match_body_anchored(text: str, pos: int) -> _AbsoluteSpan | None:
    """Run the rule-body regex against ``text[pos:]`` and require the
    match to start at offset 0 (i.e. immediately after the prefix).
    Returns a span with absolute offsets relative to ``text``, or
    ``None`` when the body doesn't match."""
    sub = text[pos:]
    if not sub:
        return None
    hit = _rule_body_matcher().find_first(sub)
    if hit is None or hit.start != 0:
        return None
    # Wrap the inner span as a span-with-absolute-offsets shim.
    return _AbsoluteSpan(hit, pos)


def iter_federal_rule_matches(
    text: str,
) -> Iterator[tuple[FederalRuleSet, RegexMatchSpan, _AbsoluteSpan]]:
    """Yield ``(rule_set, prefix_match, body_match)`` triples."""
    if not text:
        return
    seen: set[tuple[int, int]] = set()
    for rule_set, matcher in _fed_rule_matchers():
        for prefix_match in matcher.find_all(text):
            body = _match_body_anchored(text, prefix_match.end)
            if body is None:
                continue
            span = (prefix_match.start, body.end)
            if span in seen:
                continue
            seen.add(span)
            yield rule_set, prefix_match, body


_RULE_SET_DISPLAY: dict[str, str] = {
    "FRCP": "Fed. R. Civ. P.",
    "FRCRMP": "Fed. R. Crim. P.",
    "FRE": "Fed. R. Evid.",
    "FRAP": "Fed. R. App. P.",
    "FRBP": "Fed. R. Bankr. P.",
    "SCT": "Sup. Ct. R.",
}


def _normalize_fed_rule(
    rule_set: FederalRuleSet,
    rule_number: str,
    subdivisions: tuple[str, ...],
    is_acn: bool,
    amendment_year: int | None,
) -> str:
    prefix = _RULE_SET_DISPLAY.get(rule_set, cast("str", rule_set))
    subs = "".join(f"({s})" for s in subdivisions)
    base = f"{prefix} {rule_number}{subs}"
    if is_acn:
        if amendment_year:
            base = f"{base} advisory committee's note to {amendment_year} amendment"
        else:
            base = f"{base} advisory committee's note"
    return base


def extract_federal_rule_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[FederalRuleCitation]:
    """Extract Federal Rules + Supreme Court Rules citations."""
    if not text:
        return []
    acn_matcher = _acn_matcher()

    results: list[FederalRuleCitation] = []
    for rule_set, prefix_match, body in iter_federal_rule_matches(text):
        start = prefix_match.start
        end = body.end

        is_acn = False
        amendment_year: int | None = None
        # Anchor ACN match immediately after the body.
        sub_after = text[end:]
        if sub_after:
            acn_hit = acn_matcher.find_first(sub_after)
            if acn_hit is not None and acn_hit.start == 0:
                is_acn = True
                # groups[1] = year (named group)
                year_str = acn_hit.groups[1] if len(acn_hit.groups) > 1 else None
                if year_str:
                    with contextlib.suppress(ValueError):
                        amendment_year = int(year_str)
                end = end + acn_hit.end

        rule_number = body.groups[1] if len(body.groups) > 1 else ""
        if not rule_number:
            continue
        subs_raw = body.groups[2] if len(body.groups) > 2 else ""
        subdivisions = _split_subdivisions(subs_raw)
        raw = text[start:end]
        results.append(
            FederalRuleCitation(
                raw=raw,
                normalized=_normalize_fed_rule(
                    rule_set, rule_number, subdivisions, is_acn, amendment_year
                ),
                span=(start, end),
                source_uri=source_uri,
                rule_set=rule_set,
                rule_number=rule_number,
                subdivisions=subdivisions,
                is_advisory_committee_note=is_acn,
                amendment_year=amendment_year,
            )
        )

    results.sort(key=lambda c: c.span[0])
    return results


# ---------------------------------------------------------------------------
# USSG
# ---------------------------------------------------------------------------


def iter_ussg_matches(text: str) -> Iterator[RegexMatchSpan]:
    yield from _ussg_matcher().find_all(text)


def extract_ussg_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[USSGCitation]:
    if not text:
        return []
    results: list[USSGCitation] = []
    for match in iter_ussg_matches(text):
        # groups[0] = whole, [1] = section, [2] = subs
        section = match.groups[1] if len(match.groups) > 1 else ""
        if not section:
            continue
        subs_raw = match.groups[2] if len(match.groups) > 2 else ""
        subs = _split_subdivisions(subs_raw)
        results.append(
            USSGCitation(
                raw=match.text,
                normalized=f"U.S.S.G. § {section}{''.join(f'({s})' for s in subs)}",
                span=(match.start, match.end),
                source_uri=source_uri,
                section=section,
                subdivisions=subs,
            )
        )
    results.sort(key=lambda c: c.span[0])
    return results


__all__ = [
    "extract_federal_rule_citations",
    "extract_ussg_citations",
    "iter_federal_rule_matches",
    "iter_ussg_matches",
]
