"""CFR citation extractor — kaos-nlp-core RegexMatcher, no `re`.

Coverage:
- ``17 CFR 240.10b-5``
- ``21 CFR § 312.2``
- ``40 CFR Part 60.7(a)(1)``
- ``17 C.F.R. 240.10b5-1(c)(1)(i)``
- ``17 C.F.R. § 240.10b-5``

Normalized form is ``<title> CFR <section>``.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatchSpan, regex
from kaos_citations.model import CFRCitation

# Section grammar:
#   base   = digits(.digits)*(suffix)?     e.g. 240.10b-5 or 1.165-7
#   suffix = alpha-led (``b-5``) or hyphen-led digits (``-7``)
#   tail   = (alpha-digit parens){0,8}     e.g. (a)(1)(i)
#
# KCITE-02 (0.1.0a1): the subsection-tail repetition is capped at 8
# levels. Real-world CFR cites bottom out around 4 levels.
_SECTION_PATTERN = (
    r"[0-9]+(?:\.[0-9]+)*"
    r"(?:[-A-Za-z][A-Za-z0-9-]*)?"
    r"(?:\([A-Za-z0-9]+\)){0,8}"
)

_CFR_PATTERN = (
    r"\b(?P<title>[1-9][0-9]?)\s*"
    r"(?:C\.?\s*F\.?\s*R\.?|CFR)\s*"
    r"(?:Part\s+|part\s+|§\s*)?"
    r"(?P<section>" + _SECTION_PATTERN + r")"
)


@lru_cache(maxsize=1)
def _matcher():  # type: ignore[no-untyped-def]
    return regex(_CFR_PATTERN)


def iter_cfr_matches(text: str) -> Iterator[RegexMatchSpan]:
    """Yield every raw RegexMatchSpan. Exposed for diagnostic / test use."""
    yield from _matcher().find_all(text)


def extract_cfr_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[CFRCitation]:
    """Extract every CFR citation from ``text``."""
    results: list[CFRCitation] = []
    for match in iter_cfr_matches(text):
        # match.groups: [whole, title, section]
        title_str = match.groups[1] or ""
        section = match.groups[2] or ""
        if not title_str or not section:
            continue
        try:
            title = int(title_str)
        except (TypeError, ValueError):
            continue
        if title < 1 or title > 50:
            continue
        raw = match.text
        normalized = f"{title} CFR {section}"
        results.append(
            CFRCitation(
                raw=raw,
                normalized=normalized,
                span=(match.start, match.end),
                source_uri=source_uri,
                title=title,
                section=section,
            )
        )
    return results


__all__ = ["extract_cfr_citations", "iter_cfr_matches"]
