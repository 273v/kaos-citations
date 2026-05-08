"""US Constitution citation extractor — kaos-nlp-core, no `re`.

eyecite does not recognize ``U.S. Const.`` citations; this is a small
parser that handles the Bluebook citation form for both article and
amendment.

Coverage:
- ``U.S. Const. art. III``, ``U.S. Const. art. III, § 2``,
  ``U.S. Const. art. I, § 8, cl. 3``
- ``U.S. Const. amend. I``, ``U.S. Const. amend. XIV, § 1``
- Variants: ``U.S. CONST.``, ``United States Constitution``

Article and amendment numbers are Roman; sections and clauses are
Arabic.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatchSpan, regex
from kaos_citations.model import ConstitutionCitation

# Roman numeral pattern — covers up through XXVII for amendments.
_ROMAN = r"(?:M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"

# The "U.S. Const." or "United States Constitution" preamble.
_PREAMBLE = r"(?:U\.\s*S\.\s*Const\.|United\s+States\s+Constitution)"

# Section/clause tail (both optional, order-dependent).
_TAIL = r"(?:[,\s]+§\s*(?P<section>\d+))?(?:[,\s]+cl\.\s*(?P<clause>\d+))?"

# Article form. The Rust regex crate accepts inline ``(?i)`` for
# case-insensitive matching.
_ARTICLE_PATTERN = r"(?i)" + _PREAMBLE + r"[,\s]*art\.?\s+(?P<article>" + _ROMAN + r")" + _TAIL

# Amendment form.
_AMENDMENT_PATTERN = (
    r"(?i)"
    + _PREAMBLE
    + r"[,\s]*amend\.?\s+(?P<amendment>"
    + _ROMAN
    + r")"
    + r"(?:[,\s]+§\s*(?P<section>\d+))?"
)


@lru_cache(maxsize=1)
def _article_matcher():  # type: ignore[no-untyped-def]
    return regex(_ARTICLE_PATTERN)


@lru_cache(maxsize=1)
def _amendment_matcher():  # type: ignore[no-untyped-def]
    return regex(_AMENDMENT_PATTERN)


def iter_constitution_matches(text: str) -> Iterator[RegexMatchSpan]:
    """Yield every match (article + amendment combined, source-ordered)."""
    matches = list(_article_matcher().find_all(text)) + list(_amendment_matcher().find_all(text))
    matches.sort(key=lambda m: m.start)
    yield from matches


def extract_constitution_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[ConstitutionCitation]:
    """Extract every US Constitution citation from ``text``.

    Article and amendment forms are merged into one source-ordered
    result list; the ``article`` and ``amendment`` fields are mutually
    exclusive on each citation.
    """
    results: list[ConstitutionCitation] = []
    seen_spans: set[tuple[int, int]] = set()

    # Article matches:
    # groups[0] = full match, then named groups in declaration order:
    # 1=article, 2=section, 3=clause
    for match in _article_matcher().find_all(text):
        span = (match.start, match.end)
        if span in seen_spans:
            continue
        seen_spans.add(span)
        article = match.groups[1].upper() if match.groups[1] else ""
        section = match.groups[2] if len(match.groups) > 2 else None
        clause = match.groups[3] if len(match.groups) > 3 else None
        normalized_parts = [f"U.S. Const. art. {article}"]
        if section:
            normalized_parts.append(f"§ {section}")
        if clause:
            normalized_parts.append(f"cl. {clause}")
        results.append(
            ConstitutionCitation(
                raw=match.text,
                normalized=", ".join(normalized_parts),
                span=span,
                source_uri=source_uri,
                article=article,
                amendment=None,
                section=section,
                clause=clause,
            )
        )

    # Amendment matches: groups 1=amendment, 2=section
    for match in _amendment_matcher().find_all(text):
        span = (match.start, match.end)
        if span in seen_spans:
            continue
        seen_spans.add(span)
        amendment = match.groups[1].upper() if match.groups[1] else ""
        section = match.groups[2] if len(match.groups) > 2 else None
        normalized_parts = [f"U.S. Const. amend. {amendment}"]
        if section:
            normalized_parts.append(f"§ {section}")
        results.append(
            ConstitutionCitation(
                raw=match.text,
                normalized=", ".join(normalized_parts),
                span=span,
                source_uri=source_uri,
                article=None,
                amendment=amendment,
                section=section,
                clause=None,
            )
        )

    results.sort(key=lambda c: c.span[0])
    return results


__all__ = ["extract_constitution_citations", "iter_constitution_matches"]
