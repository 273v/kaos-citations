"""Internet + archive parser — kaos-nlp-core RegexMatcher, no `re`.

Covers Bluebook R18:

- Generic internet citations (R18.1): plain URLs with optional
  ``last visited`` tail.
- Web archives (R18.3): ``web.archive.org/web/<timestamp>/<url>`` and
  ``perma.cc/<short-code>``.

Outputs:
- :class:`InternetCitation` for plain URLs.
- :class:`ArchiveCitation` for Wayback / Perma.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from kaos_citations.matchers import RegexMatchSpan, regex
from kaos_citations.model import ArchiveCitation, InternetCitation

# Practical URL pattern — protocol + path body, stopping at whitespace
# or closing brackets/parens.
_URL_PATTERN = r"""https?://[^\s<>"'\)\]]+"""

# Optional ``last visited`` tail (Bluebook R18.1).
_LAST_VISITED_PATTERN = (
    r"(?i)"
    r"\s*\(?\s*"
    r"last\s+visited\s+"
    r"(?P<date>"
    r"[A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r")"
    r"\s*\)?"
)

# Anchored archive patterns — match must span the entire URL.
# ``\A`` / ``\z`` anchor at start / end of input (Rust regex syntax).
_WAYBACK_PATTERN = r"\Ahttps?://(?:www\.)?web\.archive\.org/web/(?P<ts>\d{14})/(?P<orig>.+)\z"
_PERMA_PATTERN = r"\Ahttps?://(?:www\.)?perma\.cc/(?P<code>[A-Za-z0-9\-]+)/?\z"

_TRAILING_PUNCT = ".,;:!?"


@lru_cache(maxsize=1)
def _url_matcher():  # type: ignore[no-untyped-def]
    return regex(_URL_PATTERN)


@lru_cache(maxsize=1)
def _last_visited_matcher():  # type: ignore[no-untyped-def]
    return regex(_LAST_VISITED_PATTERN)


@lru_cache(maxsize=1)
def _wayback_matcher():  # type: ignore[no-untyped-def]
    return regex(_WAYBACK_PATTERN)


@lru_cache(maxsize=1)
def _perma_matcher():  # type: ignore[no-untyped-def]
    return regex(_PERMA_PATTERN)


def _trim_url_trailing_punct(url: str) -> str:
    while url and url[-1] in _TRAILING_PUNCT:
        url = url[:-1]
    return url


def _detect_archive(url: str) -> tuple[str | None, str | None, str | None]:
    """Return ``(archive_url, archive_id, original_url)`` for Wayback /
    Perma URLs; otherwise ``(None, None, None)``."""
    wayback = _wayback_matcher().find_first(url)
    if wayback is not None and wayback.start == 0 and wayback.end == len(url):
        # groups: [whole, ts, orig]
        return url, wayback.groups[1], wayback.groups[2]
    perma = _perma_matcher().find_first(url)
    if perma is not None and perma.start == 0 and perma.end == len(url):
        return url, perma.groups[1], None
    return None, None, None


def iter_url_matches(text: str) -> Iterator[RegexMatchSpan]:
    """Yield every URL RegexMatchSpan."""
    yield from _url_matcher().find_all(text)


def extract_internet_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[InternetCitation]:
    """Extract plain URL citations (skipping archive URLs)."""
    if not text:
        return []
    out: list[InternetCitation] = []
    lv_matcher = _last_visited_matcher()
    for match in _url_matcher().find_all(text):
        url = _trim_url_trailing_punct(match.text)
        if not url:
            continue
        archive_url, _, _ = _detect_archive(url)
        if archive_url is not None:
            continue
        url_end = match.start + len(url)

        # Optional ``last visited`` tail. We restrict the lookup window
        # to the few-dozen chars immediately following the URL so the
        # matcher's leftmost-match doesn't pick up a distant ``last
        # visited`` clause from elsewhere.
        tail_window = text[url_end : min(len(text), url_end + 80)]
        last_visited: str | None = None
        end = url_end
        if tail_window:
            lv_hit = lv_matcher.find_first(tail_window)
            if lv_hit is not None and lv_hit.start == 0:
                # groups[1] = date
                last_visited = lv_hit.groups[1] if len(lv_hit.groups) > 1 else None
                end = url_end + lv_hit.end

        out.append(
            InternetCitation(
                raw=text[match.start : end],
                normalized=url,
                span=(match.start, end),
                source_uri=source_uri,
                url=url,
                last_visited=last_visited,
            )
        )
    return out


def extract_archive_citations(
    text: str,
    *,
    source_uri: str | None = None,
) -> list[ArchiveCitation]:
    """Extract Wayback Machine + Perma.cc citations."""
    if not text:
        return []
    out: list[ArchiveCitation] = []
    for match in _url_matcher().find_all(text):
        url = _trim_url_trailing_punct(match.text)
        archive_url, archive_id, original_url = _detect_archive(url)
        if archive_url is None:
            continue
        archive_date: str | None = None
        if archive_id and len(archive_id) == 14 and archive_id.isdigit():
            archive_date = f"{archive_id[0:4]}-{archive_id[4:6]}-{archive_id[6:8]}"
        url_end = match.start + len(url)
        out.append(
            ArchiveCitation(
                raw=url,
                normalized=archive_url,
                span=(match.start, url_end),
                source_uri=source_uri,
                archive_url=archive_url,
                archive_id=archive_id,
                original_url=original_url,
                archive_date=archive_date,
            )
        )
    return out


__all__ = [
    "extract_archive_citations",
    "extract_internet_citations",
    "iter_url_matches",
]
