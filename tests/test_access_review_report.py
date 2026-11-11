import json
from datetime import date

import pytest

from access_review_report import (
    AccessReviewError,
    Account,
    Finding,
    RosterEntry,
    load_accounts,
    load_roster,
    review,
)

# Helper functions to build CSV strings ----------


def _accounts_csv(rows: list[dict[str, str]]) -> str:
    lines = ["account_id,email,role,last_login,status"]
    for row in rows:
        lines.append(
            ",".join(
                row.get(col, "") for col in ["account_id", "email", "role", "last_login", "status"]
            )
        )
    return "\n".join(lines) + "\n"


def _roster_csv(rows: list[dict[str, str]]) -> str:
    lines = ["email,status,termination_date"]
    for row in rows:
        lines.append(",".join(row.get(col, "") for col in ["email", "status", "termination_date"]))
    return "\n".join(lines) + "\n"


# Acceptance test ---------------------------------


def test_acceptance_summary():
    accounts_csv = _accounts_csv(
        [
            {
                "account_id": "a1",
                "email": "ana@example.com",
                "role": "member",
                "last_login": "2026-08-10",
                "status": "active",
            },
            {
                "account_id": "a2",
                "email": "Bob@Example.com",
                "role": "admin",
                "last_login": "2026-11-01",
                "status": "active",
            },
            {
                "account_id": "a3",
                "email": "eve@example.com",
                "role": "member",
                "last_login": "2026-11-08",
                "status": "active",
            },
            {
                "account_id": "a4",
                "email": "ci-bot@example.com",
                "role": "member",
                "last_login": "",
                "status": "active",
            },
            {
                "account_id": "a5",
                "email": "dan@example.com",
                "role": "member",
                "last_login": "",
                "status": "active",
            },
        ]
    )
    roster_csv = _roster_csv(
        [
            {"email": "ana@example.com", "status": "active", "termination_date": ""},
            {"email": "bob@example.com", "status": "terminated", "termination_date": "2026-10-01"},
            {"email": "dan@example.com", "status": "active", "termination_date": ""},
        ]
    )
    accounts = load_accounts(accounts_csv, system="github")
    roster = load_roster(roster_csv)
    report = review(
        accounts, roster, today=date(2026, 11, 9), service_accounts={"ci-bot@example.com"}
    )
    assert report.summary == {"accounts": 5, "high": 2, "medium": 1, "low": 1, "info": 1}


def test_individual_findings():
    accounts = [
        Account(
            system="github",
            account_id="a1",
            email="ana@example.com",
            role="member",
            last_login=date(2026, 8, 10),
            status="active",
        ),
        Account(
            system="github",
            account_id="a2",
            email="bob@example.com",
            role="admin",
            last_login=date(2026, 11, 1),
            status="active",
        ),
        Account(
            system="github",
            account_id="a3",
            email="eve@example.com",
            role="member",
            last_login=date(2026, 11, 8),
            status="active",
        ),
        Account(
            system="github",
            account_id="a4",
            email="ci-bot@example.com",
            role="member",
            last_login=None,
            status="active",
        ),
        Account(
            system="github",
            account_id="a5",
            email="dan@example.com",
            role="member",
            last_login=None,
            status="active",
        ),
    ]
    roster = {
        "ana@example.com": type(
            "RosterEntry",
            (),
            {"email": "ana@example.com", "status": "active", "termination_date": None},
        )(),
        "bob@example.com": type(
            "RosterEntry",
            (),
            {
                "email": "bob@example.com",
                "status": "terminated",
                "termination_date": date(2026, 10, 1),
            },
        )(),
        "dan@example.com": type(
            "RosterEntry",
            (),
            {"email": "dan@example.com", "status": "active", "termination_date": None},
        )(),
    }
    report = review(
        accounts, roster, today=date(2026, 11, 9), service_accounts={"ci-bot@example.com"}
    )
    expected = [
        Finding(
            system="github",
            account_id="a1",
            email="ana@example.com",
            code="dormant",
            severity="medium",
            detail="last login 2026-08-10 (91 days ago)",
        ),
        Finding(
            system="github",
            account_id="a2",
            email="bob@example.com",
            code="privileged",
            severity="info",
            detail="role admin",
        ),
        Finding(
            system="github",
            account_id="a2",
            email="bob@example.com",
            code="terminated_with_access",
            severity="high",
            detail="terminated 2026-10-01",
        ),
        Finding(
            system="github",
            account_id="a3",
            email="eve@example.com",
            code="orphaned",
            severity="high",
            detail="",
        ),
        Finding(
            system="github",
            account_id="a5",
            email="dan@example.com",
            code="never_logged_in",
            severity="low",
            detail="",
        ),
    ]
    assert list(report.findings) == expected


