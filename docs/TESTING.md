# Testing

## Running

```sh
python -m pytest tests/test_access_review_report.py
```

The test module is collected by pytest. The cached bytecode filename records pytest 9.2.0.

## Policy

Tests import the public API from `access_review_report` and assert observable results: findings, summary counts, CSV and JSON text, and `AccessReviewError.code` and `message`. Fixed dates are passed to `review`; tests do not depend on the wall clock. The provided tree contains one test module and no separate `conftest.py`.

## Tiers

The provided tree contains a single pytest module. It contains no conformance marker tier, external-tool setup, or separate local/CI split.

## Layout

`tests/test_access_review_report.py` is the only test file shown. It defines `_accounts_csv` and `_roster_csv` helpers that build CSV text from rows, and the following tests:

- `test_acceptance_summary` builds the acceptance accounts and roster, calls `load_accounts`, `load_roster`, and `review` with `today=date(2026, 11, 9)` and `service_accounts={'ci-bot@example.com'}`, and asserts `summary == {'accounts': 5, 'high': 2, 'medium': 1, 'low': 1, 'info': 1}`.
- `test_individual_findings` asserts the specific findings: `a1` dormant medium with detail `last login 2026-08-10 (91 days ago)`; `a2` `terminated_with_access` high with detail `terminated 2026-10-01` and `privileged` info with detail `role admin`; `a3` `orphaned` high; `a4` has no findings; `a5` `never_logged_in` low; and findings are ordered by system, account_id, and code.
- `test_dormant_boundary_90_days` constructs `Account` values with `last_login` 2026-08-11 and 2026-08-10 for `today=date(2026, 11, 9)` and asserts no dormant finding at 90 days and a dormant finding at 91 days.
- `test_csv_injection_protection` uses an account with `account_id='=cmd'`, asserts `to_csv()` starts with the header `system,account_id,email,code,severity,detail`, and asserts the cell is written as `'=cmd`.
- `test_json_deterministic` calls `to_json()` twice, asserts the strings are equal, and checks the parsed JSON structure.
- `test_load_accounts_missing_column` parses an accounts CSV without `email` and asserts `AccessReviewError.code == 'missing_column'` with message `missing column: email`.
- `test_load_accounts_invalid_date_row_number` parses an accounts CSV with `last_login='2026-13-01'` and asserts `AccessReviewError.code == 'invalid_date'` and a message naming row 2.
