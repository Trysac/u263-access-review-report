# Architecture

## Design Decision: Pure Functions and Immutable Data

The core `review` function takes an iterable of `Account` values, a mapping of normalised email to `RosterEntry`, and keyword parameters. It returns a `Report` without reading files or using the wall clock. Parsing is separate: `load_accounts` and `load_roster` read CSV text and raise `AccessReviewError`. `Account`, `RosterEntry`, `Finding`, and `Report` are frozen dataclasses; `Report.findings` is a tuple and `Report.summary` is a dict containing `accounts`, `high`, `medium`, `low`, and `info`.

## CSV Injection Mitigation

`Report.to_csv()` applies `_sanitise_cell` to every emitted field. A cell that starts with `=`, `+`, `-`, `@`, tab, or carriage return is prefixed with an apostrophe. Output uses `csv.writer` with a newline line terminator. `Report.to_json()` serialises values without this CSV-specific prefix.

## Size Limits

`MAX_INPUT_BYTES` is 10,485,760 bytes. `MAX_ROWS` is 100,000 data rows. `load_accounts` and `load_roster` check the UTF-8 encoded size and raise `input_too_large`; they count accounts or roster entries and raise `too_many_rows`. The CLI `_read_file` reads at most `MAX_INPUT_BYTES + 1` bytes before decoding.

## Error Handling

`AccessReviewError` carries a machine-readable `code` and a human-readable `message`. The code is one of `missing_column`, `invalid_date`, `invalid_value`, `input_too_large`, `too_many_rows`, or `duplicate_account`. Messages that include input values truncate them to at most 200 characters. `review` also raises `invalid_value` for negative `dormant_days` and for invalid account or roster statuses.