def test_dormant_boundary_90_days():
    account_90 = Account(
        system="github",
        account_id="x",
        email="x@example.com",
        role="member",
        last_login=date(2026, 8, 11),
        status="active",
    )
    account_91 = Account(
        system="github",
        account_id="y",
        email="y@example.com",
        role="member",
        last_login=date(2026, 8, 10),
        status="active",
    )
    roster: dict = {}
    report_90 = review([account_90], roster, today=date(2026, 11, 9), dormant_days=90)
    report_91 = review([account_91], roster, today=date(2026, 11, 9), dormant_days=90)
    assert not any(f.code == "dormant" for f in report_90.findings)
    assert any(f.code == "dormant" for f in report_91.findings)


def test_csv_injection_protection():
    account = Account(
        system="sys",
        account_id="=cmd",
        email="test@example.com",
        role="member",
        last_login=None,
        status="active",
    )
    report = review([account], {}, today=date(2026, 1, 1))
    csv_out = report.to_csv()
    assert csv_out.startswith("system,account_id,email,code,severity,detail\n")
    assert "'=cmd" in csv_out

    # Test other dangerous prefixes
    for prefix in ["+", "-", "@", "\t", "\r"]:
        bad_account = Account(
            system="sys",
            account_id=prefix + "test",
            email="test@example.com",
            role="member",
            last_login=None,
            status="active",
        )
        report2 = review([bad_account], {}, today=date(2026, 1, 1))
        csv2 = report2.to_csv()
        assert "'" + prefix + "test" in csv2


def test_json_deterministic():
    account = Account(
        system="sys",
        account_id="a",
        email="a@example.com",
        role="admin",
        last_login=None,
        status="active",
    )
    report = review([account], {}, today=date(2026, 1, 1))
    json1 = report.to_json()
    json2 = report.to_json()
    assert json1 == json2
    data = json.loads(json1)
    assert "summary" in data and "findings" in data


# load_accounts error cases ------------------------


def test_load_accounts_missing_column():
    text = "account_id,role,last_login,status\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_accounts(text, system="sys")
    assert exc_info.value.code == "missing_column"
    assert exc_info.value.message == "missing column: email"


def test_load_accounts_invalid_date_row_number():
    text = "account_id,email,role,last_login,status\na1,test@example.com,member,2026-13-01,active\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_accounts(text, system="sys")
    assert exc_info.value.code == "invalid_date"
    assert "row 2" in exc_info.value.message


def test_load_accounts_input_too_large(monkeypatch):
    monkeypatch.setattr("access_review_report.MAX_INPUT_BYTES", 10)  # small for test
    text = "a" * 11
    with pytest.raises(AccessReviewError) as exc_info:
        load_accounts(text, system="sys")
    assert exc_info.value.code == "input_too_large"


def test_load_accounts_too_many_rows(monkeypatch):
    monkeypatch.setattr("access_review_report.MAX_ROWS", 3)
    rows = [
        {
            "account_id": f"a{i}",
            "email": f"u{i}@example.com",
            "role": "member",
            "last_login": "",
            "status": "active",
        }
        for i in range(4)
    ]
    text = _accounts_csv(rows)
    with pytest.raises(AccessReviewError) as exc_info:
        load_accounts(text, system="sys")
    assert exc_info.value.code == "too_many_rows"


