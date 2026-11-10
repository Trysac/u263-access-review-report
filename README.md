# trysac-access-review-report

[![CI](https://github.com/Trysac/u263-access-review-report/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u263-access-review-report/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/trysac-access-review-report.svg)](https://badge.fury.io/py/trysac-access-review-report)

Build periodic access review reports from system account exports and an HR roster. The library reads exported CSV data, applies explicit dated rules, and writes CSV or JSON. It detects terminated users with access, orphaned accounts, dormant accounts, never-used accounts, and privileged roles.

## Installation

```bash
pip install trysac-access-review-report
```

## Usage

```python
from datetime import date
from access_review_report import load_accounts, load_roster, review

accounts = load_accounts(open("accounts.csv").read(), system="github")
roster = load_roster(open("roster.csv").read())
report = review(accounts, roster, today=date(2026, 11, 9))
print(report.to_csv())
```

Or use the command line:

```bash
python -m access_review_report --accounts github=accounts.csv --roster roster.csv --today 2026-11-09 --format csv
```

Exit codes: `0` no high findings, `1` high findings present, `2` usage or input error.

## Public API

- `load_accounts(text: str, *, system: str) -> list[Account]` parses an accounts CSV. Required columns are `account_id`, `email`, `role`, `last_login`, and `status`; extra columns are ignored.
- `load_roster(text: str) -> dict[str, RosterEntry]` parses an HR roster CSV. Required columns are `email`, `status`, and `termination_date`.
- `review(accounts, roster, *, today, dormant_days=90, privileged_roles=('admin', 'owner', 'superuser', 'root', 'maintainer'), service_accounts=()) -> Report` applies the rules. `today` is required; there is no wall-clock lookup.
- `Report.findings` is a tuple of `Finding` values. `Report.summary` contains `accounts`, `high`, `medium`, `low`, and `info` counts.
- `Report.to_csv()` returns CSV text. `Report.to_json()` returns JSON text with sorted keys.

`AccessReviewError` has `code` and `message` attributes. Codes are `missing_column`, `invalid_date`, `invalid_value`, `input_too_large`, `too_many_rows`, and `duplicate_account`.

Limits: input text must be at most `MAX_INPUT_BYTES` (10,485,760 bytes); accounts and roster may contain at most `MAX_ROWS` (100,000) data rows.

Options: `dormant_days` must be non-negative. `privileged_roles` is matched case-insensitively after stripping. `service_accounts` is normalised by stripping and casefolding.

## Input Formats

### Accounts CSV

Required columns: `account_id`, `email`, `role`, `last_login`, `status`.
`last_login` is an ISO date (`YYYY-MM-DD`) or empty. `status` is `active` or `disabled`; matching is case-insensitive. Email addresses are stripped and casefolded. Extra columns are ignored. A leading UTF-8 BOM is stripped.

### Roster CSV

Required columns: `email`, `status`, `termination_date`.
`status` is `active` or `terminated`; matching is case-insensitive. `termination_date` is an ISO date or empty. Email addresses are stripped and casefolded. A leading UTF-8 BOM is stripped.

## Rules

| Code | Severity | Condition |
|---|---|---|
| `terminated_with_access` | high | Roster status terminated and account active |
| `orphaned` | high | Active account not in roster and not a service account |
| `dormant` | medium | `today - last_login > dormant_days` |
| `never_logged_in` | low | Empty `last_login` |
| `privileged` | info | Role in `privileged_roles` |

Disabled accounts receive no findings. Service accounts receive only `privileged` findings.

## Security

CSV output protects against CSV injection by prefixing cells that start with `=`, `+`, `-`, `@`, tab, or carriage return with an apostrophe. `to_json()` does not apply this CSV-specific prefix. See [docs/SECURITY.md](docs/SECURITY.md) for the threat model and limits.

## Why not a spreadsheet

A spreadsheet requires manual matching each period. This utility applies the same explicit rules every run, requires a dated `today` value, and writes an export that is safe to open in a spreadsheet for auditor review. It reads exported data; it does not evaluate permissions or fetch exports from systems.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [Testing](docs/TESTING.md)
- [Project](docs/PROJECT.md)
- [Stack](docs/STACK.md)
