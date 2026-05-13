# kaos-citations test fixtures

Golden-set JSONL files used by the unit parsers to verify recall + field
extraction for the three regex/eyecite-backed citation kinds. Each line
is one JSON record: the `text` field is the input string fed to the
parser; the remaining fields are the expected typed-citation
attributes the parser must recover.

These are **hand-crafted by 273V** for the express purpose of being
deterministic regression fixtures. The underlying *citations themselves*
are landmark U.S. federal case names, U.S. Code sections, and CFR
sections — all public-domain government work product under
17 USC §105 — but the curated JSONL records (the chosen examples,
the `text` strings, and the expected-field structure) are original to
this test suite. No content was scraped from a third-party corpus.

Consumed by:
- `tests/unit/test_case_parser.py`
- `tests/unit/test_statute_parser.py`
- `tests/unit/test_cfr_parser.py`
- `tests/benchmarks/test_corpus_benchmark.py` (recall benchmark)

## Per-file provenance

| File | Records | Source | License | Retrieved | SHA-256 |
|---|---|---|---|---|---|
| `case-citations-golden.jsonl` | 15 SCOTUS landmark cases (Miranda, Brown, Marbury, Roe, Chevron, Citizens United, Gideon, Terry, Griswold, NYT v. Sullivan, US v. Nixon, Bivens, Mapp, Heller, Obergefell) | Hand-crafted by 273V for kaos-citations regression; case names + reporter cites are public-domain federal court opinions (17 USC §105) | Hand-crafted, 273V (CC0 for the JSONL records; underlying case names public-domain) | 2026-04-15 (first commit `43efaa76`) | `e617a7efb6306efe9b4bc608a763b73aa03905f6b8b17dd209b50abbbb64d9a3` |
| `statute-citations-golden.jsonl` | 10 U.S.C. citations (42 USC §1983, 18 USC §1341, 15 USC §78j(b), etc.) — exercises eyecite path + USC alphanumeric-section regex fallback | Hand-crafted by 273V for kaos-citations regression; underlying USC sections are public-domain federal statute (17 USC §105) | Hand-crafted, 273V (CC0 for the JSONL records; underlying statute text public-domain) | 2026-04-15 (first commit `43efaa76`) | `b14ec605fca3b9e5c8287deb59fbf89e7057948760cfd0d5ede48fe4152e0126` |
| `cfr-citations-golden.jsonl` | 20 CFR citations including formatting variants (`17 CFR 240.10b-5`, `17 CFR § 240.10b-5`, `17 C.F.R. § 240.10b-5`) — exercises the dedicated CFR regex parser and the eyecite-CFR skip-list | Hand-crafted by 273V for kaos-citations regression; underlying CFR sections are public-domain federal regulation (17 USC §105) | Hand-crafted, 273V (CC0 for the JSONL records; underlying regulatory text public-domain) | 2026-04-15 (first commit `43efaa76`) | `69e597ea1f7f617cd9d0fa4ab5718db17b797e03da2f995e60a9068d14663712` |

## Confirmations (per provenance-policy.md §"Backfill PR template")

- No file in this directory is customer / client / privileged content.
- No file is pseudonymized client content.
- No file was sourced from a non-public Slack/email/internal share.
- No file contains real PII; the case names are public-record SCOTUS
  parties.
- The dep-license denylist (CC-BY-NC, AGPL/GPL for data-shaped
  artifacts) does not apply — records are hand-crafted by 273V and
  the underlying citations are 17 USC §105 federal work product.

## How to refresh

Edit the JSONL files in place. After any change, re-run
`sha256sum tests/fixtures/*.jsonl` and update the matching row above.

```bash
sha256sum tests/fixtures/case-citations-golden.jsonl \
          tests/fixtures/statute-citations-golden.jsonl \
          tests/fixtures/cfr-citations-golden.jsonl
```
