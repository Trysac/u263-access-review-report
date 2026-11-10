# Security

## Threat Model

The library processes untrusted CSV exports from identity providers and HR systems. It must not be tricked into producing a report that hides or fabricates findings.

Defended: required-column checks, status validation, strict ISO date validation, duplicate `(system, account_id)` detection, duplicate roster-email detection, email normalisation by strip and casefold, input size and row limits, and CSV-injection prefixing in `Report.to_csv()`. Error messages truncate included input values to 200 characters. Logging uses a `NullHandler` by default and records only summary counts at debug level.

Not defended: the library does not authenticate or authorise users, fetch or verify source exports, expand group memberships, run approval workflows, validate email syntax beyond normalisation, or check that a roster termination date agrees with its status. `Report.to_json()` does not apply the CSV-injection apostrophe prefix. A caller can construct `Account` and `RosterEntry` objects directly; `review` revalidates statuses but not CSV columns.

### CSV Injection

When the report is opened in a spreadsheet, cells that begin with `=`, `+`, `-`, `@`, tab, or carriage return can be interpreted as formulas. `Report.to_csv()` applies `_sanitise_cell` to every field and prefixes a leading apostrophe when the value starts with one of these characters. This protection applies to CSV output only.

### Resource Exhaustion

Input text is limited to `MAX_INPUT_BYTES` = 10,485,760 bytes. Accounts and roster input are limited to `MAX_ROWS` = 100,000 data rows. Exceeding either raises `AccessReviewError` with code `input_too_large` or `too_many_rows`. The CLI reads at most `MAX_INPUT_BYTES + 1` bytes before decoding.

### Data Integrity

- Dates are strictly validated as `YYYY-MM-DD` ISO calendar dates; empty strings are allowed for `last_login` and `termination_date`.
- Duplicate `(system, account_id)` pairs raise `duplicate_account`.
- Duplicate roster emails raise `invalid_value`.
- Email addresses are stripped and casefolded in accounts, roster, and service-account lists.
- Account statuses must be `active` or `disabled`; roster statuses must be `active` or `terminated`.

### Logging

The library uses `logging.getLogger(__name__)` with a `NullHandler`. The only logged value is the review summary at debug level; no sensitive data is logged.

## Reporting a Vulnerability

Report security issues privately to the maintainers. Do not open a public issue.
