import pytest

from services import academic_context_service


CONTEXTS = [
    {"id": 1, "course_code": "BCA", "course_name": "BCA", "academic_year": "2027-28", "semester_number": 1, "section": "A"},
    {"id": 2, "course_code": "BCA", "course_name": "BCA", "academic_year": "2027-28", "semester_number": 1, "section": "C"},
    {"id": 3, "course_code": "BCA", "course_name": "BCA", "academic_year": "2026-27", "semester_number": 2, "section": "A"},
    {"id": 4, "course_code": "MCA", "course_name": "MCA", "academic_year": "2026-27", "semester_number": 3, "section": "A"},
]


@pytest.mark.unit
def test_resolves_exact_four_level_academic_context():
    selected = academic_context_service.resolve_context(
        CONTEXTS, programme="BCA", academic_year="2027-28", semester=1, section="C",
    )
    assert selected["id"] == 2


@pytest.mark.unit
def test_changed_parent_selection_uses_valid_child_defaults():
    selected = academic_context_service.resolve_context(
        CONTEXTS, programme="MCA", academic_year="2027-28", semester=1, section="C",
    )
    assert selected["id"] == 4


@pytest.mark.unit
def test_unknown_programme_or_context_id_is_rejected():
    assert academic_context_service.resolve_context(CONTEXTS, programme="UNKNOWN") is None
    assert academic_context_service.resolve_context(CONTEXTS, semester_id=999) is None


@pytest.mark.unit
def test_selector_options_only_include_children_of_selected_context():
    options = academic_context_service.build_selector_options(CONTEXTS, CONTEXTS[1])
    assert [item["code"] for item in options["programmes"]] == ["BCA", "MCA"]
    assert options["academic_years"] == ["2027-28", "2026-27"]
    assert options["semesters"] == [1]
    assert options["sections"] == ["A", "C"]
