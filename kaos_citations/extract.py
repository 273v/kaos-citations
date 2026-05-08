"""Top-level ``extract_citations`` dispatcher.

A ``kinds`` filter is exposed so callers can opt-in to specific
families; unsupported or unknown kinds raise an agent-friendly
three-part error message so an LLM consumer can self-correct.
"""

from __future__ import annotations

from collections.abc import Iterable

from kaos_core.logging import get_logger

from kaos_citations.errors import CitationParseError
from kaos_citations.model import Citation
from kaos_citations.parsers.accounting import (
    extract_aicpa_citations,
    extract_asc_citations,
    extract_asu_citations,
    extract_fasab_citations,
    extract_gasb_citations,
    extract_government_audit_citations,
    extract_iaasb_citations,
    extract_iesba_citations,
    extract_ifrs_citations,
    extract_legacy_fasb_citations,
    extract_naic_accounting_citations,
    extract_pcaob_citations,
    extract_sustainability_citations,
)
from kaos_citations.parsers.agency import (
    extract_agency_adjudication_citations,
    extract_agency_manual_citations,
    extract_bar_ethics_citations,
    extract_legal_opinion_citations,
)
from kaos_citations.parsers.case import extract_case_family
from kaos_citations.parsers.cfr import extract_cfr_citations
from kaos_citations.parsers.constitution import extract_constitution_citations
from kaos_citations.parsers.federal_rules import (
    extract_federal_rule_citations,
    extract_ussg_citations,
)
from kaos_citations.parsers.identifiers import (
    extract_doi_citations,
    extract_pubmed_citations,
)
from kaos_citations.parsers.internet import (
    extract_archive_citations,
    extract_internet_citations,
)
from kaos_citations.parsers.legislative import (
    extract_legislative_citations,
    extract_public_law_citations,
    extract_restatement_citations,
    extract_uniform_act_citations,
)
from kaos_citations.parsers.regulatory import (
    extract_executive_action_citations,
    extract_irs_guidance_citations,
    extract_treasury_regulation_citations,
)
from kaos_citations.parsers.sec import (
    extract_basel_citations,
    extract_cfpb_citations,
    extract_cftc_citations,
    extract_exchange_rule_citations,
    extract_fdic_citations,
    extract_fed_reserve_letter_citations,
    extract_fed_reserve_regulation_citations,
    extract_ffiec_citations,
    extract_finra_disciplinary_citations,
    extract_finra_notice_citations,
    extract_finra_rule_citations,
    extract_international_finance_citations,
    extract_naic_citations,
    extract_ncua_citations,
    extract_occ_citations,
    extract_sec_filing_citations,
    extract_sec_regulation_citations,
    extract_sec_release_citations,
    extract_sec_staff_citations,
)
from kaos_citations.parsers.statute import (
    extract_federal_register_citations,
    extract_statute_citations,
)
from kaos_citations.postprocess import apply_postprocess

logger = get_logger(__name__)

# Stable ordering for deterministic output when multiple kinds produce
# overlapping matches. Match the order in the ``Citation`` union.
# Kinds run by default when no ``kinds=`` filter is given. All
# legal-relevant citation families. arXiv is excluded by default
# because lawyers rarely cite academic preprints — opt in via
# ``kinds=("arxiv", ...)`` to include it.
_SUPPORTED_KINDS: tuple[str, ...] = (
    "cfr",
    "case",
    "case_short",
    "id",
    "supra",
    "case_ref",
    "journal",
    "statute",
    "fed_register",
    "const",
    "fed_rule",
    "ussg",
    "treas_reg",
    "irs_guidance",
    "exec_action",
    "public_law",
    "legislative",
    "restatement",
    "uniform_act",
    "internet",
    "archive",
    "agency_adj",
    "agency_manual",
    "legal_opinion",
    "bar_ethics",
    # Phase 3 — financial
    "sec_filing",
    "sec_release",
    "sec_staff",
    "sec_reg",
    "finra_rule",
    "finra_notice",
    "finra_disciplinary",
    "exchange_rule",
    "fed_reserve_reg",
    "fed_reserve_letter",
    "fdic_doc",
    "occ_doc",
    "cfpb_doc",
    "ncua_letter",
    "basel",
    "cftc_doc",
    "naic",
    "intl_finance",
    "ffiec_call",
    # Phase 4 — accounting
    "asc",
    "asu",
    "legacy_fasb",
    "pcaob",
    "aicpa",
    "ifrs",
    "iaasb",
    "iesba",
    "gasb",
    "fasab",
    "govt_audit",
    "naic_acct",
    "sustainability",
    "doi",
    "pmid",
)

