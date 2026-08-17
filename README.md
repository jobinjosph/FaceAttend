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

Authentication and face recognition are intentionally **not** included in
Phase 1. They are the next development phases.

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
  "message": "Connected to faceattend on MySQL ..."
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
- Add/edit/delete students
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
