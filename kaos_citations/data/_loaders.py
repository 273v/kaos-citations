"""Typed loaders for vendored reporters_db / courts_db JSON.

All loaders are cached via ``functools.lru_cache`` so the JSON is
parsed exactly once per process. Resource resolution uses
``importlib.resources.files()`` for wheel-safe path lookup — the
data files are force-included in the wheel via the
``[tool.hatch.build.targets.wheel.force-include]`` section in
``pyproject.toml``.

Returned data structures are deliberately *plain* — frozen dataclasses
rather than pydantic models — to keep the import surface small. The
matchers / parsers consume these via FstSet / iteration and don't need
field validation at construction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

# The vendored data directory inside the package.
_DATA_PKG = "kaos_citations.data"


def _load_json(filename: str) -> Any:
    """Load a JSON file from the vendored ``kaos_citations.data``
    package via importlib.resources."""
    with resources.files(_DATA_PKG).joinpath(filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Reporters
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReporterEdition:
    """One historical edition of a reporter abbreviation.

    A single canonical abbreviation (e.g. ``U.S.``) can correspond to
    multiple editions over time (early Wallace / Cranch nominate
    reporters → modern U.S. Reports). Each edition has its own
    start/end date and matching patterns.
    """

    edition_key: str  # The dictionary key under "editions" — usually the abbrev itself
    start_date: str | None  # ISO 8601, e.g. "1875-01-01T00:00:00"
    end_date: str | None
    regexes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReporterEntry:
    """A vendored reporters_db entry for one abbreviation.

    The same abbreviation can appear with different ``cite_type`` values
    across history — e.g. ``Wall.`` is both a SCOTUS early-nominative
    reporter and used elsewhere. We keep the full list rather than
    collapsing.
    """

    abbreviation: str  # e.g. "U.S." (the dict key in reporters.json)
    # cite_type values: "federal" / "state" / "state_regional" / "neutral"
    # / "specialty" / "specialty_lexis" / "specialty_west" / "scotus_early"
    cite_type: str
    name: str  # "United States Supreme Court Reports"
    editions: tuple[ReporterEdition, ...]
    variations: tuple[tuple[str, str], ...]  # ((variant, canonical), ...) — alternative spellings
    mlz_jurisdiction: tuple[str, ...]
    notes: str = ""


def _parse_reporter_entry(abbreviation: str, raw: dict[str, Any]) -> ReporterEntry:
    editions: list[ReporterEdition] = []
    for ed_key, ed_val in (raw.get("editions") or {}).items():
        editions.append(
            ReporterEdition(
                edition_key=ed_key,
                start_date=ed_val.get("start"),
                end_date=ed_val.get("end"),
                regexes=tuple(ed_val.get("regexes") or ()),
            )
        )
    variations = tuple((k, v) for k, v in (raw.get("variations") or {}).items())
    jurisdictions = tuple(raw.get("mlz_jurisdiction") or ())
    return ReporterEntry(
        abbreviation=abbreviation,
        cite_type=raw.get("cite_type", ""),
        name=raw.get("name", ""),
        editions=tuple(editions),
        variations=variations,
        mlz_jurisdiction=jurisdictions,
        notes=raw.get("notes", ""),
    )


@lru_cache(maxsize=1)
def load_reporters() -> dict[str, tuple[ReporterEntry, ...]]:
    """Return the reporters_db.

    Keys are canonical abbreviations (``U.S.``, ``F.3d``, ``S. Ct.``,
    ``L. Ed. 2d``, ...). Values are tuples of one-or-more
    :class:`ReporterEntry` (multiple when the same abbreviation has
    different historical editions).

    The reporters_db ships ~1,235 distinct abbreviations.
    """
    raw = _load_json("reporters.json")
    out: dict[str, tuple[ReporterEntry, ...]] = {}
    for abbrev, entries in raw.items():
        out[abbrev] = tuple(_parse_reporter_entry(abbrev, e) for e in entries)
    return out


@lru_cache(maxsize=1)
def reporter_canonical_set() -> frozenset[str]:
    """Every canonical Bluebook reporter abbreviation.

    Includes BOTH:

    - Top-level dict keys (``F.``, ``U.S.``, ``S. Ct.``)
    - Edition keys nested under each entry (``F.2d``, ``F.3d``,
      ``F.4th``, ``F. Supp. 2d``, etc.)

    The reporters_db organizes a reporter's editions as children of a
    single canonical key (``F.`` is the parent of ``F.2d``/``F.3d``).
    For citation MATCHING, every edition key is a canonical form a
    document might use — so we flatten them into one set.
    """
    out: set[str] = set()
    for abbrev, entries in load_reporters().items():
        out.add(abbrev)
        for e in entries:
            for ed in e.editions:
                out.add(ed.edition_key)
    return frozenset(out)


@lru_cache(maxsize=1)
def reporter_variations() -> dict[str, str]:
    """Return ``{variant: canonical}`` for every reporter spelling
    variation across all entries.

    Example: ``{"U. S.": "U.S.", "USSCR": "U.S."}``. Used to normalize
    extracted reporter strings to the canonical Bluebook form.
    """
    out: dict[str, str] = {}
    for entries in load_reporters().values():
        for e in entries:
            for variant, canonical in e.variations:
                out[variant] = canonical
    return out


@lru_cache(maxsize=1)
def reporter_all_spellings() -> frozenset[str]:
    """Every spelling that should match — canonical + edition keys +
    variations.

    Used as the universe of strings to register in the FstSet so that
    reporter detection catches ``U.S.``, ``U. S.``, ``USSCR``, ``F.3d``,
    ``F. 3d``, ``F3d``, etc.
    """
    spellings: set[str] = set(reporter_canonical_set())
    spellings.update(reporter_variations().keys())
    return frozenset(spellings)


# ---------------------------------------------------------------------------
# Case-name abbreviations
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_case_name_abbreviations() -> dict[str, tuple[str, ...]]:
    """Return ``{abbreviation: tuple[full_word, ...]}`` mapping.

    The vendored reporters_db file uses abbreviations as keys and
    full-form expansions as values, e.g. ``{"Ass'n": ["Association"]}``,
    ``{"Inc.": ["Incorporated"]}``. We preserve that direction.
    """
    raw = _load_json("case_name_abbreviations.json")
    return {abbrev: tuple(expansions) for abbrev, expansions in raw.items()}


# Modern entity-type abbreviations not present in vendored
# case_name_abbreviations.json (reporters_db is biased toward older
# Bluebook conventions). We supplement with these to keep case-name
# parsing robust against contemporary corporate forms.
_MODERN_CASE_NAME_TOKENS: frozenset[str] = frozenset(
    {
        "LLC",
        "L.L.C.",
        "LLP",
        "L.L.P.",
        "PLLC",
        "P.L.L.C.",
        "LP",
        "L.P.",
        "P.A.",
        "P.C.",
        "N.A.",
        "S.A.",
        "AG",
        "GmbH",
        "PLC",
    }
)


@lru_cache(maxsize=1)
def case_name_abbreviation_tokens() -> frozenset[str]:
    """Flat set of every abbreviation token used in case names.

    Includes ``Ass'n``, ``Co.``, ``Corp.``, ``Inc.``, ``Ltd.``,
    ``LLC``, ``LLP``, ``Soc'y``, etc. Used by the case-name boundary
    detector to know that a token like ``Inc.`` does NOT terminate
    the case name even though it ends in a period.

    Sources:
      1. Vendored reporters_db ``case_name_abbreviations.json`` keys
      2. ``_MODERN_CASE_NAME_TOKENS`` — supplementary list for modern
         entity types (LLC, LLP, P.A., etc.) that the historical DB
         doesn't cover.
    """
    return frozenset(load_case_name_abbreviations().keys()) | _MODERN_CASE_NAME_TOKENS


# ---------------------------------------------------------------------------
# State abbreviations
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_state_abbreviations() -> dict[str, str]:
    """Return ``{Bluebook_abbrev: state_name}`` — e.g.
    ``{"Cal.": "California", "N.Y.": "New York"}``."""
    return _load_json("state_abbreviations.json")


@lru_cache(maxsize=1)
def state_abbreviation_set() -> frozenset[str]:
    """Flat set of state abbreviations (``Ala.``, ``Cal.``, ``N.Y.``,
    etc.)."""
    return frozenset(load_state_abbreviations().keys())


# ---------------------------------------------------------------------------
# Laws (statute reporters: U.S.C., I.R.C., state codes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LawReporterEntry:
    abbreviation: str
    cite_type: str
    name: str
    jurisdiction: str
    examples: tuple[str, ...]
    regexes: tuple[str, ...]
    href: str = ""


@lru_cache(maxsize=1)
def load_law_reporters() -> dict[str, LawReporterEntry]:
    """Return the laws.json db — statute / code reporters keyed by
    abbreviation (``U.S.C.``, ``I.R.C.``, ``Cal. Penal Code``, etc.)."""
    raw = _load_json("laws.json")
    out: dict[str, LawReporterEntry] = {}
    for abbrev, entries in raw.items():
        # laws.json values are lists of dicts (like reporters.json) —
        # take the first entry; multi-entry laws are rare and we don't
        # currently need historical disambiguation here.
        first = entries[0] if entries else {}
        out[abbrev] = LawReporterEntry(
            abbreviation=abbrev,
            cite_type=first.get("cite_type", ""),
            name=first.get("name", ""),
            jurisdiction=first.get("jurisdiction", ""),
            examples=tuple(first.get("examples") or ()),
            regexes=tuple(first.get("regexes") or ()),
            href=first.get("href", ""),
        )
    return out


@lru_cache(maxsize=1)
def law_reporter_set() -> frozenset[str]:
    return frozenset(load_law_reporters().keys())


# ---------------------------------------------------------------------------
# Journals
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class JournalEntry:
    abbreviation: str
    cite_type: str
    name: str
    examples: tuple[str, ...]
    regexes: tuple[str, ...]
    notes: str = ""


@lru_cache(maxsize=1)
def load_journals() -> dict[str, JournalEntry]:
    """Return journals.json — law-review / law-journal abbreviations
    keyed by Bluebook short form (``Yale L.J.``, ``Harv. L. Rev.``,
    etc.). ~797 entries."""
    raw = _load_json("journals.json")
    out: dict[str, JournalEntry] = {}
    for abbrev, entries in raw.items():
        first = entries[0] if entries else {}
        out[abbrev] = JournalEntry(
            abbreviation=abbrev,
            cite_type=first.get("cite_type", ""),
            name=first.get("name", ""),
            examples=tuple(first.get("examples") or ()),
            regexes=tuple(first.get("regexes") or ()),
            notes=first.get("notes", ""),
        )
    return out


@lru_cache(maxsize=1)
def journal_abbreviation_set() -> frozenset[str]:
    return frozenset(load_journals().keys())


# ---------------------------------------------------------------------------
# Courts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CourtEntry:
    """One court_db entry. ~2,809 entries total."""

    court_id: str
    name: str
    jurisdiction: str
    citation_strings: tuple[str, ...]
    examples: tuple[str, ...]


@lru_cache(maxsize=1)
def load_courts() -> tuple[CourtEntry, ...]:
    """Return all court_db entries as a tuple."""
    raw = _load_json("courts.json")
    out: list[CourtEntry] = []
    for entry in raw:
        out.append(
            CourtEntry(
                court_id=entry.get("id", ""),
                name=entry.get("name", ""),
                jurisdiction=entry.get("jurisdiction", ""),
                citation_strings=tuple(
                    entry.get("citation_string", "").split("|")
                    if entry.get("citation_string")
                    else ()
                ),
                examples=tuple(entry.get("examples") or ()),
            )
        )
    return tuple(out)


@lru_cache(maxsize=1)
def court_citation_strings() -> frozenset[str]:
    """Every court citation string (e.g. ``2d Cir.``, ``S.D.N.Y.``)
    that appears in courts_db, flattened and deduplicated.

    Used by case-citation parsing to detect the court abbreviation in
    a parenthetical."""
    out: set[str] = set()
    for c in load_courts():
        for s in c.citation_strings:
            s = s.strip()
            if s:
                out.add(s)
    return frozenset(out)


@lru_cache(maxsize=1)
def court_id_by_citation_string() -> dict[str, str]:
    """Reverse map: citation string → court_id. When multiple courts
    share a citation string (rare) the first wins; downstream callers
    can use ``load_courts()`` for full disambiguation."""
    out: dict[str, str] = {}
    for c in load_courts():
        for s in c.citation_strings:
            s = s.strip()
            if s and s not in out:
                out[s] = c.court_id
    return out


__all__ = [
    "CourtEntry",
    "JournalEntry",
    "LawReporterEntry",
    "ReporterEdition",
    "ReporterEntry",
    "case_name_abbreviation_tokens",
    "court_citation_strings",
    "court_id_by_citation_string",
    "journal_abbreviation_set",
    "law_reporter_set",
    "load_case_name_abbreviations",
    "load_courts",
    "load_journals",
    "load_law_reporters",
    "load_reporters",
    "load_state_abbreviations",
    "reporter_all_spellings",
    "reporter_canonical_set",
    "reporter_variations",
    "state_abbreviation_set",
]