# Kinds whose dependencies live behind opt-in extras; if the extra
# isn't installed, a default-path call should skip the kind with a
# logger.info rather than crash the whole extraction. An explicit
# ``kinds=("case",)`` still raises so the caller's requested kind
# never silently disappears.
_KIND_TO_EXTRA: dict[str, str] = {
    "case": "legal",
    "case_short": "legal",
    "id": "legal",
    "supra": "legal",
    "case_ref": "legal",
    "journal": "legal",
    "statute": "legal",
    "fed_register": "legal",
}

# Opt-in kinds: parseable but excluded from the default extraction
# pass for relevance reasons. Caller can request explicitly via
# ``kinds=`` and the dispatcher will run them; just not on auto-pilot.
_OPT_IN_KINDS: tuple[str, ...] = ("arxiv",)

# Stub kinds — declared in the ``Citation`` union but not yet parseable.
_STUB_KINDS: tuple[str, ...] = ("unknown",)


def extract_citations(
    text: str,
    *,
    kinds: Iterable[str] | None = None,
    source_uri: str | None = None,
) -> list[Citation]:
    """Extract every citation of the requested kinds from ``text``.

    Args:
        text: Raw text to search.
        kinds: Optional iterable of citation kinds to extract (default:
            every supported kind). Unsupported kinds raise
            :class:`CitationParseError` so callers aren't silently
            short-changed by stubs that are in the union but not yet
            parseable.
        source_uri: Optional URI threaded onto every returned citation.

    Returns:
        List of :class:`Citation` in source order. Spans are absolute
        offsets into ``text``.

    Raises:
        CitationParseError: If ``kinds`` includes a stub not-yet-parseable
            citation family.
    """
    requested = tuple(kinds) if kinds is not None else _SUPPORTED_KINDS
    requested_set = frozenset(requested)

    unsupported = [k for k in requested if k in _STUB_KINDS]
    if unsupported:
        msg = (
            f"kaos-citations does not yet support kinds={unsupported!r}. "
            f"Fix: pass only kinds in {list(_SUPPORTED_KINDS + _OPT_IN_KINDS)!r}, "
            "or omit the ``kinds`` argument to use the default legal-relevant set."
        )
        raise CitationParseError(msg)

    valid = set(_SUPPORTED_KINDS) | set(_OPT_IN_KINDS) | set(_STUB_KINDS)
    invalid = [k for k in requested if k not in valid]
    if invalid:
        msg = (
            f"Unknown citation kinds={invalid!r}. "
            f"Fix: choose from {list(_SUPPORTED_KINDS + _OPT_IN_KINDS)!r}. "
            "Alternative: see kaos_citations.model for the full ``Citation`` union."
        )
        raise CitationParseError(msg)

    # KCITE-01: distinguish default-kinds from explicit-kinds for the
    # graceful-skip-vs-raise decision. A caller who omits ``kinds`` is
    # asking for "everything you can do"; missing extras should not
    # tank the whole call. A caller who passes ``kinds=("case",)``
    # explicitly is asking for that family and deserves the typed error.
    explicit = kinds is not None

    results: list[Citation] = []

    def _run(kind: str, fn) -> None:  # type: ignore[no-untyped-def]
        if kind not in requested:
            return
        try:
            results.extend(fn(text, source_uri=source_uri))
        except CitationParseError as exc:
            if explicit or kind not in _KIND_TO_EXTRA:
                raise
            logger.info(
                "kaos-citations: skipping %s in default extract — "
                "install kaos-citations[%s] to enable (%s)",
                kind,
                _KIND_TO_EXTRA[kind],
                exc,
            )

    _run("cfr", extract_cfr_citations)
    _run("statute", extract_statute_citations)
    _run("fed_register", extract_federal_register_citations)
    _run("const", extract_constitution_citations)
    _run("fed_rule", extract_federal_rule_citations)
    _run("ussg", extract_ussg_citations)
    _run("treas_reg", extract_treasury_regulation_citations)
    _run("irs_guidance", extract_irs_guidance_citations)
    _run("exec_action", extract_executive_action_citations)
    _run("public_law", extract_public_law_citations)
    _run("legislative", extract_legislative_citations)
    _run("restatement", extract_restatement_citations)
    _run("uniform_act", extract_uniform_act_citations)
    _run("internet", extract_internet_citations)
    _run("archive", extract_archive_citations)
    _run("agency_adj", extract_agency_adjudication_citations)
    _run("agency_manual", extract_agency_manual_citations)
    _run("legal_opinion", extract_legal_opinion_citations)
    _run("bar_ethics", extract_bar_ethics_citations)
    _run("sec_filing", extract_sec_filing_citations)
    _run("sec_release", extract_sec_release_citations)
    _run("sec_staff", extract_sec_staff_citations)
    _run("sec_reg", extract_sec_regulation_citations)
    _run("finra_rule", extract_finra_rule_citations)
    _run("finra_notice", extract_finra_notice_citations)
    _run("finra_disciplinary", extract_finra_disciplinary_citations)
    _run("exchange_rule", extract_exchange_rule_citations)
    _run("fed_reserve_reg", extract_fed_reserve_regulation_citations)
    _run("fed_reserve_letter", extract_fed_reserve_letter_citations)
    _run("fdic_doc", extract_fdic_citations)
    _run("occ_doc", extract_occ_citations)
    _run("cfpb_doc", extract_cfpb_citations)
    _run("ncua_letter", extract_ncua_citations)
    _run("basel", extract_basel_citations)
    _run("cftc_doc", extract_cftc_citations)
    _run("naic", extract_naic_citations)
    _run("intl_finance", extract_international_finance_citations)
    _run("ffiec_call", extract_ffiec_citations)
    _run("asc", extract_asc_citations)
    _run("asu", extract_asu_citations)
    _run("legacy_fasb", extract_legacy_fasb_citations)
    _run("pcaob", extract_pcaob_citations)
    _run("aicpa", extract_aicpa_citations)
    _run("ifrs", extract_ifrs_citations)
    _run("iaasb", extract_iaasb_citations)
    _run("iesba", extract_iesba_citations)
    _run("gasb", extract_gasb_citations)
    _run("fasab", extract_fasab_citations)
    _run("govt_audit", extract_government_audit_citations)
    _run("naic_acct", extract_naic_accounting_citations)
    _run("sustainability", extract_sustainability_citations)
    _run("doi", extract_doi_citations)
    _run("pmid", extract_pubmed_citations)

    # Phase 1A: case-family citations (full + short-form + journal) all
    # share one underlying eyecite pass. ``extract_case_family`` returns
    # the full union; we filter to whatever subset the caller requested.
    case_family_kinds = frozenset({"case", "case_short", "id", "supra", "case_ref", "journal"})
    wanted_case_family = requested_set & case_family_kinds
    if wanted_case_family:
        try:
            family = extract_case_family(text, source_uri=source_uri)
        except CitationParseError as exc:
            if explicit:
                raise
            logger.info(
                "kaos-citations: skipping case-family citations in default extract — "
                "install kaos-citations[%s] to enable (%s)",
                _KIND_TO_EXTRA["case"],
                exc,
            )
        else:
            results.extend(c for c in family if c.kind in wanted_case_family)

    if "arxiv" in requested:
        # Opt-in only; not in default _SUPPORTED_KINDS. Lazy-imported so
        # the parsers/identifiers package isn't pulled into the cold
        # path when arXiv isn't requested.
        from kaos_citations.parsers.identifiers import extract_arxiv_citations

        results.extend(extract_arxiv_citations(text, source_uri=source_uri))

    # Stable ordering: sort by span.start so callers can depend on
    # source-order iteration regardless of which parser produced which hit.
    results.sort(key=lambda c: c.span[0])

    # Phase 1A post-processing: bind Bluebook signals (R1.2), string-cite
    # groups (R1.4), and subsequent-history relations (R10.7) onto the
    # already-extracted citations. Each pass returns a new list because the
    # Citation models are frozen.
    results = apply_postprocess(text, results)
    return results


__all__ = ["extract_citations"]
