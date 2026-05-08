"""MCP tools for kaos-citations.

Three tools expose the structured-extraction surface to agents:

1. ``kaos-citations-extract`` — extract every citation from a passage of text
2. ``kaos-citations-validate`` — parse a single citation string into a typed
   record (or report ``None`` if the input doesn't parse)
3. ``kaos-citations-doctor`` — diagnostic: confirm the bundled Punkt model
   loaded, report supported citation kinds, and report vendored-data counts

All three follow the kaos-core ``KaosTool`` pattern: frozen metadata +
async ``execute()`` → ``ToolResult``. None make network calls — citation
extraction is fully offline.
"""

from __future__ import annotations

from typing import Any

from kaos_core import KaosRuntime, KaosTool, ToolMetadata, ToolResult
from kaos_core.logging import get_logger
from kaos_core.types.annotations import ToolAnnotations
from kaos_core.types.enums import ToolCapability, ToolCategory
from kaos_core.types.parameters import ParameterSchema

from kaos_citations._version import __version__ as _MODULE_VERSION

logger = get_logger(__name__)

_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


# ---------------------------------------------------------------------------
# Extract — main bulk-extraction surface
# ---------------------------------------------------------------------------


class ExtractCitationsTool(KaosTool):
    """Extract every legal / financial / accounting citation from text."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="kaos-citations-extract",
            display_name="Extract Citations",
            description=(
                "Identify and extract every typed citation from a passage "
                "of text. Recognises 60 citation kinds including federal + state "
                "case law, U.S. Code, CFR, Federal Register, U.S. "
                "Constitution, Federal Rules + USSG, IRS guidance, "
                "executive actions, public laws + bills + reports + Cong. "
                "Rec., Restatements, Uniform Acts, agency adjudications + "
                "manuals, AG/OLC opinions, bar ethics, SEC filings + "
                "releases + staff guidance + named regulations, FINRA, "
                "exchange rules, banking, Basel, CFTC, NAIC, FFIEC, FASB "
                "ASC + ASU + legacy, PCAOB, AICPA, IFRS family, IAASB, "
                "IESBA, GASB, FASAB, government audit, sustainability "
                "frameworks, DOI, arXiv, PubMed, internet URLs, archives. "
                "Returns frozen Pydantic-typed citation objects with span, "
                "normalized form, and family-specific structured fields. "
                "Fully offline (no network); deterministic."
            ),
            category=ToolCategory.TEXT,
            capability=ToolCapability.EXTRACT,
            module_name="kaos-citations",
            version=_MODULE_VERSION,
            annotations=_READ_ONLY,
            input_schema=[
                ParameterSchema(
                    name="text",
                    type="string",
                    description="Text to extract citations from.",
                    required=True,
                ),
                ParameterSchema(
                    name="kinds",
                    type="string",
                    description=(
                        "Optional comma-separated subset of citation kinds "
                        "to extract (e.g. ``case,statute``). When omitted, "
                        "every supported kind is attempted. Use the "
                        "``kaos-citations-doctor`` tool for the full list."
                    ),
                    required=False,
                ),
                ParameterSchema(
                    name="source_uri",
                    type="string",
                    description=(
                        "Optional source URI threaded onto every returned "
                        "citation's ``source_uri`` field — for downstream "
                        "consumers that need to round-trip back to the "
                        "originating document."
                    ),
                    required=False,
                ),
            ],
        )

    async def execute(self, inputs: dict[str, Any], context: Any | None = None) -> ToolResult:
        text = inputs.get("text", "")
        if not text:
            return ToolResult.create_error(
                "Missing 'text' parameter. Fix: provide the text to extract "
                "citations from. Alternative: use kaos-source-discover or "
                "kaos-pdf-parse to surface document text first, then pipe "
                "the result here."
            )

        kinds_str = inputs.get("kinds")
        kinds = [k.strip() for k in kinds_str.split(",")] if kinds_str else None
        source_uri = inputs.get("source_uri")

        from kaos_citations import extract_citations
        from kaos_citations.errors import CitationParseError

        try:
            citations = extract_citations(text, kinds=kinds, source_uri=source_uri)
        except CitationParseError as exc:
            return ToolResult.create_error(
                f"Citation extraction failed: {exc}. "
                "Fix: drop the offending kind from ``kinds=`` or omit it "
                "entirely to use the default supported set. "
                "Alternative: call ``kaos-citations-doctor`` to see the "
                "full list of supported kinds."
            )

        results = [c.model_dump(mode="json") for c in citations]
        kind_counts: dict[str, int] = {}
        for c in citations:
            kind_counts[c.kind] = kind_counts.get(c.kind, 0) + 1

        return ToolResult.create_success(
            output={
                "citations": results,
                "count": len(results),
                "kind_counts": kind_counts,
            },
            summary=(f"Extracted {len(results)} citation(s) across {len(kind_counts)} kind(s)."),
        )


# ---------------------------------------------------------------------------
# Validate — single-citation parser
# ---------------------------------------------------------------------------


class ValidateCitationTool(KaosTool):
    """Parse a single citation string into a typed record."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="kaos-citations-validate",
            display_name="Validate Citation",
            description=(
                "Parse a single citation string (or short passage) and "
                "return the typed-record breakdown if exactly one citation "
                "is recognised. Returns ``valid=false`` when the input "
                "doesn't parse, or ``valid=false`` with a count when the "
                "input contains multiple citations (use "
                "``kaos-citations-extract`` for bulk passages). Useful for "
                "agents that want to confirm \"is 'Brown v. Bd. of Educ., "
                "347 U.S. 483 (1954)' a valid citation?\" without writing "
                "their own slicing logic. Fully offline; deterministic."
            ),
            category=ToolCategory.TEXT,
            capability=ToolCapability.EXTRACT,
            module_name="kaos-citations",
            version=_MODULE_VERSION,
            annotations=_READ_ONLY,
            input_schema=[
                ParameterSchema(
                    name="citation",
                    type="string",
                    description="A single citation string to validate.",
                    required=True,
                ),
                ParameterSchema(
                    name="expected_kind",
                    type="string",
                    description=(
                        "Optional — when set, the returned citation must "
                        "match this kind (e.g. ``case``, ``statute``, "
                        "``cfr``); otherwise ``valid`` is ``false``."
                    ),
                    required=False,
                ),
            ],
        )

    async def execute(self, inputs: dict[str, Any], context: Any | None = None) -> ToolResult:
        citation_str = inputs.get("citation", "")
        if not citation_str:
            return ToolResult.create_error(
                "Missing 'citation' parameter. Fix: provide a single "
                "citation string (e.g. ``'347 U.S. 483'``)."
            )

        expected_kind = inputs.get("expected_kind")

        from kaos_citations import extract_citations
        from kaos_citations.extract import _OPT_IN_KINDS, _SUPPORTED_KINDS

        if expected_kind is not None:
            valid_kinds = set(_SUPPORTED_KINDS) | set(_OPT_IN_KINDS)
            if expected_kind not in valid_kinds:
                # Suggest a near-match if there's an obvious typo
                # (Levenshtein-1 / prefix overlap). Cheap, no external dep.
                suggestions = [
                    k
                    for k in sorted(valid_kinds)
                    if k.startswith(expected_kind[:3]) or expected_kind.startswith(k[:3])
                ][:5]
                hint = f" Did you mean one of: {suggestions!r}?" if suggestions else ""
                return ToolResult.create_error(
                    f"Unknown expected_kind={expected_kind!r}.{hint} "
                    "Fix: pass a kind from the kaos-citations://kinds resource, "
                    "or call kaos-citations-doctor for the full supported list."
                )

        cites = extract_citations(citation_str)

        if len(cites) == 0:
            return ToolResult.create_success(
                output={
                    "valid": False,
                    "reason": "No citation recognised in the input string.",
                    "citation": None,
                },
                summary="Not a valid citation.",
            )

        if len(cites) > 1:
            return ToolResult.create_success(
                output={
                    "valid": False,
                    "reason": (
                        f"Input contains {len(cites)} citations; "
                        "use ``kaos-citations-extract`` for bulk passages."
                    ),
                    "count": len(cites),
                    "citation": None,
                },
                summary=f"Input contains {len(cites)} citations, not one.",
            )

        c = cites[0]
        if expected_kind and c.kind != expected_kind:
            return ToolResult.create_success(
                output={
                    "valid": False,
                    "reason": (f"Citation parsed as kind={c.kind!r}; expected {expected_kind!r}."),
                    "citation": c.model_dump(mode="json"),
                },
                summary=f"Wrong kind: parsed as {c.kind}, expected {expected_kind}.",
            )

        return ToolResult.create_success(
            output={
                "valid": True,
                "citation": c.model_dump(mode="json"),
            },
            summary=f"Valid {c.kind} citation: {c.normalized}.",
        )


