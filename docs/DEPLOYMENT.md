# Deployment guide

Use Python 3.12 and MySQL 8.4 on Linux or macOS. Run commands from the repository with its virtual environment activated.

```sh
pip install -r requirements-production.txt
```

Set DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD for the target database. Use a dedicated runtime database account; schema migrations require a separate account with schema-changing privileges. Keep credentials outside Git.

Generate a stable session key using `python -c 'import secrets; print(secrets.token_hex(32))'`, place it in SECRET_KEY, and set FLASK_DEBUG=0. Set SESSION_COOKIE_SECURE=1 when serving through HTTPS. For a localhost HTTP rehearsal use SESSION_COOKIE_SECURE=0. All workers must share the same secret.

Before changing an existing database, take a backup (the command prompts for the database password):

```sh
mysqldump -h 127.0.0.1 -u root -p --single-transaction faceattend > faceattend-before-release.sql
python init_db.py
```

Substitute the configured host, account and database. Keep the backup outside the repository. Existing migrations include historical demo seeds; review these before targeting a real college database. Rehearse migrations against a separate database first. Do not rerun database/seed.sql as a release step.

For a new installation, create an administrator:

```sh
flask --app app create-admin
```

Start the production server:

```sh
gunicorn --config gunicorn.conf.py wsgi:app
```

The server listens on localhost:8000. Configure your host's HTTPS reverse proxy to forward to that address; allow at least the application's 8 MB upload limit. Camera access on a remote domain requires HTTPS and browser permission. Keep models/face and its licence files with the release. Configure your host's process manager to restart Gunicorn after reboot and preserve logs. Domain, TLS and process-manager configuration depend on the deployment host and must be completed there.

Check /health and /health/database, then follow DEMO.md. These endpoints verify process/database availability, not face recognition or complete user workflows. If a release fails, stop traffic, retain logs and use the previous code version; restore a verified backup only after checking schema compatibility and accounting for any newer records.

Configuration reference: https://docs.gunicorn.org/en/stable/settings.html
