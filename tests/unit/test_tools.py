"""Unit tests for the kaos-citations MCP tools.

Exercises each tool's ``execute()`` method against real text. Pure
regex / Aho-Corasick paths — no network calls, no mocks.
"""

from __future__ import annotations

import json

import pytest

from kaos_citations.tools import (
    DoctorTool,
    ExtractCitationsTool,
    ValidateCitationTool,
)

# ---------------------------------------------------------------------------
# ExtractCitationsTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_finds_cfr_citation() -> None:
    tool = ExtractCitationsTool()
    result = await tool.execute({"text": "The court cited 17 CFR 240.10b-5 in its ruling."})
    assert not result.isError
    output = result.require_structured()
    assert output["count"] >= 1
    kinds = [c["kind"] for c in output["citations"]]
    assert "cfr" in kinds


@pytest.mark.asyncio
async def test_extract_with_kinds_filter() -> None:
    tool = ExtractCitationsTool()
    result = await tool.execute({"text": "17 CFR 240.10b-5 and 42 U.S.C. 1983", "kinds": "cfr"})
    assert not result.isError
    kinds = {c["kind"] for c in result.require_structured()["citations"]}
    assert kinds == {"cfr"}


@pytest.mark.asyncio
async def test_extract_with_source_uri() -> None:
    tool = ExtractCitationsTool()
    result = await tool.execute({"text": "17 CFR 240.10b-5", "source_uri": "doc://example/p1"})
    assert not result.isError
    cite = result.require_structured()["citations"][0]
    assert cite["source_uri"] == "doc://example/p1"


@pytest.mark.asyncio
async def test_extract_empty_text_errors() -> None:
    tool = ExtractCitationsTool()
    result = await tool.execute({"text": ""})
    assert result.isError
    assert "Missing" in str(result.content)


@pytest.mark.asyncio
async def test_extract_no_citations_returns_zero() -> None:
    tool = ExtractCitationsTool()
    result = await tool.execute({"text": "No legal citations here."})
    assert not result.isError
    assert result.require_structured()["count"] == 0


@pytest.mark.asyncio
async def test_extract_kind_counts() -> None:
    tool = ExtractCitationsTool()
    result = await tool.execute({"text": "Under 17 CFR 240.10b-5 and 42 U.S.C. § 1983."})
    assert not result.isError
    counts = result.require_structured()["kind_counts"]
    assert counts["cfr"] == 1
    assert counts["statute"] == 1


@pytest.mark.asyncio
async def test_extract_citation_json_round_trips() -> None:
    tool = ExtractCitationsTool()
    result = await tool.execute({"text": "17 CFR 240.10b-5 is the SEC anti-fraud rule."})
    assert not result.isError
    assert result.require_structured()["count"] >= 1
    cite_json = json.dumps(result.require_structured()["citations"][0])
    assert json.loads(cite_json)["kind"] == "cfr"


# ---------------------------------------------------------------------------
# ValidateCitationTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_valid_cfr_citation() -> None:
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "17 CFR 240.10b-5"})
    assert not result.isError
    output = result.require_structured()
    assert output["valid"] is True
    assert output["citation"]["kind"] == "cfr"


@pytest.mark.asyncio
async def test_validate_invalid_string() -> None:
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "this is just plain text"})
    assert not result.isError
    output = result.require_structured()
    assert output["valid"] is False
    assert output["citation"] is None


@pytest.mark.asyncio
async def test_validate_multiple_citations_rejected() -> None:
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "17 CFR 240.10b-5 and 42 U.S.C. § 1983"})
    assert not result.isError
    output = result.require_structured()
    assert output["valid"] is False
    assert output["count"] == 2


@pytest.mark.asyncio
async def test_validate_with_expected_kind_match() -> None:
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "17 CFR 240.10b-5", "expected_kind": "cfr"})
    assert not result.isError
    assert result.require_structured()["valid"] is True


@pytest.mark.asyncio
async def test_validate_with_expected_kind_mismatch() -> None:
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "17 CFR 240.10b-5", "expected_kind": "case"})
    assert not result.isError
    output = result.require_structured()
    assert output["valid"] is False
    assert output["citation"]["kind"] == "cfr"


@pytest.mark.asyncio
async def test_validate_missing_input_errors() -> None:
    tool = ValidateCitationTool()
    result = await tool.execute({})
    assert result.isError


@pytest.mark.asyncio
async def test_validate_unknown_expected_kind_errors_upfront() -> None:
    """Unknown ``expected_kind`` (e.g. typo ``"caselaw"``) must error
    immediately rather than silently always returning ``valid=false``."""
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "17 CFR 240.10b-5", "expected_kind": "caselaw"})
    assert result.isError
    msg = str(result.content)
    assert "caselaw" in msg
    assert "Fix:" in msg


@pytest.mark.asyncio
async def test_validate_unknown_expected_kind_suggests_alternatives() -> None:
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "X v. Y, 1 U.S. 1", "expected_kind": "cas"})
    assert result.isError
    msg = str(result.content)
    # Should suggest at least one near-match (e.g. case / case_short / case_ref)
    assert "case" in msg


@pytest.mark.asyncio
async def test_validate_known_expected_kind_passes_upfront_check() -> None:
    """Sanity: a real kind never trips the upfront-validation guard."""
    tool = ValidateCitationTool()
    result = await tool.execute({"citation": "17 CFR 240.10b-5", "expected_kind": "cfr"})
    assert not result.isError


# ---------------------------------------------------------------------------
# DoctorTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_doctor_reports_punkt_loaded() -> None:
    tool = DoctorTool()
    result = await tool.execute({})
    assert not result.isError
    output = result.require_structured()
    # Punkt legal model has ~27,000 abbreviations.
    assert output["punkt"]["abbreviations"] >= 5_000


@pytest.mark.asyncio
async def test_doctor_reports_vendored_data_counts() -> None:
    tool = DoctorTool()
    result = await tool.execute({})
    output = result.require_structured()
    vd = output["vendored_data"]
    assert vd["reporter_canonical"] >= 1_200
    assert vd["court_citation_strings"] >= 1_000
    assert vd["case_name_abbreviations"] >= 100
    assert vd["state_abbreviations"] == 50


@pytest.mark.asyncio
async def test_doctor_lists_supported_kinds() -> None:
    tool = DoctorTool()
    result = await tool.execute({})
    output = result.require_structured()
    kinds = output["supported_kinds"]
    # Spot-check a few across families.
    for k in ("case", "cfr", "statute", "asc", "ifrs", "sec_filing", "doi"):
        assert k in kinds, f"{k!r} missing from supported_kinds"


# ---------------------------------------------------------------------------
# Tool metadata invariants
# ---------------------------------------------------------------------------


class TestToolMetadata:
    def test_module_versions_match_package(self) -> None:
        """All tools report the same version as the wheel."""
        from kaos_citations._version import __version__

        for cls in (ExtractCitationsTool, ValidateCitationTool, DoctorTool):
            tool = cls()
            assert tool.metadata.version == __version__, (
                f"{cls.__name__}.metadata.version != {__version__}"
            )

    def test_all_tools_are_read_only(self) -> None:
        """No kaos-citations tool mutates state or hits the network."""
        for cls in (ExtractCitationsTool, ValidateCitationTool, DoctorTool):
            tool = cls()
            ann = tool.metadata.annotations
            assert ann is not None
            assert ann.readOnlyHint is True
            assert ann.openWorldHint is False
