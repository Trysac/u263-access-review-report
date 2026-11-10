"""Behavior tests for the public API of access_review_report."""

from __future__ import annotations

import pytest

import access_review_report


def test_normalize_trims_and_lowercases() -> None:
    assert access_review_report.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        access_review_report.normalize(value)


def test_version_is_semver() -> None:
    parts = access_review_report.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
