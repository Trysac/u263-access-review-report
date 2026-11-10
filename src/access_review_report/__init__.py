"""Build periodic access review reports from system account exports and an HR roster."""

from __future__ import annotations

import csv
import io
import json
import logging
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Literal

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

__version__ = "0.1.0"

ErrorCode = Literal[
    "missing_column",
    "invalid_date",
    "invalid_value",
    "input_too_large",
    "too_many_rows",
    "duplicate_account",
]

MAX_INPUT_BYTES = 10_485_760
MAX_ROWS = 100_000


class AccessReviewError(Exception):
    """Raised for invalid input data or usage errors."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class Account:
    """A single account from a system export."""

    system: str
    account_id: str
    email: str
    role: str
    last_login: date | None
    status: str


@dataclass(frozen=True)
class RosterEntry:
    """A single entry from the HR roster."""

    email: str
    status: str
    termination_date: date | None


@dataclass(frozen=True)
class Finding:
    """A single access review finding."""

    system: str
    account_id: str
    email: str
    code: str
    severity: str
    detail: str


@dataclass(frozen=True)
class Report:
    """The result of an access review."""

    findings: tuple[Finding, ...]
    summary: dict[str, int]

    def to_csv(self) -> str:
        """Return the report as CSV text, with CSV injection protection."""
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["system", "account_id", "email", "code", "severity", "detail"])
        for finding in self.findings:
            writer.writerow(
                [
                    _sanitise_cell(finding.system),
                    _sanitise_cell(finding.account_id),
                    _sanitise_cell(finding.email),
                    _sanitise_cell(finding.code),
                    _sanitise_cell(finding.severity),
                    _sanitise_cell(finding.detail),
                ]
            )
        return output.getvalue()

    def to_json(self) -> str:
        """Return the report as JSON text with sorted keys."""
        data = {
            "summary": self.summary,
            "findings": [
                {
                    "system": f.system,
                    "account_id": f.account_id,
                    "email": f.email,
                    "code": f.code,
                    "severity": f.severity,
                    "detail": f.detail,
                }
                for f in self.findings
            ],
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _truncate(value: str, limit: int = 200) -> str:
    """Truncate a string to at most ``limit`` characters."""
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


def _normalise_email(value: str) -> str:
    """Normalise an email address: strip surrounding whitespace and casefold."""
    return value.strip().casefold()


def _required_field(row: Mapping[str, str | None], name: str, row_number: int) -> str:
    """Return a CSV field, raising if the row is too short to contain it."""
    value = row.get(name)
    if value is None:
        raise AccessReviewError("invalid_value", f"missing field at row {row_number}")
    return value


def _is_iso_date(s: str) -> bool:
    """Return True if ``s`` strictly matches YYYY-MM-DD."""
    if len(s) != 10:
        return False
    if s[4] != "-" or s[7] != "-":
        return False
    return all(s[idx].isdigit() for idx in (0, 1, 2, 3, 5, 6, 8, 9))


def _parse_date(value: str, *, field: str, row: int) -> date | None:
    """Parse an ISO date or return None for an empty string."""
    if value == "":
        return None
    if not _is_iso_date(value):
        raise AccessReviewError("invalid_date", f"invalid {field} at row {row}: {_truncate(value)}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise AccessReviewError(
            "invalid_date", f"invalid {field} at row {row}: {_truncate(value)}"
        ) from None


def _check_size(text: str) -> None:
    """Raise if the UTF-8 encoded text exceeds the size limit."""
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise AccessReviewError("input_too_large", f"input exceeds {MAX_INPUT_BYTES} bytes")


def _check_row_count(count: int) -> None:
    """Raise if the number of rows exceeds the maximum."""
    if count > MAX_ROWS:
        raise AccessReviewError("too_many_rows", f"too many rows: maximum is {MAX_ROWS}")


def _sanitise_cell(value: str) -> str:
    """Prefix with apostrophe if the cell starts with a dangerous character."""
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def load_accounts(text: str, *, system: str) -> list[Account]:
    """Parse an accounts CSV export and return a list of Account objects.

    Required columns: account_id, email, role, last_login, status.
    Status must be 'active' or 'disabled' (case-insensitive).
    Email addresses are normalized (stripped and casefolded).
    Duplicate (system, account_id) pairs raise AccessReviewError.
    """
    _check_size(text)
    if text.startswith("\ufeff"):
        text = text[1:]
    if not system:
        raise AccessReviewError("invalid_value", "system must not be empty")

    reader = csv.DictReader(io.StringIO(text))
    required = {"account_id", "email", "role", "last_login", "status"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise AccessReviewError("missing_column", f"missing column: {', '.join(sorted(missing))}")

    accounts: list[Account] = []
    seen: set[tuple[str, str]] = set()
    for row in reader:
        row_number = reader.line_num
        _check_row_count(len(accounts) + 1)
        account_id = _required_field(row, "account_id", row_number)
        email = _normalise_email(_required_field(row, "email", row_number))
        role = _required_field(row, "role", row_number)
        status = _required_field(row, "status", row_number).strip()
        if status.casefold() not in ("active", "disabled"):
            raise AccessReviewError(
                "invalid_value", f"invalid status at row {row_number}: {_truncate(status)}"
            )
        last_login = _parse_date(
            _required_field(row, "last_login", row_number), field="last_login", row=row_number
        )
        key = (system, account_id)
        if key in seen:
            raise AccessReviewError("duplicate_account", f"duplicate account {system}/{account_id}")
        seen.add(key)
        accounts.append(
            Account(
                system=system,
                account_id=account_id,
                email=email,
                role=role,
                last_login=last_login,
                status=status,
            )
        )
    return accounts


def load_roster(text: str) -> dict[str, RosterEntry]:
    """Parse an HR roster CSV and return a dict keyed by normalized email.

    Required columns: email, status, termination_date.
    Status must be 'active' or 'terminated' (case-insensitive).
    """
    _check_size(text)
    if text.startswith("\ufeff"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))
    required = {"email", "status", "termination_date"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise AccessReviewError("missing_column", f"missing column: {', '.join(sorted(missing))}")

    roster: dict[str, RosterEntry] = {}
    for row in reader:
        row_number = reader.line_num
        _check_row_count(len(roster) + 1)
        email = _normalise_email(_required_field(row, "email", row_number))
        status = _required_field(row, "status", row_number).strip()
        if status.casefold() not in ("active", "terminated"):
            raise AccessReviewError(
                "invalid_value", f"invalid status at row {row_number}: {_truncate(status)}"
            )
        termination_date = _parse_date(
            _required_field(row, "termination_date", row_number),
            field="termination_date",
            row=row_number,
        )
        if email in roster:
            raise AccessReviewError(
                "invalid_value", f"duplicate roster email at row {row_number}: {_truncate(email)}"
            )
        roster[email] = RosterEntry(email=email, status=status, termination_date=termination_date)
    return roster


def review(
    accounts: Iterable[Account],
    roster: Mapping[str, RosterEntry],
    *,
    today: date,
    dormant_days: int = 90,
    privileged_roles: Collection[str] = ("admin", "owner", "superuser", "root", "maintainer"),
    service_accounts: Collection[str] = (),
) -> Report:
    """Review accounts against the roster and return a Report.

    Rules applied, in order:
    - terminated_with_access (high): roster status terminated and account active
    - orphaned (high): active account not in roster and not a service account
    - dormant (medium): today - last_login > dormant_days
    - never_logged_in (low): empty last_login
    - privileged (info): role casefolded in privileged_roles

    Disabled accounts receive no findings. Service accounts receive only
    privileged findings.
    """
    if dormant_days < 0:
        raise AccessReviewError("invalid_value", "dormant_days must be non-negative")

    service_accounts_norm = {_normalise_email(s) for s in service_accounts}
    privileged_norm = {role.strip().casefold() for role in privileged_roles}
    findings: list[Finding] = []
    accounts_count = 0

    for account in accounts:
        accounts_count += 1
        status_norm = account.status.casefold()
        if status_norm not in ("active", "disabled"):
            raise AccessReviewError(
                "invalid_value", f"invalid account status: {_truncate(account.status)}"
            )
        if status_norm == "disabled":
            continue

        email = _normalise_email(account.email)
        is_service = email in service_accounts_norm
        if is_service:
            if account.role.casefold() in privileged_norm:
                findings.append(
                    Finding(
                        system=account.system,
                        account_id=account.account_id,
                        email=email,
                        code="privileged",
                        severity="info",
                        detail=f"role {account.role}",
                    )
                )
            continue

        roster_entry = roster.get(email)
        if roster_entry is not None:
            roster_status_norm = roster_entry.status.casefold()
            if roster_status_norm not in ("active", "terminated"):
                raise AccessReviewError(
                    "invalid_value", f"invalid roster status: {_truncate(roster_entry.status)}"
                )
            if roster_status_norm == "terminated" and status_norm == "active":
                detail = (
                    f"terminated {roster_entry.termination_date.isoformat()}"
                    if roster_entry.termination_date
                    else "terminated"
                )
                findings.append(
                    Finding(
                        system=account.system,
                        account_id=account.account_id,
                        email=email,
                        code="terminated_with_access",
                        severity="high",
                        detail=detail,
                    )
                )

        if status_norm == "active" and email not in roster and not is_service:
            findings.append(
                Finding(
                    system=account.system,
                    account_id=account.account_id,
                    email=email,
                    code="orphaned",
                    severity="high",
                    detail="",
                )
            )

        if account.last_login is None:
            findings.append(
                Finding(
                    system=account.system,
                    account_id=account.account_id,
                    email=email,
                    code="never_logged_in",
                    severity="low",
                    detail="",
                )
            )
        else:
            days = (today - account.last_login).days
            if days > dormant_days:
                findings.append(
                    Finding(
                        system=account.system,
                        account_id=account.account_id,
                        email=email,
                        code="dormant",
                        severity="medium",
                        detail=f"last login {account.last_login.isoformat()} ({days} days ago)",
                    )
                )

        if account.role.casefold() in privileged_norm:
            findings.append(
                Finding(
                    system=account.system,
                    account_id=account.account_id,
                    email=email,
                    code="privileged",
                    severity="info",
                    detail=f"role {account.role}",
                )
            )

    findings.sort(key=lambda f: (f.system, f.account_id, f.code))
    summary = {
        "accounts": accounts_count,
        "high": sum(1 for f in findings if f.severity == "high"),
        "medium": sum(1 for f in findings if f.severity == "medium"),
        "low": sum(1 for f in findings if f.severity == "low"),
        "info": sum(1 for f in findings if f.severity == "info"),
    }
    logger.debug("access review summary: %s", summary)
    return Report(findings=tuple(findings), summary=summary)


__all__ = [
    "AccessReviewError",
    "Account",
    "Finding",
    "Report",
    "RosterEntry",
    "__version__",
    "load_accounts",
    "load_roster",
    "review",
]
