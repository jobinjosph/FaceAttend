"""Production entry point: gunicorn --config gunicorn.conf.py wsgi:app."""
import os
from dotenv import load_dotenv

load_dotenv()
secret = os.getenv("SECRET_KEY", "")
if len(secret) < 32 or secret.startswith(("replace-", "PASTE_")):
    raise RuntimeError("Set SECRET_KEY to a stable random value of at least 32 characters.")
if os.getenv("FLASK_DEBUG", "0") != "0":
    raise RuntimeError("Set FLASK_DEBUG=0 for production startup.")

from app import app
