"""Tests for PeriodExpression parsing and error handling."""

import pytest

from metadata_ingestion_framework.models import PeriodExpression, PeriodUnit


@pytest.mark.parametrize(
    ("raw", "amount", "unit"),
    [
        ("3 days", 3, PeriodUnit.DAY),
        ("1 day", 1, PeriodUnit.DAY),
        ("3 hrs", 3, PeriodUnit.HOUR),
        ("2 hours", 2, PeriodUnit.HOUR),
        ("5 months", 5, PeriodUnit.MONTH),
        ("1 year", 1, PeriodUnit.CALENDAR_YEAR),
        ("2 calendar years", 2, PeriodUnit.CALENDAR_YEAR),
        ("1 calendar year", 1, PeriodUnit.CALENDAR_YEAR),
    ],
)
def test_parse_valid(raw: str, amount: int, unit: PeriodUnit) -> None:
    assert PeriodExpression.parse(raw) == PeriodExpression(amount=amount, unit=unit)


@pytest.mark.parametrize("raw", ["", "days", "1.5 days", "2 yrs", "3 parsecs", "abc"])
def test_parse_invalid_raises(raw: str) -> None:
    with pytest.raises(ValueError):
        PeriodExpression.parse(raw)


def test_parse_unparseable_expression_message() -> None:
    with pytest.raises(ValueError, match="Invalid period expression"):
        PeriodExpression.parse("3 fortnights")
