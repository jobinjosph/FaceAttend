from pathlib import Path

import pytest


@pytest.mark.unit
def test_sface_upgrade_preserves_legacy_embeddings_and_updates_registration_flag():
    migration = (
        Path(__file__).parents[2]
        / "database"
        / "migrations"
        / "013_upgrade_face_embeddings_to_sface.sql"
    ).read_text(encoding="utf-8")

    assert "opencv-yunet-sface-v1" in migration
    assert "face_registered" in migration
    assert "DELETE FROM FACE_EMBEDDINGS" not in migration.upper()
