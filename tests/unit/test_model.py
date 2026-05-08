"""Unit tests for the discriminated-union :class:`Citation` model."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from kaos_citations.model import CaseCitation, CFRCitation, Citation


def _make_cfr(
    *,
    raw: str = "17 CFR 240.10b-5",
    normalized: str = "17 CFR 240.10b-5",
    span: tuple[int, int] = (0, 16),
    title: int = 17,
    section: str = "240.10b-5",
) -> CFRCitation:
    return CFRCitation(
        raw=raw,
        normalized=normalized,
        span=span,
        title=title,
        section=section,
    )


@pytest.mark.unit
class TestCitationBase:
    def test_cfr_frozen(self) -> None:
        cit = _make_cfr()
        with pytest.raises(ValidationError):
            cit.raw = "other"  # type: ignore[misc]

    def test_kind_is_locked_to_literal(self) -> None:
        with pytest.raises(ValidationError):
            CFRCitation(
                kind="case",  # ty: ignore[invalid-argument-type]
                raw="17 CFR 240.10b-5",
                normalized="17 CFR 240.10b-5",
                span=(0, 16),
                title=17,
                section="240.10b-5",
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CFRCitation(
                raw="17 CFR 240.10b-5",
                normalized="17 CFR 240.10b-5",
                span=(0, 16),
                title=17,
                section="240.10b-5",
                extra_junk="nope",  # ty: ignore[unknown-argument]
            )

    def test_title_range_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _make_cfr(title=99)


@pytest.mark.unit
class TestDiscriminatedUnion:
    """Pydantic v2 must select the right subclass from the ``kind`` tag."""

    def test_cfr_round_trips_through_union(self) -> None:
        adapter = TypeAdapter(Citation)
        payload = {
            "kind": "cfr",
            "raw": "17 CFR 240.10b-5",
            "normalized": "17 CFR 240.10b-5",
            "span": [0, 16],
            "title": 17,
            "section": "240.10b-5",
        }
        parsed = adapter.validate_python(payload)
        assert isinstance(parsed, CFRCitation)
        assert parsed.title == 17
        # Round-trip via dump.
        dumped = adapter.dump_python(parsed)
        reparsed = adapter.validate_python(dumped)
        assert reparsed == parsed

    def test_case_selected_by_discriminator(self) -> None:
        """Even though the case parser is deferred, the union must route
        ``kind=case`` payloads to CaseCitation."""
        adapter = TypeAdapter(Citation)
        payload = {
            "kind": "case",
            "raw": "Miranda v. Arizona, 384 U.S. 436 (1966)",
            "normalized": "384 U.S. 436",
            "span": [0, 40],
            "volume": 384,
            "reporter": "U.S.",
            "page": 436,
            "year": 1966,
        }
        parsed = adapter.validate_python(payload)
        assert isinstance(parsed, CaseCitation)
        assert parsed.volume == 384

    def test_unknown_kind_rejected(self) -> None:
        adapter = TypeAdapter(Citation)
        with pytest.raises(ValidationError):
            adapter.validate_python(
                {
                    "kind": "does-not-exist",
                    "raw": "x",
                    "normalized": "x",
                    "span": [0, 1],
                }
            )
