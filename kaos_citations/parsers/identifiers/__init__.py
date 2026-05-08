"""Identifier-based citation parsers — DOI, arXiv, PubMed.

Each parser is a stateless function that takes raw text and returns a
list of typed :class:`~kaos_citations.model.Citation` instances.
"""

from __future__ import annotations

from kaos_citations.parsers.identifiers.arxiv import (
    extract_arxiv_citations,
    iter_arxiv_matches,
)
from kaos_citations.parsers.identifiers.doi import (
    extract_doi_citations,
    iter_doi_matches,
)
from kaos_citations.parsers.identifiers.pubmed import (
    extract_pubmed_citations,
    iter_pubmed_matches,
)

__all__ = [
    "extract_arxiv_citations",
    "extract_doi_citations",
    "extract_pubmed_citations",
    "iter_arxiv_matches",
    "iter_doi_matches",
    "iter_pubmed_matches",
]
