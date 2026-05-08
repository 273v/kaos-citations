"""Unit tests for the kaos-citations MCP resource surface."""

from __future__ import annotations

import pytest

from kaos_citations.extract import _OPT_IN_KINDS as _DISPATCHER_OPT_IN
from kaos_citations.extract import _SUPPORTED_KINDS as _DISPATCHER_SUPPORTED
from kaos_citations.resources import (
    CITATION_KINDS_URI,
    CitationKindsResource,
    register_citations_resources,
)


@pytest.mark.unit
class TestCitationKindsResource:
    @pytest.mark.asyncio
    async def test_read_returns_static_taxonomy(self) -> None:
        resource = CitationKindsResource()
        data = await resource.read()
        assert data["count"] == len(data["kinds"])
        assert data["families"] == ["legal", "financial", "accounting", "identifier"]
        assert data["opt_in_kinds"] == ["arxiv"]

    @pytest.mark.asyncio
    async def test_arxiv_flagged_opt_in(self) -> None:
        data = await CitationKindsResource().read()
        arxiv = next(k for k in data["kinds"] if k["kind"] == "arxiv")
        assert arxiv["opt_in"] is True
        assert arxiv["family"] == "identifier"

    @pytest.mark.asyncio
    async def test_metadata_advertises_global_cache(self) -> None:
        resource = CitationKindsResource()
        # Static taxonomy — context-independent.
        assert resource.cache_scope == "global"
        meta = resource.metadata
        assert meta.uri == CITATION_KINDS_URI
        assert meta.mime_type == "application/json"
        assert meta.provider_module == "kaos-citations"

    @pytest.mark.asyncio
    async def test_table_covers_every_dispatcher_kind(self) -> None:
        """The resource taxonomy must list every kind the dispatcher
        accepts in ``kinds=`` filters. Drift between the dispatcher's
        ``_SUPPORTED_KINDS`` / ``_OPT_IN_KINDS`` and the resource table
        means agents can't trust the resource for self-discovery."""
        data = await CitationKindsResource().read()
        resource_kinds = {k["kind"] for k in data["kinds"]}
        dispatcher_kinds = set(_DISPATCHER_SUPPORTED) | set(_DISPATCHER_OPT_IN)
        missing = dispatcher_kinds - resource_kinds
        extra = resource_kinds - dispatcher_kinds
        assert not missing, f"resource taxonomy missing kinds: {sorted(missing)}"
        assert not extra, f"resource taxonomy lists kinds the dispatcher rejects: {sorted(extra)}"


@pytest.mark.unit
class TestResourceRegistration:
    @pytest.mark.asyncio
    async def test_register_then_read_via_runtime(self) -> None:
        from kaos_core import KaosRuntime

        runtime = KaosRuntime.default()
        n = register_citations_resources(runtime)
        assert n == 1
        data = await runtime.resources.get_resource(CITATION_KINDS_URI)
        assert "kinds" in data
        assert data["count"] > 50
