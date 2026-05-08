"""PubMed PMID extractor — kaos-nlp-core RegexMatcher, no `re`.

Coverage:
- ``PMID:12345678``
- ``PMID 12345678``
- ``pubmed:12345678``
- ``https://pubmed.ncbi.nlm.nih.gov/12345678/``
- ``https://www.ncbi.nlm.nih.gov/pubmed/12345678``

Normalized form: ``PMID:<integer>``. PMCID is intentionally not
extracted (separate registry).
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatchSpan, regex
from kaos_citations.model import PubMedCitation

_PMID_PATTERN = (
    r"(?i)"
    r"(?P<prefix>"
    r"PMID[:\s]+"
    r"|pubmed[:\s]+"
    r"|https?://(?:www\.)?(?:pubmed\.)?ncbi\.nlm\.nih\.gov/(?:pubmed/)?"
    r")"
    r"(?P<pmid>\d{1,9})"
    r"/?"
)


@lru_cache(maxsize=1)
def _matcher():  # type: ignore[no-untyped-def]
    return regex(_PMID_PATTERN)


def iter_pubmed_matches(text: str) -> Iterator[RegexMatchSpan]:
    """Yield every RegexMatchSpan for diagnostic / test use."""
    yield from _matcher().find_all(text)


def extract_pubmed_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[PubMedCitation]:
    """Extract every PubMed PMID citation from ``text``."""
    results: list[PubMedCitation] = []
    for match in iter_pubmed_matches(text):
        # groups[0] = whole, [1] = prefix, [2] = pmid
        pmid_str = match.groups[2] if len(match.groups) > 2 else None
        if not pmid_str:
            continue
        try:
            pmid = int(pmid_str)
        except (TypeError, ValueError):
            continue
        if pmid < 1:
            continue
        normalized = f"PMID:{pmid}"
        results.append(
            PubMedCitation(
                raw=match.text,
                normalized=normalized,
                span=(match.start, match.end),
                source_uri=source_uri,
                pmid=pmid,
            )
        )
    return results


__all__ = ["extract_pubmed_citations", "iter_pubmed_matches"]