# ---------------------------------------------------------------------------
# Doctor — diagnostic
# ---------------------------------------------------------------------------


class DoctorTool(KaosTool):
    """Diagnostic: confirm the bundled Punkt model + vendored data loaded."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="kaos-citations-doctor",
            display_name="kaos-citations Doctor",
            description=(
                "Diagnostic tool. Verifies the bundled kaos-nlp-core Punkt "
                "sentence model is loaded with the legal abbreviation set, "
                "reports the vendored reporters_db / courts_db data counts, "
                "and lists every supported citation kind. Use this to "
                "confirm a fresh install is functional, or for agent "
                'self-discovery ("what kinds can this tool extract?"). '
                "Fully offline; deterministic."
            ),
            category=ToolCategory.TEXT,
            capability=ToolCapability.EXTRACT,
            module_name="kaos-citations",
            version=_MODULE_VERSION,
            annotations=_READ_ONLY,
            input_schema=[],
        )

    async def execute(self, inputs: dict[str, Any], context: Any | None = None) -> ToolResult:
        from kaos_citations._nlp import PunktModelMissingError, verify_punkt_model
        from kaos_citations.data._loaders import (
            case_name_abbreviation_tokens,
            court_citation_strings,
            journal_abbreviation_set,
            law_reporter_set,
            reporter_all_spellings,
            reporter_canonical_set,
            state_abbreviation_set,
        )
        from kaos_citations.extract import _SUPPORTED_KINDS

        try:
            punkt = verify_punkt_model()
        except PunktModelMissingError as exc:
            return ToolResult.create_error(
                f"Punkt model failed to load: {exc}. "
                "Fix: reinstall kaos-nlp-core from a published wheel."
            )

        output = {
            "version": _MODULE_VERSION,
            "punkt": punkt,
            "vendored_data": {
                "reporter_canonical": len(reporter_canonical_set()),
                "reporter_all_spellings": len(reporter_all_spellings()),
                "case_name_abbreviations": len(case_name_abbreviation_tokens()),
                "state_abbreviations": len(state_abbreviation_set()),
                "law_reporters": len(law_reporter_set()),
                "journal_abbreviations": len(journal_abbreviation_set()),
                "court_citation_strings": len(court_citation_strings()),
            },
            "supported_kinds": list(_SUPPORTED_KINDS),
        }

        return ToolResult.create_success(
            output=output,
            summary=(
                f"kaos-citations {_MODULE_VERSION} ready. "
                f"Punkt: {punkt['abbreviations']} abbrevs. "
                f"Supports {len(_SUPPORTED_KINDS)} citation kinds."
            ),
        )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_citations_tools(runtime: KaosRuntime) -> int:
    """Register every kaos-citations tool with ``runtime``.

    Returns the number of tools registered. Idempotent — safe to call
    multiple times."""
    tools: list[KaosTool] = [
        ExtractCitationsTool(),
        ValidateCitationTool(),
        DoctorTool(),
    ]
    for tool in tools:
        runtime.tools.register_tool(tool)
    return len(tools)


__all__ = [
    "DoctorTool",
    "ExtractCitationsTool",
    "ValidateCitationTool",
    "register_citations_tools",
]