def test_load_accounts_duplicate():
    text = _accounts_csv(
        [
            {
                "account_id": "dup",
                "email": "a@example.com",
                "role": "member",
                "last_login": "",
                "status": "active",
            },
            {
                "account_id": "dup",
                "email": "b@example.com",
                "role": "member",
                "last_login": "",
                "status": "active",
            },
        ]
    )
    with pytest.raises(AccessReviewError) as exc_info:
        load_accounts(text, system="sys")
    assert exc_info.value.code == "duplicate_account"


def test_load_accounts_truncated_row():
    text = "account_id,email,role,last_login,status\na1,test@example.com,member\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_accounts(text, system="sys")
    assert exc_info.value.code == "invalid_value"
    assert "missing field at row 2" in exc_info.value.message


def test_load_accounts_status_invalid():
    text = "account_id,email,role,last_login,status\na1,test@example.com,member,,unknown\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_accounts(text, system="sys")
    assert exc_info.value.code == "invalid_value"


def test_load_accounts_bom():
    text = "\ufeffaccount_id,email,role,last_login,status\na1,test@example.com,member,,active\n"
    accounts = load_accounts(text, system="sys")
    assert len(accounts) == 1
    assert accounts[0].account_id == "a1"


# load_roster error cases --------------------------


def test_load_roster_missing_column():
    text = "email,status\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_roster(text)
    assert exc_info.value.code == "missing_column"
    assert "termination_date" in exc_info.value.message


def test_load_roster_invalid_status():
    text = "email,status,termination_date\na@example.com,unknown,\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_roster(text)
    assert exc_info.value.code == "invalid_value"


def test_load_roster_truncated_row():
    text = "email,status,termination_date\na@example.com\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_roster(text)
    assert exc_info.value.code == "invalid_value"
    assert "missing field at row 2" in exc_info.value.message


def test_load_roster_duplicate_email():
    text = "email,status,termination_date\na@example.com,active,\na@example.com,terminated,2026-01-01\n"
    with pytest.raises(AccessReviewError) as exc_info:
        load_roster(text)
    assert exc_info.value.code == "invalid_value"


def test_load_roster_bom():
    text = "\ufeffemail,status,termination_date\na@example.com,active,\n"
    roster = load_roster(text)
    assert "a@example.com" in roster


# review validation and edge cases ----------------


def test_review_normalises_caller_built_account_email():
    accounts = [
        Account(
            system="github",
            account_id="a2",
            email="Bob@Example.com",
            role="admin",
            last_login=date(2026, 11, 1),
            status="active",
        )
    ]
    roster = {
        "bob@example.com": RosterEntry(
            email="bob@example.com",
            status="terminated",
            termination_date=date(2026, 10, 1),
        )
    }
    report = review(accounts, roster, today=date(2026, 11, 9))
    terminated = [f for f in report.findings if f.code == "terminated_with_access"]
    assert len(terminated) == 1
    assert terminated[0].email == "bob@example.com"
    assert terminated[0].detail == "terminated 2026-10-01"
    assert not any(f.code == "orphaned" for f in report.findings)


def test_review_normalises_caller_built_service_account_email():
    account = Account(
        system="sys",
        account_id="svc",
        email="  SVC@Example.com  ",
        role="member",
        last_login=None,
        status="active",
    )
    report = review([account], {}, today=date(2026, 1, 1), service_accounts={"svc@example.com"})
    assert report.findings == ()


def test_review_invalid_account_status():
    account = Account(
        system="sys",
        account_id="a",
        email="a@example.com",
        role="member",
        last_login=None,
        status="unknown",
    )
    with pytest.raises(AccessReviewError) as exc_info:
        review([account], {}, today=date(2026, 1, 1))
    assert exc_info.value.code == "invalid_value"


