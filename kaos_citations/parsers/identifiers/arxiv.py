"""arXiv ID extractor — kaos-nlp-core RegexMatcher, no `re`.

Coverage:
- ``arXiv:2401.12345``, ``arxiv:2401.12345v2``
- ``arXiv:hep-th/0001234``, ``arXiv:math.AG/9903012``
- ``https://arxiv.org/abs/<id>``, ``https://arxiv.org/pdf/<id>``

Normalized form: ``arXiv:<id>``.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatchSpan, regex
from kaos_citations.model import ArXivCitation

# New-style: YYMM.NNNNN (4 digits before 2015, 5 since), optional vN.
_NEW_STYLE = r"\d{4}\.\d{4,5}(?:v\d+)?"
# Old-style: category[.subject]/NNNNNNN
_OLD_STYLE = r"[a-z]+(?:-[a-z]+)*(?:\.[A-Z]{2})?/\d{7}"
_ID = rf"(?P<arxiv_id>{_NEW_STYLE}|{_OLD_STYLE})"

# Three accepted surface forms (case-insensitive via inline ``(?i)``).
_ARXIV_PATTERN = (
    r"(?i)"
    r"(?P<prefix>"
    r"arxiv:\s*"
    r"|https?://arxiv\.org/(?:abs|pdf)/"
    r")" + _ID
)

# Trailing ``.pdf`` stripper for PDF URLs.
_PDF_SUFFIX_PATTERN = r"(?i)\.pdf$"


@lru_cache(maxsize=1)
def _matcher():  # type: ignore[no-untyped-def]
    return regex(_ARXIV_PATTERN)


@lru_cache(maxsize=1)
def _pdf_suffix():  # type: ignore[no-untyped-def]
    return regex(_PDF_SUFFIX_PATTERN)


def iter_arxiv_matches(text: str) -> Iterator[RegexMatchSpan]:
    """Yield every RegexMatchSpan for diagnostic / test use."""
    yield from _matcher().find_all(text)


def extract_arxiv_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[ArXivCitation]:
    """Extract every arXiv citation from ``text``."""
    results: list[ArXivCitation] = []
    for match in iter_arxiv_matches(text):
        # groups[0] = whole, [1] = prefix, [2] = arxiv_id
        arxiv_id = match.groups[2] if len(match.groups) > 2 else None
        if not arxiv_id:
            continue
        # Strip ``.pdf`` suffix from PDF-URL captures.
        arxiv_id = _pdf_suffix().replace_all(arxiv_id, "")
        raw = match.text
        normalized = f"arXiv:{arxiv_id}"
        results.append(
            ArXivCitation(
                raw=raw,
                normalized=normalized,
                span=(match.start, match.end),
                source_uri=source_uri,
                arxiv_id=arxiv_id,
            )
        )
    return results


__all__ = ["extract_arxiv_citations", "iter_arxiv_matches"]
