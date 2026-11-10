# access-review-report

[![PyPI version](https://img.shields.io/pypi/v/trysac-access-review-report)](https://pypi.org/project/trysac-access-review-report/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-access-review-report)](LICENSE)
[![CI](https://github.com/Trysac/u263-access-review-report/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u263-access-review-report/actions/workflows/ci.yml)

Build periodic access review reports from system account exports and an HR roster: terminated users with access, orphaned, dormant and never-used accounts, and privileged roles

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-access-review-report
# or
uv add trysac-access-review-report
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import access_review_report

# normalize() trims surrounding whitespace and lower-cases the text.
print(access_review_report.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    access_review_report.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
