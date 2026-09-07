from pathlib import Path

import pytest


@pytest.mark.unit
def test_demo_structure_keeps_four_active_programmes_without_hardcoding_the_app():
    sql = (
        Path(__file__).resolve().parents[2]
        / "database/migrations/019_simplify_demo_academic_structure.sql"
    ).read_text()

    assert "('BCA', 'Bachelor of Computer Applications', 4, TRUE)" in sql
    assert "('MCA', 'Master of Computer Applications', 4, TRUE)" in sql
    assert "('BCOM', 'Bachelor of Commerce', 4, TRUE)" in sql
    assert "('MSW', 'Master of Social Work', 4, TRUE)" in sql
    assert "SET is_active=FALSE" in sql
    assert "semester_number > 4" in sql
    assert "sem.section NOT IN ('A', 'B')" in sql
    assert "SELECT 'A' AS section UNION ALL SELECT 'B'" in sql
    assert "ON DUPLICATE KEY UPDATE is_active=TRUE" in sql
