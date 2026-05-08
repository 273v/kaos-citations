"""DOI extractor — kaos-nlp-core RegexMatcher, no `re`.

Coverage:
- Bare DOI: ``10.1145/3133956.3134105``
- ``doi:`` prefix: ``doi:10.1109/TPAMI.2020.3001905``
- URL: ``https://doi.org/10.1038/nature12373``,
  ``http://dx.doi.org/10.1000/xyz``

Normalized form: ``https://doi.org/<suffix>``.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatchSpan, regex
from kaos_citations.model import DOICitation

# Crossref's recommended pattern, with optional URL prefix.
# ``(?i)`` inline flag = case-insensitive.
_DOI_PATTERN = (
    r"(?i)"
    r"(?P<prefix>https?://(?:dx\.)?doi\.org/|doi:\s*)?"
    r"(?P<doi>10\.\d{4,9}/[-._;()/:a-z0-9]+)"
)


@lru_cache(maxsize=1)
def _matcher():  # type: ignore[no-untyped-def]
    return regex(_DOI_PATTERN)


def iter_doi_matches(text: str) -> Iterator[RegexMatchSpan]:
    """Yield every RegexMatchSpan for diagnostic / test use."""
    yield from _matcher().find_all(text)


def extract_doi_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[DOICitation]:
    """Extract every DOI citation from ``text``."""
    results: list[DOICitation] = []
    for match in iter_doi_matches(text):
        # groups[0] = full, groups[1] = prefix, groups[2] = doi
        doi = match.groups[2] if len(match.groups) > 2 else ""
        if not doi or "/" not in doi:
            continue
        # Strip trailing sentence punctuation greedily included by the
        # permissive suffix character class.
        doi_trimmed = doi.rstrip(".,;:)")
        if "/" not in doi_trimmed or len(doi_trimmed.split("/", 1)[1]) == 0:
            continue
        match_start = match.start
        match_end = match.end
        # Adjust the matched span to drop the same trailing punctuation
        # we trimmed from the DOI suffix.
        raw = match.text
        trimmed_raw = raw.rstrip(".,;:)")
        match_end = match_start + len(trimmed_raw)
        normalized = f"https://doi.org/{doi_trimmed}"
        results.append(
            DOICitation(
                raw=trimmed_raw,
                normalized=normalized,
                span=(match_start, match_end),
                source_uri=source_uri,
                doi=doi_trimmed,
            )
        )
    return results


__all__ = ["extract_doi_citations", "iter_doi_matches"]
