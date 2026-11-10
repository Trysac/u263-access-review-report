import argparse
import sys
from datetime import date
from pathlib import Path

import access_review_report as _core

from . import AccessReviewError, load_accounts, load_roster, review


def _read_file(path: Path) -> str:
    """Read a file as UTF-8 text, rejecting oversized input before decoding."""
    limit = _core.MAX_INPUT_BYTES
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise AccessReviewError("input_too_large", f"input exceeds {limit} bytes")
    return data.decode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate access review report from account exports and an HR roster."
    )
    parser.add_argument(
        "--accounts",
        action="append",
        required=True,
        help="SYSTEM=PATH to an accounts CSV; repeatable.",
    )
    parser.add_argument("--roster", required=True, help="Path to roster CSV.")
    parser.add_argument("--today", required=True, help="Report date YYYY-MM-DD.")
    parser.add_argument(
        "--dormant-days",
        type=int,
        default=90,
        help="Days after last login to consider dormant (default 90).",
    )
    parser.add_argument(
        "--service-accounts", help="Path to a file with one service account email per line."
    )
    parser.add_argument(
        "--format", choices=["csv", "json"], default="csv", help="Output format (default csv)."
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2

    try:
        today = date.fromisoformat(args.today)
    except ValueError:
        print(f"error: invalid date: {args.today}", file=sys.stderr)
        return 2

    if args.dormant_days < 0:
        print("error: --dormant-days must be non-negative", file=sys.stderr)
        return 2

    accounts_list = []
    for spec in args.accounts:
        if "=" not in spec:
            print(f"error: --accounts must be SYSTEM=PATH, got '{spec}'", file=sys.stderr)
            return 2
        system, path_str = spec.split("=", 1)
        if not system or not path_str:
            print(f"error: --accounts must be SYSTEM=PATH, got '{spec}'", file=sys.stderr)
            return 2
        try:
            text = _read_file(Path(path_str))
            accounts = load_accounts(text, system=system)
            accounts_list.extend(accounts)
        except AccessReviewError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except (OSError, UnicodeDecodeError) as e:
            print(f"error: cannot read {path_str}: {e}", file=sys.stderr)
            return 2

    try:
        roster_text = _read_file(Path(args.roster))
        roster = load_roster(roster_text)
    except AccessReviewError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: cannot read {args.roster}: {e}", file=sys.stderr)
        return 2

    service_accounts = set()
    if args.service_accounts:
        try:
            lines = _read_file(Path(args.service_accounts)).splitlines()
            service_accounts = {line.strip() for line in lines if line.strip()}
        except AccessReviewError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except (OSError, UnicodeDecodeError) as e:
            print(f"error: cannot read {args.service_accounts}: {e}", file=sys.stderr)
            return 2

    report = review(
        accounts_list,
        roster,
        today=today,
        dormant_days=args.dormant_days,
        service_accounts=service_accounts,
    )
    if args.format == "json":
        print(report.to_json())
    else:
        print(report.to_csv(), end="")
    return 1 if report.summary["high"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
