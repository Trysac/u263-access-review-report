# Stack

## Used

| Tool | Why |
|---|---|
| Python >= 3.10 | The code uses `X | Y` annotations and `list[str]`; `__main__.py` uses `list[str] | None`. |
| Python standard library: `csv`, `io`, `json`, `logging`, `dataclasses`, `datetime`, `typing`, `argparse`, `pathlib`, `sys` | All runtime functionality; the specification allows no runtime dependencies. |
| pytest | The test cache filename records pytest; tests are plain functions in `tests/test_access_review_report.py`. |
| `py.typed` | The package ships `src/access_review_report/py.typed`. |

## Discarded

The specification does not name discarded tools. The implementation has no runtime dependencies.
