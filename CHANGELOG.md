# Changelog

All notable changes to `kaos-citations` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] — 2026-05-25

Dependabot batch — automated dep bumps.

### Dependabot

- chore(deps): bump the deps-minor group with 6 updates (#27)

## [0.1.1] — 2026-05-23

### Added

- Declared `[mcp]` optional-dependency (`kaos-mcp>=0.1.0,<0.2`). The
  `kaos-citations-serve` console script and the README MCP-server
  section already advertised this install path, but the extra itself
  was not declared because `kaos-mcp` was not on PyPI when 0.1.0a1
  shipped. Closes audit-04/kaos-citations.md F-001.

### Changed

- `pyproject.toml` classifier bumped from `Development Status :: 3 - Alpha`
  to `Development Status :: 5 - Production/Stable` to reflect the
  0.1.0 GA release (WU-L #543) that froze the public API for the
  0.1.x line. Closes audit-04/kaos-citations.md Family D (classifier drift).

### Documentation

- **audit-04 §23-C public-API surface.** README "Maturity" row no
  longer says `kaos_citations.__all__` includes "the per-family
  `extract_*` functions". The top-level facade exposes only the
  dispatcher + 5 curated family extractors (the audit confirmed 6
  total `extract_*` names on the top-level surface; 132 names
  overall). The 59 additional per-family extractors live under
  `kaos_citations.parsers.__all__` (66 names total) and are public,
  but callers import them from the `parsers` subpackage. The prior
  README wording would have made `from kaos_citations import
  extract_sec_filing_citations` look like a stable contract — it
  isn't and never was. No public-API behavior change; doc-only fix
  closing audit-04/kaos-citations.md §23-C.

### Tests

- Test `tests/unit/test_serve_install_contract.py` pins the install
  contract: `kaos-citations-serve` exits 1 with `[mcp]` and
  `kaos-citations[mcp]` in stderr when `kaos-mcp` is unavailable.


## [0.1.0] — 2026-05-20

### Changed — WU-L of 0.1.0 GA plan

- 0.1.0 GA — WU-L of the 0.1.0 GA plan. First stable release of
  `kaos-citations`. The public API is frozen for the 0.1.x line: no
  breaking changes will land until 0.2.0. Runtime kaos-* pins raised
  from `>=0.1.0rc1,<0.2` to `>=0.1.0,<0.2` for both `kaos-core` and
  `kaos-nlp-core`. No source changes vs 0.1.0rc1.


## [0.1.0rc1] — 2026-05-20

### Changed

- Pin floor raised to `>=0.1.0rc1,<0.2` across kaos-* runtime
  dependencies (`kaos-core`, `kaos-nlp-core`). Refreshed `uv.lock`
  to pick up `kaos-core 0.1.0rc1` and `kaos-nlp-core 0.1.0rc1`.

### Internal

- WU-J of the 0.1.0 GA plan
  (`kaos-modules/docs/plans/2026-05-20-0.1.0-ga-plan.md`).
  Release candidate; freezes the public API for `kaos-citations`
  ahead of 0.1.0 GA.

## [0.1.0a4] — 2026-05-20

### Changed

- Bumped minimum `kaos-core` to `0.1.0a12` (post-URI-redesign +
  Capability type). kaos-citations does not use the URI redesign
  directly — the bump aligns the supported floor with the rest of
  the kaos-* DAG ahead of 0.1.0 GA.
- Refreshed `uv.lock` to pick up `kaos-nlp-core 0.1.0a8` and
  `kaos-core 0.1.0a12`.

### Internal

- WU-F.1 of the 0.1.0 GA plan
  (`kaos-modules/docs/plans/2026-05-20-0.1.0-ga-plan.md`).
  This is the smallest-delta dry-run of the Layer 5 catch-up ceremony.

## [0.1.0a3] — 2026-05-16

### Added

- **PEP 561 `py.typed` marker** so downstream consumers using `ty` /
  `mypy` / `pyright` pick up `kaos_citations`'s inline type
  annotations directly from the installed wheel.

### Security

- **bandit + vulture now run in both pre-commit and CI.** The
  ``.pre-commit-config.yaml`` gains two new hooks (bandit static
  security scan + vulture dead-code scan), mirrored by jobs in
  ``security.yml`` so the scan is publicly visible on every PR.
  Bandit skip list is justified inline per audit
  (``B101,B404,B603,B607``); vulture runs at ``--min-confidence
  100`` with a shared ``--ignore-names`` list for framework
  callbacks / signal handlers / OAuth field names that vulture
  can't infer from the import graph alone. Both hooks currently
  pass clean. Mirrors the rollout pattern from kaos-core.

### Changed

- **uv.lock is now tracked in git.** Previously gitignored at v0.1.0a1
  because the ``[mcp]`` optional extra (and the ``kaos-mcp`` dev
  dependency) referenced a sibling not yet on PyPI; ``uv lock``
  couldn't resolve them. ``kaos-mcp`` shipped (0.1.0a2), so the
  original gating reason no longer applies. Tracking the lockfile
  gives reproducible local dev environments, lets Dependabot surface
  sibling-version bumps as PRs, and makes the supply-chain pin set
  publicly auditable. Mirrors the org-wide convention being adopted
  across all 16 kaos-* repos.

### Infrastructure

- Public-PR CI workflows hardened with pinned action SHAs.
- Dependabot migrated to the uv ecosystem with a 72-hour cooldown
  matching the rest of the kaos-* org.
- CycloneDX SBOM ships as a release asset (F8).
- CODEOWNERS expansion + Dependabot + OpenSSF Scorecard rollup.
- macOS-arm64 + Windows-x64 test legs added to the CI matrix.

### Documentation

- Fixture provenance README backfilled (audit-03 D9).


## [0.1.0a2] — 2026-05-07

Second public alpha — recall fixes uncovered by a 16-document
real-PDF benchmark sweep against eyecite (court orders, FDA guidance,
GAO / GPO reports, SEC 10-Ks, EPA rulemaking, contracts, patents;
554 KB of real text). Previously we matched eyecite on 16/16 cases
in the synthetic SCOTUS fixture; on the wider corpus we missed 5
cases out of 41 (87% recall). This release closes both root causes.

### Fixed

- **Westlaw / LEXIS page numbers truncated at 5 digits.** Real
  Westlaw cites use 7-digit page numbers (``2013 WL 3958350``); the
  prior ``\d{1,5}`` page-anchor pattern silently truncated to 5 digits
  (``page=39583``), causing the resulting ``(volume, reporter, page)``
  tuple to disagree with eyecite. The ``_PAGE_HEAD_PATTERN`` and
  ``_PIN_HEAD_PATTERN`` integer caps are now ``\d{1,8}`` — accommodates
  Westlaw, LEXIS, and star-paginated services without affecting any
  conventional reporter (whose page numbers fit in 5 digits anyway).
  Three regression tests in ``TestWestlawAndLEXISPages`` lock the fix.

- **OCR-degraded reporter spellings rejected.** PDF text extraction
  (Tesseract / pypdfium2) commonly drops the case of one or more
  letters in multi-token reporters: ``Fed. Cl.`` → ``Fed. cl.``,
  ``F. Supp. 2d`` → ``F. supp. 2d``. The strict case-sensitive
  Aho-Corasick matcher rejected these, leaving the cite unrecognised.
  A second case-insensitive matcher now runs over reporter spellings
  ≥ 4 characters; results merge with the strict matcher's hits via
  longest-span-wins. Resolves OCR-degraded forms back to the
  canonical Bluebook spelling (``Fed. Cl.``). The 4-char threshold
  prevents bare-letter reporters (``P.``, ``F.``, ``WL``) from
  firing in unrelated prose. Five regression tests in
  ``TestOCRDegradedReporterMatching`` lock the fix and the
  false-positive guard.

### Notes

- Cross-validation against eyecite on the same 16-document corpus now
  shows kaos-citations finding **48 cases vs eyecite's 41** — net +7
  on coverage, driven by the lenient OCR-tolerance fix recovering
  cases eyecite did NOT find (the inverse of what we expected:
  eyecite's looser internal matching caught 5 OCR-degraded cites we
  initially missed; now we catch them too plus a category eyecite
  misses entirely).
- Speed unchanged on the SCOTUS fixture (~3.5 ms / 1918 chars); the
  added matcher pass adds ≤ 5% wall-clock on real-doc workloads.
- 498 unit tests, ruff format / ruff check / ty check all green.

## [0.1.0a1] — 2026-05-07

First public alpha release.

### Added

- **`extract_citations(text, *, kinds=None, source_uri=None)`** — top-
  level dispatcher across **60 supported `kind` literals** spanning
  four domains:
  - **Legal** (25 kinds): full-form + short-form case law (`case` /
    `case_short` / `id` / `supra` / `case_ref`), journal articles
    (`journal`), CFR, U.S. Code / I.R.C. / state codes (`statute`),
    Federal Register, U.S. Constitution, Federal Rules + USSG, Treasury
    Regulations, IRS guidance (Rev. Rul. / Rev. Proc. / Notice / PLR /
    TAM / GCM / FSA / CCA / T.D. / IRB / IRM), executive actions
    (E.O. / Proc. / Memo / Determination), public laws + bills +
    reports + Cong. Rec., Restatements, Uniform Acts + Model Codes,
    agency adjudications (NLRB / FERC / FCC / FTC / NTSB / EPA EAB /
    BIA / PTAB / TTAB), agency manuals (MPEP / TMEP / POMS), AG / OLC
    opinions, bar ethics opinions, internet URLs, archive URLs.
  - **Financial** (19 kinds): SEC filings (20+ form types), SEC
    releases (33-/34-/IC-/IA-/TIA-), SEC staff guidance (SAB / SLB /
    C&DI / no-action), SEC named regulations (Reg. S-X / S-K / G /
    AB / M / FD / BTR / S-T), FINRA rules + notices + disciplinary,
    exchange rules (NYSE / Nasdaq / Cboe / MSRB / OCC), Federal
    Reserve regs + SR/CA/OP letters, FDIC FILs, OCC bulletins +
    interpretive letters + conditional approvals, CFPB bulletins +
    circulars + advisory opinions, NCUA letters, Basel framework,
    CFTC interpretive + no-action + advisory + orders, NAIC
    bulletins + model acts, international finance bodies (FATF /
    IOSCO), FFIEC call reports.
  - **Accounting** (13 kinds): FASB ASC + ASU + legacy (FAS / FIN /
    FSP / EITF / TB / CON / APB / ARB), PCAOB AS + Releases + Rules
    + Practice Alerts, AICPA SAS / SSAE / SSARS / SOP / TQA / Code,
    IFRS family (IFRS / IAS / IFRIC / SIC / Practice Statement /
    Conceptual Framework), IAASB (ISA / ISAE / ISRE / ISRS / ISQM /
    ISQC), IESBA Code, GASB Statements + Implementation Guides +
    Concepts + Tech Bulletins + Interpretations, FASAB SFFAS +
    Concepts + Interpretations + Tech Bulletins, government audit
    (OMB Circulars + Memos + GAO Reports + Yellow Book), NAIC SSAP,
    sustainability frameworks (GRI / SASB / TCFD / ISSB / ESRS).
  - **Identifier** (3 kinds): DOI, PubMed, arXiv (opt-in by default).
- **Three MCP tools** (`kaos-citations-extract`, `kaos-citations-validate`,
  `kaos-citations-doctor`) — registered via
  `register_citations_tools(runtime)`. All read-only, fully offline.
  `kaos-citations-validate` rejects unknown `expected_kind` values
  upfront with an error and near-match suggestions.
- **One MCP resource** — `kaos-citations://kinds` — static taxonomy
  agents read for self-discovery: every `kind`, the broader family
  (`legal` / `financial` / `accounting` / `identifier`), a Bluebook-
  style example, and an `opt_in` flag. Registered via
  `register_citations_resources(runtime)`. Unit tests cross-check the
  table against the dispatcher's `_SUPPORTED_KINDS` so they cannot drift.
- **Typed `Citation` discriminated union** with frozen Pydantic
  models per family — every `model.__all__` symbol is re-exported
  from the package surface (`from kaos_citations import IFRSCitation`,
  `SECFilingCitation`, `AgencyAdjudicationCitation`, etc.).
  Citations carry stable provenance (`raw` / `normalized` / `span` /
  `source_uri`), a per-extraction `cite_id` (`c0001`, `c0002`, ...),
  and Bluebook-modifier fields on the base class: `signal`,
  `pin_cite`, `pin_cite_kind`, `parenthetical`, `parenthetical_kind`,
  `weight`, `back_ref`, `string_cite_group`, `subsequent_history`.
- **Stable cite-id cross references** — `back_ref` and the second
  tuple element of `subsequent_history` reference other citations by
  their `cite_id` (string), not by list index. Filtering or
  re-sorting the result list never breaks the cross-references.
- **Bluebook-correct case parenthetical handling** — date parens
  (`(1954)`, `(5th Cir. 1996)`) populate `year` and `court` only;
  weight parens (`(per curiam)` / `(en banc)`) populate `weight`;
  judge parens (`(Sotomayor, J., dissenting)`) populate `judges`.
  Only Bluebook R1.5 explanatory text spills into `parenthetical`.
  Multi-paren chains like `(2014) (per curiam) (holding ...)` are
  parsed correctly across all three slots.
- **Bluebook-correct case-name boundaries** — when extracting cite
  N+1, the case-name walk-back is floored at cite N's right edge.
  R10.7 subsequent-history connectors (`overruled by`, `aff'd`,
  `rev'd`, `vacated`, `cert. denied`, etc.) are stripped from the
  leading edge, so `Roe v. Wade, ..., overruled by Dobbs v. Jackson`
  yields two clean `case_name` values rather than swallowing the
  prior cite into the second.
- **kaos-nlp-core integration boundary** (`kaos_citations._nlp`):
  `get_sentence_tokenizer()` returns the singleton Punkt tokenizer
  initialized with the bundled legal model (~27,000 abbreviations).
  Loader fails loudly via `PunktModelMissingError` if the embedded
  model is missing or the abbreviation count is below threshold —
  no silent fallback to an empty tokenizer.
- **`kaos_citations.matchers`** — single source of truth for all
  matching: `regex(...)` (Rust regex), `multi_pattern(...)`
  (Aho-Corasick), `tokenize_words(...)`, `sentence_tokenizer()`,
  plus `FstSet` builders for reporters / courts / case-name
  abbreviations / journals / statute reporters / US states.
- **Vendored data** — `reporters_db` and `courts_db` JSON ship under
  `kaos_citations/data/` with the upstream BSD-2 license preserved
  in `kaos_citations/data/LICENSE.vendored`. The runtime consumes
  the JSON only; no upstream Python code is imported.
- **Bluebook post-processing passes** (`kaos_citations.postprocess`):
  cite-id assignment, signal binding (R1.2), string-cite grouping
  (R1.4), and subsequent-history detection (R10.7), all anchored to
  Punkt-derived sentence boundaries.
- **`KaosCitationsSettings`** — `ModuleSettings` subclass with env
  prefix `KAOS_CITATIONS_` (empty at this release; reserved).
- **Typed error hierarchy** rooted at
  `KaosCitationsError(KaosCoreError)`: `CitationParseError`.

### Notes

- The runtime dependency graph is exactly two packages: `kaos-core`
  (logging + settings + MCP tool primitives) and `kaos-nlp-core`
  (matching + Punkt + tokenization). No `httpx`, no `eyecite`, no
  `re`-module imports anywhere in the runtime.
- `kaos-citations` does NOT do citation resolution (URL building,
  body fetching) or claim verification. Those responsibilities live
  in the rest of the KAOS stack — `kaos-source` for typed source
  connectors, `kaos-web` for generic search + fetch, `kaos-llm-core`
  for in-process `Cited[T]` grounding, and `kaos-agents` for
  orchestration. Compose them with the typed citations this package
  produces.
- `kaos-mcp` is intentionally absent from extras at 0.1.0a1 — Wave 3,
  not yet on PyPI. The MCP server entry point will work once
  `kaos-mcp` publishes; until then, install `kaos-mcp` from source
  alongside `kaos-citations`.

[Unreleased]: https://github.com/273v/kaos-citations/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/273v/kaos-citations/releases/tag/v0.1.0a1
