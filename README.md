# kaos-citations

> **Part of [Kelvin Agentic OS](https://kelvin.legal) (KAOS)** — open agentic
> infrastructure for legal work, built by
> [273 Ventures](https://273ventures.com).
> See the [full KAOS package map](https://github.com/273v) for the rest of the stack.

[![PyPI - Version](https://img.shields.io/pypi/v/kaos-citations)](https://pypi.org/project/kaos-citations/)
[![Python](https://img.shields.io/pypi/pyversions/kaos-citations)](https://pypi.org/project/kaos-citations/)
[![License](https://img.shields.io/pypi/l/kaos-citations)](https://github.com/273v/kaos-citations/blob/main/LICENSE)
[![CI](https://github.com/273v/kaos-citations/actions/workflows/ci.yml/badge.svg)](https://github.com/273v/kaos-citations/actions/workflows/ci.yml)

**Structured, high-performance citation identification and extraction.**
Text in, typed `Citation` records out — frozen Pydantic models with
`raw` / `normalized` / `span` provenance, Bluebook modifiers
(`signal`, `pin_cite`, `parenthetical`, `weight`, `subsequent_history`,
stable `cite_id` cross-references), and family-specific structured
fields (volume / reporter / page / year / court / case_name; CFR title +
section; SEC filing form; ASC topic-subtopic-section; etc.).

Pure-Python, fully offline, deterministic, Rust-backed matching, ~5×
faster than `eyecite` on the SCOTUS corpus we benchmark against. Two
runtime deps (`kaos-core` + `kaos-nlp-core`) — no `httpx`, no
`eyecite`, no Python `re`-module imports.

60 supported `kind`s across four domains:

- **Legal** (25 kinds): case law (federal + state), U.S. Code, CFR,
  Federal Register, U.S. Constitution, Federal Rules + USSG, IRS
  guidance, Treasury Regs, executive actions, public laws + bills +
  reports + Cong. Rec., Restatements, Uniform Acts + Model Codes,
  agency adjudications + manuals, AG/OLC opinions, bar ethics, internet
  + archive URLs
- **Financial** (19 kinds): SEC filings + releases + staff guidance +
  named regulations (Reg. S-X / S-K / G / AB / M / FD / BTR / S-T),
  FINRA (rules / notices / disciplinary), exchange rules (NYSE /
  Nasdaq / Cboe / MSRB / OCC), banking (Fed Reserve / FDIC / OCC /
  CFPB / NCUA), Basel, CFTC, NAIC, FFIEC call reports, FATF / IOSCO
- **Accounting** (13 kinds): FASB ASC + ASU + legacy (FAS / FIN /
  FSP / EITF / CON / APB / ARB), PCAOB, AICPA, IFRS family (IFRS /
  IAS / IFRIC / SIC), IAASB, IESBA, GASB, FASAB, government audit
  (OMB / GAO / Yellow Book), NAIC SAP, sustainability frameworks
  (GRI / SASB / TCFD / ISSB / ESRS)
- **Identifier** (3 kinds): DOI, PubMed, arXiv (opt-in)

Identification + extraction only. Citation resolution (URL building,
body fetching) and claim verification belong to the rest of the KAOS
stack (`kaos-source`, `kaos-web`, `kaos-llm-core`'s `Cited[T]`,
`kaos-agents`).

## Architecture

Identification and extraction route through
[`kaos-nlp-core`](https://github.com/273v/kaos-nlp-core)'s Rust+PyO3
primitives. There is no Python `re` module and no third-party
tokenizer in the runtime path:

- **`MultiPatternMatcher`** (Aho-Corasick) over reporter spellings —
  one linear pass identifies every reporter token candidate.
- **`RegexMatcher`** (Rust `regex` crate) for per-family tail
  patterns (volume / page / pin cite / parenthetical, etc.).
- **`PunktTokenizer`** with the bundled legal model
  (~27,000 abbreviations) for sentence-boundary anchoring during
  Bluebook signal binding and string-cite grouping.
- **`FstSet`** for known-vocabulary lookups — reporters, courts,
  case-name abbreviations, journals, statute reporters, US states.
- **`Tokenizer`** for word-level operations.

Reporter / court / journal / case-name-abbreviation data is vendored
under [`kaos_citations/data/`](kaos_citations/data/) from the Free Law
Project's `reporters_db` and `courts_db` (BSD-2). The full upstream
license texts are preserved in
[`LICENSE.vendored`](kaos_citations/data/LICENSE.vendored). kaos-
citations consumes the JSON data only — no upstream Python code is
imported at runtime.

## Install

```bash
uv add kaos-citations
# or
pip install kaos-citations
```

`kaos-citations` requires Python **3.13** or newer.

## Quick start

```python
from kaos_citations import extract_citations

text = (
    "The court held that 17 CFR 240.10b-5(b) applies to insider "
    "trading, citing Brown v. Board of Education, 347 U.S. 483 (1954). "
    "See also U.S. Const. amend. I."
)

for c in extract_citations(text):
    print(f"  [{c.kind:<10}] {c.normalized!r:<30}  span={c.span}")
```

```
  [cfr       ] '17 CFR 240.10b-5(b)'           span=(20, 39)
  [case      ] '347 U.S. 483 (1954)'           span=(104, 116)
  [const     ] 'U.S. Const. amend. I'          span=(134, 154)
```

The base install handles every citation family — there are no
extras-gated extractors. Filter with `extract_citations(text, kinds=...)`:

```python
extract_citations(text, kinds=("case", "cfr"))   # only case + CFR
extract_citations(text, kinds=("statute",))      # only U.S.C. / state codes
```

### `raw` vs `normalized` vs `span`

For most citation families `raw == text[span[0]:span[1]] == normalized`.
Two exceptions to know about:

- **Case citations**: `span` covers only the volume-reporter-page anchor
  (`347 U.S. 483`), matching eyecite's contract. `normalized` reconstructs
  the canonical `vol reporter page (year)` form (`347 U.S. 483 (1954)`),
  pulling the year from a date parenthetical that sits outside `span`.
- **Citations with normalised reporters / spacing**: `raw` preserves the
  exact source spelling (e.g. `347 U. S. 483`); `normalized` rewrites to
  the Bluebook canonical (`347 U.S. 483`).

When you need the exact source bytes, use `text[c.span[0]:c.span[1]]`.
When you need a stable, reporter-canonical string, use `c.normalized`.

## Concepts

| Concept | What it is |
|---|---|
| **`Citation`** | Frozen Pydantic discriminated-union over 60 citation `kind`s. Every variant carries `raw` / `normalized` / `span` / `source_uri` / `cite_id` plus family-specific structured fields, plus Bluebook modifiers on the base class (`signal`, `pin_cite`, `pin_cite_kind`, `parenthetical`, `parenthetical_kind`, `weight`, `back_ref`, `string_cite_group`, `subsequent_history`). |
| **`extract_citations(text, *, kinds=None, source_uri=None)`** | Top-level dispatcher. Returns `list[Citation]` in source order. Pure-function, fully offline, deterministic. |
| **`KaosCitationsSettings`** | `ModuleSettings` subclass — empty at this release. Reserved for future configuration via the standard kaos-* env / context channels. |
| **MCP tools** | `kaos-citations-extract` (bulk), `kaos-citations-validate` (single citation), `kaos-citations-doctor` (diagnostic). All read-only, no network. Register via `register_citations_tools(runtime)`. |

## Citation kinds

Pass any of these as elements of the `kinds=` filter. The full per-family
taxonomy with canonical examples and structured fields lives in
[`docs/CITATION_TAXONOMY.md`](docs/CITATION_TAXONOMY.md).

| `kind` | Domain | Example |
|---|---|---|
| `case` | Legal | `Brown v. Bd. of Educ., 347 U.S. 483 (1954)` |
| `case_short` | Legal | `Brown, 347 U.S. at 495` |
| `id` | Legal | `Id. at 495` |
| `supra` | Legal | `Smith, supra note 12, at 45` |
| `case_ref` | Legal | `Roe at 240` |
| `journal` | Legal | `94 Yale L.J. 247 (1985)` |
| `cfr` | Legal | `17 C.F.R. § 240.10b-5` |
| `statute` | Legal | `42 U.S.C. § 1983` |
| `fed_register` | Legal | `88 Fed. Reg. 12,345 (Mar. 1, 2023)` |
| `const` | Legal | `U.S. Const. amend. I` |
| `fed_rule` | Legal | `Fed. R. Civ. P. 56(c)` |
| `ussg` | Legal | `U.S.S.G. § 2D1.1(a)(1)` |
| `treas_reg` | Legal | `Treas. Reg. § 1.501(c)(3)-1` |
| `irs_guidance` | Legal | `Rev. Rul. 78-189`, `Notice 2020-32` |
| `exec_action` | Legal | `Exec. Order No. 13,769`, `Proc. 9844` |
| `public_law` | Legal | `Pub. L. No. 111-148, 124 Stat. 119` |
| `legislative` | Legal | `H.R. 3590, 111th Cong. (2009)` |
| `restatement` | Legal | `Restatement (Second) of Torts § 402A (1965)` |
| `uniform_act` | Legal | `U.C.C. § 2-207` |
| `agency_adj` | Legal | `In re Boeing Co., 369 N.L.R.B. No. 8 (2020)` |
| `agency_manual` | Legal | `MPEP § 2106`, `TMEP § 1202.04` |
| `legal_opinion` | Legal | `42 Op. O.L.C. 1 (2018)` |
| `bar_ethics` | Legal | `ABA Comm. on Ethics, Formal Op. 477 (2017)` |
| `internet` | Legal | `https://example.com/page` |
| `archive` | Legal | `https://web.archive.org/web/.../...` |
| `sec_filing` | Financial | `Form 10-K, Apple Inc. (2023)` |
| `sec_release` | Financial | `Securities Act Release No. 33-11070` |
| `sec_staff` | Financial | `Staff Accounting Bulletin No. 121` |
| `sec_reg` | Financial | `Reg. S-X`, `Reg. S-K` |
| `finra_rule` | Financial | `FINRA Rule 2010` |
| `finra_notice` | Financial | `FINRA Reg. Notice 22-08` |
| `finra_disciplinary` | Financial | `FINRA Discip. Proc. 2018058950501` |
| `exchange_rule` | Financial | `NYSE Rule 123`, `Nasdaq Rule 5635` |
| `fed_reserve_reg` | Financial | `Reg. K`, `Reg. T` |
| `fed_reserve_letter` | Financial | `SR Letter 22-3`, `CA Letter 21-7` |
| `fdic_doc` | Financial | `FDIC FIL-22-2022` |
| `occ_doc` | Financial | `OCC Bull. 2020-26` |
| `cfpb_doc` | Financial | `CFPB Bull. 2022-04` |
| `ncua_letter` | Financial | `NCUA Letter 22-CU-04` |
| `basel` | Financial | `Basel III Framework, BCBS 189` |
| `cftc_doc` | Financial | `CFTC Letter No. 22-04` |
| `naic` | Financial | `NAIC Model Bull. 2023-1` |
| `intl_finance` | Financial | `FATF Recommendation 10`, `IOSCO Final Report` |
| `ffiec_call` | Financial | `FFIEC Call Report Schedule RC-R` |
| `asc` | Accounting | `ASC 606-10-25-2` |
| `asu` | Accounting | `ASU 2016-13` |
| `legacy_fasb` | Accounting | `FAS 109`, `FIN 48`, `EITF 02-13` |
| `pcaob` | Accounting | `PCAOB AS 2410`, `PCAOB Release No. 2022-002` |
| `aicpa` | Accounting | `AICPA SAS 145`, `AICPA Code of Professional Conduct § 1.130` |
| `ifrs` | Accounting | `IFRS 15`, `IAS 36`, `IFRIC 23` |
| `iaasb` | Accounting | `ISA 315 (Revised 2019)` |
| `iesba` | Accounting | `IESBA Code § 110.1` |
| `gasb` | Accounting | `GASB Statement No. 87` |
| `fasab` | Accounting | `SFFAS 6` |
| `govt_audit` | Accounting | `OMB Circular A-133`, `GAO Yellow Book § 6.30` |
| `naic_acct` | Accounting | `NAIC SSAP No. 62R` |
| `sustainability` | Accounting | `GRI 305`, `SASB FN-CB-410a.1`, `TCFD Recommendation 2(a)` |
| `doi` | Identifier | `10.1038/nature12373` |
| `pmid` | Identifier | `PMID: 24571878` |
| `arxiv` | Identifier | `arXiv:2305.10403` (opt-in) |

**`arxiv` is opt-in** — academic preprints are rarely cited in legal /
financial / accounting writing, so the dispatcher excludes them by default
to avoid noise. Add it explicitly to the filter when you want it:

```python
extract_citations(text, kinds=("arxiv", "doi", "pmid"))
```

## CLI

`kaos-citations` ships a single entry-point script,
`kaos-citations-serve`, that boots an MCP server exposing the three
read-only tools (`kaos-citations-extract`, `kaos-citations-validate`,
`kaos-citations-doctor`) and the `kaos-citations://kinds` resource:

```bash
kaos-citations-serve                  # stdio (for Claude Code, Codex, ...)
kaos-citations-serve --http --port 8765
```

Or via the kaos-mcp manager: `kaos-mcp serve --module citations`.

## Compatibility & status

| Aspect | |
|---|---|
| **Python** | 3.13, 3.14 (informational matrix entries for 3.14t free-threaded and 3.15-dev) |
| **OS** | Linux, macOS, Windows (pure-Python wheel; no native code) |
| **Maturity** | Alpha. The public API is documented in `kaos_citations.__all__` — the typed `Citation` discriminated union, `extract_citations`, the per-family `extract_*` functions, and the post-process passes. |
| **Stability policy** | Pre-1.0: minor bumps may change behaviour. Every change is documented in [`CHANGELOG.md`](CHANGELOG.md). The MCP tool surface and the `KAOS_CITATIONS_*` environment-variable namespace are public API. |
| **Test coverage** | 460+ unit + benchmark tests across the parsers, post-process passes, MCP tools, MCP resource, and corpus benchmarks. |
| **Type checker** | Validated with [`ty`](https://docs.astral.sh/ty/), Astral's Python type checker. |

## Companion packages

`kaos-citations` is one of the packages in the
[Kelvin Agentic OS](https://kelvin.legal). The broader stack:

| Package | Layer | What it does |
|---|---|---|
| [`kaos-core`](https://github.com/273v/kaos-core) | Core | Foundational runtime, MCP-native types, registries, execution engine, VFS |
| [`kaos-content`](https://github.com/273v/kaos-content) | Core | Typed document AST: Block/Inline, provenance, views |
| [`kaos-mcp`](https://github.com/273v/kaos-mcp) | Bridge | FastMCP server, `kaos` management CLI, MCP resource templates |
| [`kaos-pdf`](https://github.com/273v/kaos-pdf) | Extraction | PDF → AST with provenance |
| [`kaos-web`](https://github.com/273v/kaos-web) | Extraction | Web extraction, browser automation, search, domain intelligence |
| [`kaos-office`](https://github.com/273v/kaos-office) | Extraction | DOCX / PPTX / XLSX readers + writers to AST |
| [`kaos-tabular`](https://github.com/273v/kaos-tabular) | Extraction | DuckDB-powered SQL analytics |
| [`kaos-source`](https://github.com/273v/kaos-source) | Data | Government + financial data connectors (Federal Register, eCFR, EDGAR, GovInfo, PACER, GLEIF) |
| [`kaos-llm-client`](https://github.com/273v/kaos-llm-client) | LLM | Multi-provider LLM transport |
| [`kaos-llm-core`](https://github.com/273v/kaos-llm-core) | LLM | Typed LLM programming (Signatures, Programs, Optimizers) |
| [`kaos-nlp-core`](https://github.com/273v/kaos-nlp-core) | Primitives (Rust) | High-performance NLP primitives |
| [`kaos-nlp-transformers`](https://github.com/273v/kaos-nlp-transformers) | ML | Dense embeddings + retrieval |
| [`kaos-graph`](https://github.com/273v/kaos-graph) | Primitives (Rust) | Graph algorithms + RDF/SPARQL |
| [`kaos-ml-core`](https://github.com/273v/kaos-ml-core) | Primitives (Rust) | Classical ML on the document AST |
| [`kaos-citations`](https://github.com/273v/kaos-citations) | Legal | Legal citation extraction, resolution, verification |
| [`kaos-agents`](https://github.com/273v/kaos-agents) | Agentic | Agent runtime, memory, recipes |
| [`kaos-reference`](https://github.com/273v/kaos-reference) | Sample | Reference module for module authors |

Packages depend on `kaos-core`; everything else is opt-in. Mix and match the
ones you need.

## Development

```bash
git clone https://github.com/273v/kaos-citations
cd kaos-citations
uv sync --group dev
```

Install pre-commit hooks (recommended — they run the same checks as CI on
every commit, scoped to staged files):

```bash
uvx pre-commit install
uvx pre-commit run --all-files     # one-time full sweep
```

Manual QA commands (the same set CI runs):

```bash
uv run ruff format --check kaos_citations tests
uv run ruff check kaos_citations tests
uv run ty check kaos_citations tests
uv run pytest -m "not live and not network and not slow and not integration"
```

## Build from source

```bash
uv build
uv pip install dist/*.whl
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
for setup, quality gates, pull request expectations, and engineering
standards. By contributing you agree to follow the
[project conduct expectations](CODE_OF_CONDUCT.md) and certify the
[Developer Certificate of Origin v1.1](https://developercertificate.org/) —
sign every commit with `git commit -s`. Please open an issue before starting
on a non-trivial change so we can align on scope.

## Security

For security issues, **please do not file a public issue**. Report privately
via [GitHub Private Vulnerability Reporting](https://github.com/273v/kaos-citations/security/advisories/new)
or email **security@273ventures.com**. See [SECURITY.md](SECURITY.md) for the
full disclosure policy.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Copyright 2026 [273 Ventures LLC](https://273ventures.com).
Built for [kelvin.legal](https://kelvin.legal).
