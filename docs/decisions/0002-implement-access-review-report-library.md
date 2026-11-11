# Implement access review report library

Status: accepted (generated, pending human review)

## Context

Access reviews are performed manually with spreadsheets, which is error-prone and not reproducible. The library must apply explicit rules to account and roster exports.

## Decision

Implement a pure Python library with typed dataclasses, a review function applying fixed-severity rules, CSV/JSON serialization with CSV injection protection, and a CLI. Use only stdlib and enforce input size/row limits and duplicate detection.

## Consequences

The library is deterministic and safe. It is limited to parsing exports, not fetching data from systems. Users must provide current data.
