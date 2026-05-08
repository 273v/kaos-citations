"""Corpus benchmark — validate kaos-citations against realistic legal text.

Goals:

1. **Precision**: every extracted citation should be a real citation
   (no false positives in plain English, no overlapping spans).
2. **Recall**: representative legal-text fixtures should produce the
   expected breadth of citation kinds.
3. **Eyecite cross-validation**: where eyecite is the gold standard
   (case citations), our case extractor must agree on all full-form
   citations eyecite produces.
4. **No-regression density**: every fixture has a documented expected
   count per kind so adding a new parser doesn't silently regress one
   we already had.

These are NOT live-network tests. The fixtures live in
``tests/benchmarks/corpus/`` and are checked into the repo.

Run::

    uv run pytest tests/benchmarks/ -v

The benchmark prints a summary table on stdout when ``-s`` is passed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("eyecite")

from kaos_citations import extract_citations
from kaos_citations.model import CaseCitation

_CORPUS_DIR = Path(__file__).parent / "corpus"


# ---------------------------------------------------------------------------
# Fixture descriptors — each fixture is a real-style document with an
# expected breadth (per-kind minimum count). Tests fail if a fixture
# loses a kind it previously matched, or if a kind unexpectedly fires
# in the negative corpus.
# ---------------------------------------------------------------------------

# Each entry: (filename, dict[kind, min_expected_count]).
# Use min_expected_count=0 only for kinds that should *never* fire in
# this fixture (false-positive guards).
_LEGAL_FIXTURES: tuple[tuple[str, dict[str, int]], ...] = (
    (
        "scotus_excerpt.txt",
        {
            "case": 15,  # ~18 full-form case cites in fixture
            "id": 1,  # ``Id. at 393``
            "statute": 1,  # 42 U.S.C. § 1983
            "const": 1,  # U.S. Const. amend. XIV
            "fed_rule": 1,  # Fed. R. Civ. P. 8(a)(2)
        },
    ),
    (
        "sec_release_excerpt.txt",
        {
            "sec_filing": 4,  # 10-K, 10-Q, 8-K, ADV, 13D
            "sec_release": 4,  # 33-, 34-, IC-, IA-
            "sec_staff": 3,  # SAB 121, SLB 14L, C&DI, no-action
            "sec_reg": 1,  # Reg. S-X
            "finra_rule": 1,
            "finra_notice": 1,
            "finra_disciplinary": 1,
            "exchange_rule": 3,  # MSRB, NYSE, Nasdaq
            "fed_reserve_reg": 1,  # Reg. Z
            "fed_reserve_letter": 1,  # SR 23-04
            "fdic_doc": 1,
            "occ_doc": 1,
            "cfpb_doc": 1,
            "ncua_letter": 1,
            "basel": 1,
            "cftc_doc": 1,
            "naic": 1,
            "intl_finance": 1,
            "irs_guidance": 3,  # Rev. Rul., Rev. Proc., T.D., IRM
            "treas_reg": 1,
            "cfr": 1,  # 17 CFR 240.10b-5
            "statute": 1,  # 15 U.S.C. § 78j(b)
            "case": 1,  # Stoneridge
        },
    ),
    (
        "accounting_excerpt.txt",
        {
            "asc": 6,  # multiple ASC cites
            "asu": 1,
            "legacy_fasb": 4,  # FAS 142, FIN 48, EITF 02-13, APB Op. 18, CON 8
            "pcaob": 4,  # AS 2401, Release, Rule, Practice Alert
            "aicpa": 3,  # SAS, SSAE, Code
            "ifrs": 5,  # IFRS 15, IFRS 15.31, IAS 36, IFRIC 23, SIC-7
            "iaasb": 2,  # ISA 315, ISAE 3000
            "iesba": 1,
            "gasb": 1,
            "fasab": 1,
            "govt_audit": 2,  # OMB A-133, Yellow Book
            "naic_acct": 1,
            "sustainability": 4,  # GRI, SASB, TCFD, ESRS, IFRS S1
        },
    ),
)


# Negative corpus — these kinds should never fire on plain English text.
# We allow a small whitelist for kinds that legitimately match common
# numeric patterns (e.g. ``CA 23-01`` could match a CA Fed Reserve letter),
# but legal-specific kinds like case / cfr / statute / const / fed_rule
# / agency_adj / sec_filing must stay at zero.
_NEGATIVE_FIXTURE = "negative_text.txt"
_NEGATIVE_FORBIDDEN_KINDS: frozenset[str] = frozenset(
    {
        "case",
        "case_short",
        "cfr",
        "const",
        "fed_register",
        "fed_rule",
        "statute",
        "public_law",
        "legislative",
        "agency_adj",
        "agency_manual",
        "legal_opinion",
        "bar_ethics",
        "treas_reg",
        "irs_guidance",
        "sec_filing",
        "sec_release",
        "sec_staff",
        "sec_reg",
        "finra_rule",
        "finra_notice",
        "finra_disciplinary",
        "exchange_rule",
        "occ_doc",
        "fdic_doc",
        "cfpb_doc",
        "ncua_letter",
        "basel",
        "cftc_doc",
        "naic",
        "ffiec_call",
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
        "restatement",
        "uniform_act",
        "ussg",
        "exec_action",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> str:
    return (_CORPUS_DIR / name).read_text(encoding="utf-8")


def _kind_counts(cites: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in cites:
        counts[c.kind] = counts.get(c.kind, 0) + 1
    return counts


def _assert_no_overlapping_spans(cites: list[Any]) -> None:
    """Two extracted citations of the same kind must not share an
    overlapping span — that's a parser-internal duplicate. Different
    kinds may overlap (e.g. ``Treas. Reg.`` may also surface as a
    statute due to eyecite's permissive law-cite extractor; we tolerate
    that and rely on per-kind dedup downstream)."""
    by_kind: dict[str, list[tuple[int, int]]] = {}
    for c in cites:
        by_kind.setdefault(c.kind, []).append(c.span)
    for kind, spans in by_kind.items():
        spans.sort()
        for i in range(len(spans) - 1):
            a, b = spans[i], spans[i + 1]
            if a[1] > b[0]:
                raise AssertionError(
                    f"overlapping {kind} spans: {a} and {b}; parser dedup is broken"
                )


# ---------------------------------------------------------------------------
# Per-fixture coverage tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,expected", _LEGAL_FIXTURES)
def test_fixture_coverage(filename: str, expected: dict[str, int]) -> None:
    """Each legal fixture must produce at least the expected per-kind
    counts. The expected values were calibrated against the as-shipped
    parser set; tightening or loosening should be a deliberate edit."""
    text = _load_fixture(filename)
    cites = extract_citations(text, source_uri=f"benchmark://{filename}")
    counts = _kind_counts(cites)
    missing: list[str] = []
    for kind, min_count in expected.items():
        actual = counts.get(kind, 0)
        if actual < min_count:
            missing.append(f"{kind}: expected ≥{min_count}, got {actual}")
    assert not missing, (
        f"{filename}: coverage regression — {missing}\nfull counts: {dict(sorted(counts.items()))}"
    )
    _assert_no_overlapping_spans(cites)


# ---------------------------------------------------------------------------
# Negative corpus — plain English must produce no legal citations
# ---------------------------------------------------------------------------


def test_negative_corpus_no_legal_citations() -> None:
    """Plain-English mountain-ecology prose must not surface any
    forbidden legal/financial/accounting kinds. URLs / DOIs / archive
    links are tolerated when present."""
    text = _load_fixture(_NEGATIVE_FIXTURE)
    cites = extract_citations(text, source_uri=f"benchmark://{_NEGATIVE_FIXTURE}")
    forbidden_hits = [c for c in cites if c.kind in _NEGATIVE_FORBIDDEN_KINDS]
    assert not forbidden_hits, (
        f"negative corpus produced false-positive citations: "
        f"{[(c.kind, c.normalized) for c in forbidden_hits]}"
    )


# ---------------------------------------------------------------------------
# Eyecite cross-validation on the SCOTUS fixture
# ---------------------------------------------------------------------------


def test_case_citations_match_eyecite_full_forms() -> None:
    """Every full-form case citation eyecite finds in the SCOTUS
    fixture must also appear in our extraction (modulo dedup of
    repeated cites at the same span)."""
    import eyecite
    from eyecite.models import FullCaseCitation

    text = _load_fixture("scotus_excerpt.txt")
    eyecite_full = [c for c in eyecite.get_citations(text) if isinstance(c, FullCaseCitation)]
    eyecite_keys: set[tuple[str | None, str | None, str | None]] = set()
    for c in eyecite_full:
        groups = c.groups or {}
        eyecite_keys.add(
            (
                str(groups.get("volume")) if groups.get("volume") else None,
                groups.get("reporter"),
                str(groups.get("page")) if groups.get("page") else None,
            )
        )

    ours = extract_citations(text, source_uri="benchmark://scotus_excerpt.txt", kinds=("case",))
    our_keys: set[tuple[str | None, str | None, str | None]] = set()
    for c in ours:
        if isinstance(c, CaseCitation):
            our_keys.add(
                (
                    str(c.volume) if c.volume else None,
                    c.reporter,
                    str(c.page) if c.page else None,
                )
            )

    missing = eyecite_keys - our_keys
    assert not missing, (
        f"kaos-citations missed {len(missing)} eyecite full-form cases: {missing}\n"
        f"  eyecite found: {len(eyecite_keys)}, we found: {len(our_keys)}"
    )


# ---------------------------------------------------------------------------
# Smoke / summary — informational, prints when -s is passed
# ---------------------------------------------------------------------------


def test_print_corpus_summary(capsys: pytest.CaptureFixture[str]) -> None:
    """Print a summary table — useful when iterating on the parser set.
    Always passes; the output is for human review with ``pytest -s``."""
    rows: list[tuple[str, int, dict[str, int]]] = []
    for filename, _expected in _LEGAL_FIXTURES:
        text = _load_fixture(filename)
        cites = extract_citations(text, source_uri=f"benchmark://{filename}")
        rows.append((filename, len(cites), _kind_counts(cites)))
    text = _load_fixture(_NEGATIVE_FIXTURE)
    neg_cites = extract_citations(text, source_uri=f"benchmark://{_NEGATIVE_FIXTURE}")
    rows.append((_NEGATIVE_FIXTURE, len(neg_cites), _kind_counts(neg_cites)))

    print()
    print("=" * 78)
    print("kaos-citations benchmark — per-fixture extraction summary")
    print("=" * 78)
    for filename, total, counts in rows:
        print(f"\n{filename}: {total} citations")
        for kind in sorted(counts):
            print(f"  {kind:24s} {counts[kind]}")
    print()
    captured = capsys.readouterr()
    # Ensure we actually printed something useful
    assert "benchmark" in captured.out
