# Project record

## Objective

Build periodic access review reports from system account exports and an HR roster: terminated users with access, orphaned, dormant and never-used accounts, and privileged roles.

## Scope

In scope: parse accounts and roster CSV text, apply the documented rules with a required `today` date, produce CSV and JSON reports, expose the typed public API, and provide the `python -m access_review_report` command. The package uses only the Python standard library at runtime.

Out of scope: fetching exports from systems, approval workflows, and group membership expansion. The library reads exported data; it does not evaluate permissions.

## Timeline

No timeline dates are recorded in the project specification.

## Effort metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 893908 / 88410 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1171 |

## Factory run u263 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | generation | deepseek-v4-pro | yes | 1716 | 22499 | 0 | 3328 | 0.0458 |
| 2026-11-10 | fix-1 | deepseek-flash | no | 12720 | 1624 | 0 | 55040 | 0.0030 |
| 2026-11-10 | fix-2 | deepseek-flash | no | 10341 | 8443 | 0 | 75776 | 0.0068 |
| 2026-11-10 | audit | deepseek-flash | no | 25067 | 19748 | 0 | 155392 | 0.0161 |
| 2026-11-10 | fix-3 | deepseek-flash | no | 27706 | 8094 | 0 | 264192 | 0.0098 |
| 2026-11-10 | threat-model | deepseek-flash | no | 15684 | 10529 | 0 | 80640 | 0.0089 |
| 2026-11-10 | fix-4 | deepseek-flash | no | 11056 | 1738 | 0 | 59520 | 0.0029 |
| 2026-11-10 | docs | deepseek-flash | no | 95474 | 15735 | 0 | 256 | 0.0238 |

Total: $0.1171. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
