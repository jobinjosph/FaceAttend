import pytest

from services.csv_service import safe_cell, safe_row


@pytest.mark.unit
@pytest.mark.parametrize("value", ["=1+1", "+SUM(A1:A2)", "-2+3", "@command", "\tformula"])
def test_spreadsheet_formulas_are_escaped(value):
    assert safe_cell(value) == "'" + value


@pytest.mark.unit
def test_normal_csv_values_are_unchanged_and_none_is_empty():
    assert safe_row(["Student Name", 12, None]) == ["Student Name", "12", ""]
