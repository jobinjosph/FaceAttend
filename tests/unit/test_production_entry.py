import runpy
from pathlib import Path

import pytest

ENTRY = Path(__file__).resolve().parents[2] / "wsgi.py"

@pytest.mark.parametrize("secret,debug", [("short", "0"), ("replace-with-a-long-random-value-123", "0"), ("a" * 64, "1")])
def test_production_startup_rejects_unsafe_settings(monkeypatch, secret, debug):
    monkeypatch.setenv("SECRET_KEY", secret)
    monkeypatch.setenv("FLASK_DEBUG", debug)
    with pytest.raises(RuntimeError):
        runpy.run_path(str(ENTRY))

def test_production_startup_accepts_explicit_settings(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("FLASK_DEBUG", "0")
    assert runpy.run_path(str(ENTRY))["app"] is not None
