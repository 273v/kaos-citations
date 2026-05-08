"""MCP resource surface for kaos-citations.

A single resource — ``kaos-citations://kinds`` — lets agents discover
the supported citation taxonomy without invoking a tool. Cheaper than
calling ``kaos-citations-doctor`` and structured: one entry per
``kind`` with the human-readable description, the broader family
(``legal`` / ``financial`` / ``accounting`` / ``identifier``), a
canonical Bluebook-style example, and whether the kind is opt-in.

The resource is fully static / context-independent, so it advertises
``cache_scope = "global"``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from kaos_core import KaosContext, KaosResource, KaosRuntime, ResourceMetadata
from kaos_core.types.enums import ResourceType

from kaos_citations._version import __version__ as _MODULE_VERSION

CITATION_KINDS_URI = "kaos-citations://kinds"


# Curated `kind` → metadata table. Mirrors the README "Citation kinds"
# table; agents read it to learn what to pass in ``kinds=`` filters.
# When adding a new family, update this table AND the README at the
# same time — they're documented together.
_KINDS_TABLE: tuple[tuple[str, str, str, str], ...] = (
    # (kind, family, example, description)
    ("case", "legal", "Brown v. Bd. of Educ., 347 U.S. 483 (1954)", "Full-form case citation."),
    ("case_short", "legal", "Brown, 347 U.S. at 495", "Bluebook R10.9 short-form case cite."),
    ("id", "legal", "Id. at 495", "Bluebook R4.1 ``Id.`` short-form."),
    ("supra", "legal", "Smith, supra note 12, at 45", "Bluebook R4.2 ``supra`` short-form."),
    ("case_ref", "legal", "Roe at 240", "Reference by case name only (R10.9)."),
    ("journal", "legal", "94 Yale L.J. 247 (1985)", "Law-review / journal article (R16)."),
    ("cfr", "legal", "17 C.F.R. § 240.10b-5", "Code of Federal Regulations."),
    ("statute", "legal", "42 U.S.C. § 1983", "U.S. Code / state codes / I.R.C."),
    ("fed_register", "legal", "88 Fed. Reg. 12,345 (Mar. 1, 2023)", "Federal Register notice."),
    ("const", "legal", "U.S. Const. amend. I", "U.S. or state constitution (R11)."),
    (
        "fed_rule",
        "legal",
        "Fed. R. Civ. P. 56(c)",
        "Federal Rules — FRCP / FRCrP / FRE / FRAP / FRBP.",
    ),
    ("ussg", "legal", "U.S.S.G. § 2D1.1(a)(1)", "U.S. Sentencing Guidelines."),
    ("treas_reg", "legal", "Treas. Reg. § 1.501(c)(3)-1", "Treasury Regulation (R14.5.1)."),
    (
        "irs_guidance",
        "legal",
        "Rev. Rul. 78-189",
        "IRS guidance — Rev. Rul., Rev. Proc., Notice, PLR, TAM, T.D., etc.",
    ),
    (
        "exec_action",
        "legal",
        "Exec. Order No. 13,769",
        "Executive Order, Proclamation, Memorandum, Determination.",
    ),
    (
        "public_law",
        "legal",
        "Pub. L. No. 111-148, 124 Stat. 119",
        "Public Law / Statutes at Large (R12.4).",
    ),
    ("legislative", "legal", "H.R. 3590, 111th Cong. (2009)", "Bills, reports, Cong. Rec."),
    ("restatement", "legal", "Restatement (Second) of Torts § 402A (1965)", "Restatement of Law."),
    ("uniform_act", "legal", "U.C.C. § 2-207", "Uniform Acts and Model Codes."),
    (
        "agency_adj",
        "legal",
        "In re Boeing Co., 369 N.L.R.B. No. 8 (2020)",
        "Agency adjudication — NLRB / FERC / FCC / FTC / NTSB / EPA EAB / BIA / PTAB / TTAB.",
    ),
    ("agency_manual", "legal", "MPEP § 2106", "Agency manual — MPEP / TMEP / POMS."),
    ("legal_opinion", "legal", "42 Op. O.L.C. 1 (2018)", "AG / OLC / state AG opinion."),
    (
        "bar_ethics",
        "legal",
        "ABA Comm. on Ethics, Formal Op. 477 (2017)",
        "Bar ethics opinion (ABA + state).",
    ),
    ("internet", "legal", "https://example.com/page", "Generic internet URL."),
    ("archive", "legal", "https://web.archive.org/web/.../...", "Wayback / Perma archive URL."),
    ("sec_filing", "financial", "Form 10-K, Apple Inc. (2023)", "SEC filing (20+ form types)."),
    (
        "sec_release",
        "financial",
        "Securities Act Release No. 33-11070",
        "SEC release — 33-/34-/IC-/IA-/TIA-.",
    ),
    (
        "sec_staff",
        "financial",
        "Staff Accounting Bulletin No. 121",
        "SEC staff guidance — SAB / SLB / C&DI / no-action.",
    ),
    (
        "sec_reg",
        "financial",
        "Reg. S-X",
        "SEC named regulation — Reg. S-X / S-K / G / AB / M / FD / BTR / S-T.",
    ),
    ("finra_rule", "financial", "FINRA Rule 2010", "FINRA rule."),
    (
        "finra_notice",
        "financial",
        "FINRA Reg. Notice 22-08",
        "FINRA Regulatory / Information Notice.",
    ),
    (
        "finra_disciplinary",
        "financial",
        "FINRA Discip. Proc. 2018058950501",
        "FINRA disciplinary proceeding.",
    ),
    (
        "exchange_rule",
        "financial",
        "NYSE Rule 123",
        "Exchange rule — NYSE / Nasdaq / Cboe / MSRB / OCC.",
    ),
    ("fed_reserve_reg", "financial", "Reg. T", "Federal Reserve regulation."),
    ("fed_reserve_letter", "financial", "SR Letter 22-3", "Fed Reserve SR / CA / OP letter."),
    ("fdic_doc", "financial", "FDIC FIL-22-2022", "FDIC Financial Institution Letter."),
    (
        "occ_doc",
        "financial",
        "OCC Bull. 2020-26",
        "OCC bulletin / interpretive letter / conditional approval.",
    ),
    ("cfpb_doc", "financial", "CFPB Bull. 2022-04", "CFPB bulletin / circular / advisory opinion."),
    ("ncua_letter", "financial", "NCUA Letter 22-CU-04", "NCUA letter to credit unions."),
    ("basel", "financial", "Basel III Framework, BCBS 189", "Basel framework document."),
    (
        "cftc_doc",
        "financial",
        "CFTC Letter No. 22-04",
        "CFTC interpretive / no-action / advisory / order.",
    ),
    ("naic", "financial", "NAIC Model Bull. 2023-1", "NAIC bulletin / model act."),
    (
        "intl_finance",
        "financial",
        "FATF Recommendation 10",
        "International finance bodies (FATF / IOSCO).",
    ),
    ("ffiec_call", "financial", "FFIEC Call Report Schedule RC-R", "FFIEC call-report reference."),
    ("asc", "accounting", "ASC 606-10-25-2", "FASB Accounting Standards Codification."),
    ("asu", "accounting", "ASU 2016-13", "FASB Accounting Standards Update."),
    (
        "legacy_fasb",
        "accounting",
        "FAS 109",
        "Legacy FASB statements — FAS / FIN / FSP / EITF / TB / CON / APB / ARB.",
    ),
    ("pcaob", "accounting", "PCAOB AS 2410", "PCAOB AS / Releases / Rules / Practice Alerts."),
    ("aicpa", "accounting", "AICPA SAS 145", "AICPA — SAS / SSAE / SSARS / SOP / TQA / Code."),
    (
        "ifrs",
        "accounting",
        "IFRS 15",
        "IFRS family — IFRS / IAS / IFRIC / SIC / Practice Statement / Conceptual Framework.",
    ),
    (
        "iaasb",
        "accounting",
        "ISA 315 (Revised 2019)",
        "IAASB — ISA / ISAE / ISRE / ISRS / ISQM / ISQC.",
    ),
    ("iesba", "accounting", "IESBA Code § 110.1", "IESBA Code of Ethics."),
    (
        "gasb",
        "accounting",
        "GASB Statement No. 87",
        "GASB Statements / Implementation Guides / Concepts / Tech Bulletins / Interpretations.",
    ),
    (
        "fasab",
        "accounting",
        "SFFAS 6",
        "FASAB SFFAS / Concepts / Interpretations / Tech Bulletins.",
    ),
    (
        "govt_audit",
        "accounting",
        "OMB Circular A-133",
        "Government audit — OMB Circulars / Memos / GAO Reports / Yellow Book.",
    ),
    ("naic_acct", "accounting", "NAIC SSAP No. 62R", "NAIC Statutory Accounting Principles."),
    (
        "sustainability",
        "accounting",
        "GRI 305",
        "Sustainability frameworks — GRI / SASB / TCFD / ISSB / ESRS.",
    ),
    ("doi", "identifier", "10.1038/nature12373", "Digital Object Identifier."),
    ("pmid", "identifier", "PMID: 24571878", "PubMed identifier."),
    ("arxiv", "identifier", "arXiv:2305.10403", "arXiv preprint identifier (opt-in by default)."),
)


_OPT_IN_KINDS: frozenset[str] = frozenset({"arxiv"})


class CitationKindsResource(KaosResource):
    """Static taxonomy resource — agents call ``read()`` to discover
    what citation ``kind`` literals the extractor accepts.

    Cache scope is ``global`` because the table is fully static and
    context-independent.
    """

    cache_scope: ClassVar[str] = "global"

    @property
    def metadata(self) -> ResourceMetadata:
        return ResourceMetadata(
            uri=CITATION_KINDS_URI,
            name="kaos-citations supported kinds",
            description=(
                "Taxonomy of every citation ``kind`` the extractor accepts. "
                "Each entry carries the broader family (``legal`` / "
                "``financial`` / ``accounting`` / ``identifier``), a "
                "canonical Bluebook-style example, and a one-line "
                "description. Use this to populate the ``kinds=`` filter "
                "of ``kaos-citations-extract`` without trial-and-error."
            ),
            resource_type=ResourceType.CONFIGURATION,
            mime_type="application/json",
            provider_module="kaos-citations",
            version=_MODULE_VERSION,
            tags=["kaos-citations", "taxonomy", "kinds"],
        )

    async def read(self, context: KaosContext | None = None) -> dict[str, Any]:
        del context  # static taxonomy — no per-context behaviour
        kinds: list[dict[str, Any]] = []
        for kind, family, example, description in _KINDS_TABLE:
            kinds.append(
                {
                    "kind": kind,
                    "family": family,
                    "example": example,
                    "description": description,
                    "opt_in": kind in _OPT_IN_KINDS,
                }
            )
        return {
            "version": _MODULE_VERSION,
            "count": len(kinds),
            "families": ["legal", "financial", "accounting", "identifier"],
            "opt_in_kinds": sorted(_OPT_IN_KINDS),
            "kinds": kinds,
        }

    async def get_metadata(self, context: KaosContext | None = None) -> dict[str, Any]:
        del context
        return {
            "count": len(_KINDS_TABLE),
            "static": True,
            "opt_in_kinds": sorted(_OPT_IN_KINDS),
        }


def register_citations_resources(runtime: KaosRuntime) -> int:
    """Register every kaos-citations MCP resource with ``runtime``.

    Returns the number of resources registered. Idempotent at the
    function-call level — re-registering an already-known URI raises
    ``RegistryError``, so callers should not call this twice on the
    same runtime."""
    runtime.resources.register_resource(CitationKindsResource())
    return 1


__all__ = [
    "CITATION_KINDS_URI",
    "CitationKindsResource",
    "register_citations_resources",
]