def test_review_invalid_roster_status():
    account = Account(
        system="sys",
        account_id="a",
        email="a@example.com",
        role="member",
        last_login=None,
        status="active",
    )
    roster = {
        "a@example.com": type(
            "RosterEntry",
            (),
            {"email": "a@example.com", "status": "unknown", "termination_date": None},
        )()
    }
    with pytest.raises(AccessReviewError) as exc_info:
        review([account], roster, today=date(2026, 1, 1))
    assert exc_info.value.code == "invalid_value"


def test_review_dormant_days_negative():
    with pytest.raises(AccessReviewError) as exc_info:
        review([], {}, today=date(2026, 1, 1), dormant_days=-1)
    assert exc_info.value.code == "invalid_value"


def test_disabled_account_no_findings():
    account = Account(
        system="sys",
        account_id="a",
        email="a@example.com",
        role="admin",
        last_login=None,
        status="disabled",
    )
    roster = {
        "a@example.com": type(
            "RosterEntry",
            (),
            {
                "email": "a@example.com",
                "status": "terminated",
                "termination_date": date(2026, 1, 1),
            },
        )()
    }
    report = review([account], roster, today=date(2026, 1, 1))
    assert report.findings == ()
    assert report.summary["high"] == 0 and report.summary["info"] == 0


def test_service_account_only_privileged():
    account = Account(
        system="sys",
        account_id="svc",
        email="svc@example.com",
        role="admin",
        last_login=None,
        status="active",
    )
    report = review([account], {}, today=date(2026, 1, 1), service_accounts={"svc@example.com"})
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.code == "privileged"
    assert finding.severity == "info"
    assert finding.detail == "role admin"


def test_dormant_days_zero():
    yesterday = date(2026, 1, 1)
    account = Account(
        system="sys",
        account_id="a",
        email="a@example.com",
        role="member",
        last_login=yesterday,
        status="active",
    )
    today = date(2026, 1, 2)
    report = review([account], {}, today=today, dormant_days=0)
    assert any(f.code == "dormant" for f in report.findings)


def test_email_normalization_casefold():
    accounts_csv = _accounts_csv(
        [
            {
                "account_id": "a1",
                "email": "  Bob@Example.com  ",
                "role": "member",
                "last_login": "",
                "status": "active",
            },
        ]
    )
    accounts = load_accounts(accounts_csv, system="sys")
    assert accounts[0].email == "bob@example.com"
    roster_csv = _roster_csv(
        [
            {"email": "BOB@example.com", "status": "terminated", "termination_date": "2026-01-01"},
        ]
    )
    roster = load_roster(roster_csv)
    assert "bob@example.com" in roster
    report = review(accounts, roster, today=date(2026, 2, 1), service_accounts=set())
    assert any(f.code == "terminated_with_access" for f in report.findings)


# CLI tests ---------------------------------------


