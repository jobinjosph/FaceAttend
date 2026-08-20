from pathlib import Path

import pytest


@pytest.mark.unit
def test_face_attendance_client_scans_repeatedly_without_student_clicks():
    script = (
        Path(__file__).parents[2] / "static" / "js" / "face_attendance.js"
    ).read_text(encoding="utf-8")

    assert "scheduleScan" in script
    assert "window.setTimeout(scan" in script
    assert 'data.result === "matched"' in script
    assert "Next student may approach" in script
    assert "recognize-student" not in script


@pytest.mark.unit
def test_continuous_camera_has_a_lecturer_stop_control():
    script = (
        Path(__file__).parents[2] / "static" / "js" / "face_attendance.js"
    ).read_text(encoding="utf-8")

    assert "stopCamera" in script
    assert "Stop attendance camera" in script
    assert "beforeunload" in script
