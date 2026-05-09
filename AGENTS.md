# Agent Guidance

## Scope

This file is the canonical coding-agent guidance for this repository.
Follow it for automated or assisted changes in `kaos-citations`, and
defer to the linked project docs for details rather than duplicating
their full content here.

Keep changes focused. Preserve user changes already present in the
worktree. Do not edit generated files or release artifacts unless the
task explicitly requires it.

## Project Identity

- Distribution: `kaos-citations`.
- Import package: `kaos_citations`.
- Python: 3.13 or newer.
- Package role: offline, deterministic citation identification and
  extraction. Text goes in; typed `Citation` records with provenance
  come out.
- Public surfaces include `kaos_citations.__all__`, Pydantic citation
  models, `extract_citations`, CLI entry points, MCP tools/resources,
  serialized schemas, and documented behavior.

## Setup

Use `uv` for environments, dependency resolution, builds, and tool
execution:

```bash
uv sync --group dev
uvx pre-commit install
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before non-trivial work. Use
the detailed standards under [docs/standards/](docs/standards/) as the
source of truth for architecture, code quality, process, tests, and CI.

## Local Checks

For normal code changes, run the local quality gate:

```bash
uv run ruff format --check kaos_citations tests
uv run ruff check kaos_citations tests
uv run ty check kaos_citations tests
uv run pytest -m "not live and not network and not slow and not integration" --no-cov
```

Use `ty`, not mypy. Inline type ignores use `# ty: ignore[...]` with
the narrowest practical rule and a reason when the reason is not
obvious.

For docs-only changes, at minimum run:

```bash
git diff --check
```

Also do a basic Markdown and link sanity review for any files changed.
If a requested or expected check is impractical, report the reason.

## Architecture Rules

Follow
[Python design and architecture](docs/standards/python-design-and-architecture.md)
and [code quality standards](docs/standards/code-quality-standards.md).

- Keep import-time work minimal: no network calls, filesystem scans,
  provider initialization, logging setup, or expensive model loads at
  import time.
- Keep base dependencies small and justified. Do not rely on undeclared
  transitive dependencies.
- Keep optional integrations behind declared extras and lazy imports.
- Use absolute imports for package code.
- Treat public API, CLI output, MCP schemas, JSON output, and Pydantic
  model shapes as compatibility contracts.
- Keep runtime extraction offline and deterministic.
- Route citation matching through the existing matcher/parser structure
  rather than adding ad hoc one-off parsing paths.

The current source layout is:

- `kaos_citations/model.py`: typed citation records and discriminated
  union contracts.
- `kaos_citations/extract.py`: top-level extraction dispatcher.
- `kaos_citations/parsers/`: citation-family parsers.
- `kaos_citations/postprocess.py`: cite IDs, signals, string-cite
  groups, short-form links, and history enrichment.
- `kaos_citations/data/`: vendored citation data and license
  provenance.
- `kaos_citations/tools.py` and `kaos_citations/resources.py`: MCP
  integration surfaces.

## Citation Principles

- Extraction and identification must be deterministic for the same
  input and options.
- Preserve provenance on every citation: `raw`, `normalized`, `span`,
  `source_uri` when provided, and `cite_id`.
- Keep `cite_id` stable for an extraction result and preserve
  cross-reference semantics for short forms, string cites, and
  subsequent history.
- Treat citation model fields, output ordering, schema shape, and
  serialized output as public contracts once released.
- Legal, financial, and accounting citation fixtures must be
  redistributable and carry source, license, and transformation
  provenance.
- Do not add citation resolution, URL fetching, source retrieval, or
  claim verification unless the task explicitly scopes that behavior
  into this package.
- Keep regex and matcher behavior covered by realistic examples,
  including negative examples and edge cases for legal, financial, and
  accounting citations.

## Testing

Follow [tests, fixtures, and CI](docs/standards/tests-fixtures-ci.md).

- New public behavior needs tests through the real public entry point
  when practical.
- Bug fixes need regression tests.
- Parser and matcher changes need realistic accepted and rejected
  examples.
- Security-sensitive behavior needs accepted and rejected cases with
  bounded input sizes.
- Fixture additions must document provenance, license, purpose, and any
  transformations.
- Unit-tier tests must not require network, credentials, local services,
  or large downloads.

## Security

Follow [SECURITY.md](SECURITY.md) and the security sections in the
standards docs.

- Never commit secrets, tokens, private keys, credentials, `.env`
  files, customer data, or privileged documents.
- Do not add GPL, AGPL, unknown-license, non-commercial, or
  no-derivatives dependencies.
- Validate untrusted inputs early and keep failures bounded and
  predictable.
- Do not expose credentials, internal paths, or sensitive payloads in
  logs, errors, CLI output, JSON output, or fixtures.
- Report suspected vulnerabilities through the repository security
  process, not public issues.

## Commits, PRs, And Releases

Follow [engineering process](docs/standards/engineering-process.md) and
[CONTRIBUTING.md](CONTRIBUTING.md).

- Use conventional commits.
- Sign commits with `git commit -s`.
- Keep PRs focused and explain what changed, why, how it was tested,
  public API or schema impact, and release impact.
- Add or update `CHANGELOG.md` for user-visible behavior, public API,
  CLI behavior, schema output, package metadata, security behavior, or
  deprecations.
- Run packaging checks only when packaging, metadata, README rendering,
  or release behavior changes:

```bash
uv build
uvx --from twine twine check --strict dist/*
```

- Do not move public tags. Do not force-push shared branches.