def _write_file(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_cli_high_findings_returns_1(tmp_path, capsys):
    acc_path = _write_file(
        tmp_path,
        "acc.csv",
        "account_id,email,role,last_login,status\na1,terminated@example.com,member,,active\n",
    )
    rost_path = _write_file(
        tmp_path,
        "rost.csv",
        "email,status,termination_date\nterminated@example.com,terminated,2026-01-01\n",
    )
    args = [
        "--accounts",
        f"sys={acc_path}",
        "--roster",
        rost_path,
        "--today",
        "2026-02-01",
        "--format",
        "csv",
    ]
    from access_review_report.__main__ import main

    ret = main(args)
    captured = capsys.readouterr()
    assert ret == 1
    assert "terminated_with_access" in captured.out


def test_cli_no_high_returns_0(tmp_path, capsys):
    acc_path = _write_file(
        tmp_path,
        "acc.csv",
        "account_id,email,role,last_login,status\na1,active@example.com,member,,active\n",
    )
    rost_path = _write_file(
        tmp_path, "rost.csv", "email,status,termination_date\nactive@example.com,active,\n"
    )
    args = [
        "--accounts",
        f"sys={acc_path}",
        "--roster",
        rost_path,
        "--today",
        "2026-02-01",
        "--format",
        "csv",
    ]
    from access_review_report.__main__ import main

    ret = main(args)
    captured = capsys.readouterr()
    assert ret == 0
    assert captured.out


def test_cli_missing_today_returns_2(capsys):
    from access_review_report.__main__ import main

    ret = main(["--accounts", "sys=acc.csv", "--roster", "rost.csv"])
    captured = capsys.readouterr()
    assert ret == 2
    assert "--today" in captured.err


def test_cli_invalid_file_returns_2(tmp_path, capsys):
    from access_review_report.__main__ import main

    args = ["--accounts", "sys=nonexistent.csv", "--roster", "rost.csv", "--today", "2026-02-01"]
    ret = main(args)
    captured = capsys.readouterr()
    assert ret == 2
    assert "cannot read" in captured.err


def test_cli_non_utf8_file_returns_2(tmp_path, capsys):
    from access_review_report.__main__ import main

    acc_path = tmp_path / "acc.csv"
    acc_path.write_bytes(
        b"account_id,email,role,last_login,status\na1,\xff@example.com,member,,active\n"
    )
    rost_path = _write_file(tmp_path, "rost.csv", "email,status,termination_date\n")
    ret = main(
        [
            "--accounts",
            f"sys={acc_path}",
            "--roster",
            rost_path,
            "--today",
            "2026-02-01",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 2
    assert "cannot read" in captured.err


# Acceptance literals and additional edge cases ----------------


def test_acceptance_roster_literal():
    roster = load_roster(
        "email,status,termination_date\nana@example.com,active,\nbob@example.com,terminated,2026-10-01\ndan@example.com,active,\n"
    )
    assert set(roster) == {"ana@example.com", "bob@example.com", "dan@example.com"}
    assert roster["bob@example.com"].status == "terminated"
    assert roster["bob@example.com"].termination_date == date(2026, 10, 1)
    assert roster["ana@example.com"].termination_date is None


def test_dormant_boundary_literal_date():
    accounts = load_accounts(
        "account_id,email,role,last_login,status\na1,ana@example.com,member,2026-08-11,active\n",
        system="github",
    )
    assert accounts[0].last_login == date.fromisoformat("2026-08-11")
    roster = load_roster("email,status,termination_date\nana@example.com,active,\n")
    report = review(accounts, roster, today=date.fromisoformat("2026-11-09"))
    assert not any(f.code == "dormant" for f in report.findings)


def test_same_email_in_two_systems():
    accounts = load_accounts(
        "account_id,email,role,last_login,status\nx1,dup@example.com,member,,active\n",
        system="github",
    ) + load_accounts(
        "account_id,email,role,last_login,status\nx1,dup@example.com,member,,active\n",
        system="gitlab",
    )
    roster = load_roster("email,status,termination_date\ndup@example.com,terminated,2026-01-01\n")
    report = review(accounts, roster, today=date(2026, 2, 1))
    terminated = [f for f in report.findings if f.code == "terminated_with_access"]
    assert len(terminated) == 2
    assert {f.system for f in terminated} == {"github", "gitlab"}


def test_cli_acceptance_literal_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "acc.csv").write_text(
        "account_id,email,role,last_login,status\na1,leaver@example.com,member,2026-11-01,active\n",
        encoding="utf-8",
    )
    (tmp_path / "hr.csv").write_text(
        "email,status,termination_date\nleaver@example.com,terminated,2026-10-01\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    from access_review_report.__main__ import main

    ret = main(
        [
            "--accounts",
            "github=acc.csv",
            "--roster",
            "hr.csv",
            "--today",
            "2026-11-09",
            "--format",
            "csv",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 1
    assert captured.out.startswith("system,account_id,email,code,severity,detail")
    assert "terminated_with_access" in captured.out
