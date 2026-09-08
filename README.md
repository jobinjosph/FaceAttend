# FaceAttend — Phase 1

FaceAttend is a Flask + MySQL foundation for a period-based student attendance
system. The future face-recognition module will record student entry and exit
events for each active period.

## What already works

- Flask application factory
- Responsive FaceAttend home page
- MySQL configuration through `.env`
- Database health endpoint
- MySQL initializer
- Core database schema for:
  - courses and semesters
  - students and faculty
  - subjects and timetable periods
  - face embeddings
  - attendance sessions
  - entry/exit events
  - final attendance records
- Automated unit, component, integration and system tests
- GitHub Actions continuous testing on pushes and pull requests
- Secure email/password login with CSRF protection
- Password hashing and role-based route protection
- Admin, faculty and student dashboard foundations
- Interactive command for creating the first administrator
- Admin student management: list, add, edit, activate and deactivate
- Versioned database migrations applied safely by `init_db.py`
- A focused four-programme demo dataset (BCA, MCA, BCOM and MSW) with Semester 1–4 and Sections A–B
- Admin faculty management with linked secure Faculty Portal accounts

Face recognition is intentionally not included yet. It will be introduced only
after the academic management features are working and tested.

---

# Run the tests

Install the development dependencies inside the virtual environment:

```bash
pip install -r requirements-dev.txt
```

Run every automated test:

```bash
pytest
```

Run the tests with a coverage report:

```bash
pytest --cov=. --cov-report=term-missing
```

The automated database-health tests use a mock and do not modify the local
`faceattend` database. GitHub Actions runs the same test suite after every push
to `main` and for every pull request targeting `main`.

## Final workflow verification

Before presenting a release, run the full suite and verify these browser journeys:

1. Create or select an academic group: programme, academic year, semester and section.
2. Add subjects, assign faculty and build its timetable.
3. Generate an attendance session and complete the faculty review workflow.
4. Confirm the student attendance views and staff reports use the selected group.
5. Submit and review an attendance correction request.
6. Move or promote a student and confirm the placement history is retained.
7. Mark a student as graduated, withdrawn or archived and confirm the lifecycle history is retained.
8. Confirm non-active students cannot sign in or enter new attendance workflows.

The automated system journeys for these workflows can be run separately with:

```bash
pytest tests/system -q
```

---

# Create the first administrator

After the database has been initialized, activate the virtual environment and
run:

```bash
flask --app app create-admin
```

Enter the administrator's name, email and a password containing at least eight
characters. The password is securely hashed before it is stored. Start the
application with `python app.py`, then open `/login` to sign in.

## Manage students

Log in as an administrator and choose **Manage Students** from the Admin
Dashboard. Student register numbers are normalized, course/semester selections
are validated, and records are deactivated rather than permanently deleted.

Whenever the project receives a new database migration, run:

```bash
python init_db.py
```

Applied migrations are recorded in `schema_migrations`, so rerunning the command
is safe.

## Manage faculty

Log in as an administrator and choose **Manage Faculty**. Adding a faculty
member creates both the faculty profile and a linked `FACULTY` login account in
one database transaction. Editing the profile keeps both records synchronized.
Entering a new password while editing securely resets it; leaving it blank keeps
the current password. Activating or deactivating faculty also controls access to
the Faculty Portal.

## Manual authentication check

After automated tests pass, verify this short browser journey:

1. Open `/login` and confirm an incorrect password is rejected.
2. Log in with the administrator account and confirm the Admin Dashboard opens.
3. Confirm `/dashboard/faculty` and `/dashboard/student` return forbidden access.
4. Log out and use the browser Back button.
5. Confirm `/dashboard/admin` redirects back to `/login` after logout.

---

# Run it on macOS

## 1. Install Python 3.12 and MySQL

If Homebrew is already installed:

```bash
brew install python@3.12
brew install mysql@8.4
brew services start mysql@8.4
```

Check them:

```bash
python3.12 --version
"$(brew --prefix mysql@8.4)/bin/mysql" --version
```

Optional but recommended after a fresh MySQL installation:

```bash
"$(brew --prefix mysql@8.4)/bin/mysql_secure_installation"
```

If you set a MySQL root password, place it in `.env` later.

---

## 2. Open the project

```bash
cd FaceAttend
```

## 3. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Your Terminal prompt should now begin with `(.venv)`.

## 4. Install the Python packages

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Create your local environment file

```bash
cp .env.example .env
```

Open `.env`.

If MySQL root has no password yet:

```env
DB_USER=root
DB_PASSWORD=
```

If you created a root password:

```env
DB_USER=root
DB_PASSWORD=YOUR_PASSWORD_HERE
```

Do not commit `.env` to Git.

For a deployed HTTPS installation, generate and keep a stable random secret and
disable debug mode:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Then set the generated value and secure-cookie options in the deployment
environment:

```env
SECRET_KEY=PASTE_THE_GENERATED_VALUE_HERE
FLASK_DEBUG=0
SESSION_COOKIE_SECURE=1
```

## 6. Create the FaceAttend MySQL database

Make sure MySQL is running:

```bash
brew services start mysql@8.4
```

Then:

```bash
python init_db.py
```

Expected result:

```text
✓ Database 'faceattend' is ready.
✓ FaceAttend tables created successfully.
```

Optional demo academic data:

```bash
"$(brew --prefix mysql@8.4)/bin/mysql" -u root -p faceattend < database/seed.sql
```

If your root account has no password, omit `-p`.

## 7. Run FaceAttend

```bash
python app.py
```

You should see a local Flask address such as:

```text
http://127.0.0.1:5000
```

Open it in Safari or Chrome.

## 8. Verify the application

Application health:

```text
http://127.0.0.1:5000/health
```

Database health:

```text
http://127.0.0.1:5000/health/database
```

A successful database response should look similar to:

```json
{
  "database": "ok",
  "message": "Database connection is healthy."
}
```

---

# Folder structure

```text
FaceAttend/
├── app.py
├── config.py
├── db.py
├── init_db.py
├── requirements.txt
├── .env.example
├── .gitignore
├── routes/
│   ├── __init__.py
│   └── main.py
├── templates/
│   ├── base.html
│   └── home.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── database/
    ├── schema.sql
    └── seed.sql
```

---

# Development roadmap

## Phase 2
- Login
- roles: Admin / Faculty / Student
- password hashing
- dashboard shells

## Phase 3
- Add/edit/activate/deactivate students (complete)
- course, semester and subject management
- timetable

## Phase 4
- Webcam
- face detection only

## Phase 5
- Face registration
- face embeddings
- student recognition
- unknown-face handling

## Phase 6
- Active period attendance
- Entry Mode
- Exit Mode
- duplicate prevention
- presence duration

## Phase 7
- faculty review
- attendance calculation
- semester/month/date student dashboard
