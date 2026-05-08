"""Per-family citation parsers.

- PR 1: CFR.
- PR 2: case law + statutes (eyecite adapter).
- WS-2.5 (this PR):
  - Federal Register routing (separates Fed Reg from generic Statute
    in the eyecite ``FullLawCitation`` family).
  - US Constitution regex parser (eyecite doesn't recognize
    ``U.S. Const.``).
  - Identifier parsers — DOI (legal scholarship + law-review footnotes)
    and PMID (medical malpractice / pharma cases). The arXiv parser is
    included for identifier-format coverage but is NOT wired into the
    default ``extract_citations`` dispatcher because lawyers rarely
    cite preprints.
"""

from __future__ import annotations

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
from kaos_citations.parsers.case import (
    extract_case_citations,
    extract_case_family,
    extract_case_short_forms,
    extract_journal_citations,
)
from kaos_citations.parsers.cfr import extract_cfr_citations, iter_cfr_matches
from kaos_citations.parsers.constitution import (
    extract_constitution_citations,
    iter_constitution_matches,
)
from kaos_citations.parsers.federal_rules import (
    extract_federal_rule_citations,
    extract_ussg_citations,
    iter_federal_rule_matches,
    iter_ussg_matches,
)
from kaos_citations.parsers.identifiers import (
    extract_arxiv_citations,
    extract_doi_citations,
    extract_pubmed_citations,
    iter_arxiv_matches,
    iter_doi_matches,
    iter_pubmed_matches,
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
    extract_law_citations,
    extract_statute_citations,
)

__all__ = [
    # Phase 2 — agency / opinions
    "extract_agency_adjudication_citations",
    "extract_agency_manual_citations",
    "extract_aicpa_citations",
    "extract_archive_citations",
    "extract_arxiv_citations",
    "extract_asc_citations",
    "extract_asu_citations",
    # Phase 3 — financial
    "extract_bar_ethics_citations",
    "extract_basel_citations",
    "extract_case_citations",
    "extract_case_family",
    "extract_case_short_forms",
    "extract_cfpb_citations",
    "extract_cfr_citations",
    "extract_cftc_citations",
    "extract_constitution_citations",
    "extract_doi_citations",
    "extract_exchange_rule_citations",
    "extract_executive_action_citations",
    "extract_fasab_citations",
    "extract_fdic_citations",
    "extract_fed_reserve_letter_citations",
    "extract_fed_reserve_regulation_citations",
    "extract_federal_register_citations",
    "extract_federal_rule_citations",
    "extract_ffiec_citations",
    "extract_finra_disciplinary_citations",
    "extract_finra_notice_citations",
    "extract_finra_rule_citations",
    "extract_gasb_citations",
    # Phase 4 — accounting
    "extract_government_audit_citations",
    "extract_iaasb_citations",
    "extract_iesba_citations",
    "extract_ifrs_citations",
    "extract_international_finance_citations",
    "extract_internet_citations",
    "extract_irs_guidance_citations",
    "extract_journal_citations",
    "extract_law_citations",
    "extract_legacy_fasb_citations",
    "extract_legal_opinion_citations",
    "extract_legislative_citations",
    "extract_naic_accounting_citations",
    "extract_naic_citations",
    "extract_ncua_citations",
    "extract_occ_citations",
    "extract_pcaob_citations",
    "extract_public_law_citations",
    "extract_pubmed_citations",
    "extract_restatement_citations",
    "extract_sec_filing_citations",
    "extract_sec_regulation_citations",
    "extract_sec_release_citations",
    "extract_sec_staff_citations",
    "extract_statute_citations",
    "extract_sustainability_citations",
    "extract_treasury_regulation_citations",
    "extract_uniform_act_citations",
    "extract_ussg_citations",
    "iter_arxiv_matches",
    "iter_cfr_matches",
    "iter_constitution_matches",
    "iter_doi_matches",
    "iter_federal_rule_matches",
    "iter_pubmed_matches",
    "iter_ussg_matches",
]
