# FACEATTEND: SMART STUDENT ATTENDANCE SYSTEM

Project report submitted in partial fulfilment of the requirements for **[degree / course name]**

Submitted by: **[student name]**  
Register number: **[register number]**  
Guide: **[guide name and designation]**  
Department: **[department name]**  
Institution: **[institution name]**  
Academic year: **[academic year]**  
Submission date: **[date]**

\pagebreak

# CERTIFICATE

This is to certify that the project entitled **“FaceAttend: Smart Student Attendance System”** is a bona fide work carried out by **[student name]**, register number **[register number]**, under the guidance of **[guide name]** during the academic year **[academic year]**. The report is submitted in partial fulfilment of the requirements for **[degree / course name]**.

Project guide: ____________________    Head of department: ____________________

External examiner: ____________________    Date and place: ____________________

> Replace this draft wording with the certificate text prescribed by your department and obtain the required signatures.

\pagebreak

# ACKNOWLEDGMENT

I thank **[guide name]**, **[department]**, and **[institution]** for guidance and support during the development of FaceAttend. I also thank the people who helped review the interface and test the academic workflows. Any camera-based demonstration should use consenting volunteers. I remain responsible for the design, implementation, testing and conclusions presented in this report.

\pagebreak

# ABSTRACT

FaceAttend is a web-based student attendance system developed with Flask, MySQL, JavaScript and OpenCV. It supports three roles. Administrators maintain programmes, academic groups, students, faculty, subjects, assignments and timetables; generate dated class sessions; and review attendance reports and correction requests. Faculty members start a scheduled session, record entry and exit by face recognition or a manual fallback, review every student's status, and confirm the final attendance record. Students see only their confirmed attendance, filter it by semester, month, date and subject, download CSV or PDF reports, and request corrections.

The system uses OpenCV YuNet for face detection and SFace for numerical face descriptors. It stores descriptors rather than relying on a raw image gallery for matching. Authentication, role checks, CSRF protection and server-side ownership checks protect the main workflows. The database retains attendance events, final records, correction decisions, and student placement/lifecycle history. Automated tests cover isolated components and complete route journeys; physical-camera, real-database and multi-user deployment checks remain separate acceptance work. Face recognition assists attendance capture, but faculty confirmation remains the authoritative step.

Keywords: attendance management; face recognition; Flask; MySQL; academic portal.

\pagebreak

# TABLE OF CONTENTS

| Chapter | Title | Page no. |
| --- | --- | --- |
| — | Abstract | Update after final pagination |
| — | List of Tables | Update after final pagination |
| — | List of Figures | Update after final pagination |
| 1 | Introduction | Update after final pagination |
| 2 | System Study | Update after final pagination |
| 3 | System Configuration | Update after final pagination |
| 4 | Software Description | Update after final pagination |
| 5 | System Design | Update after final pagination |
| 6 | Source Code | Update after final pagination |
| 7 | System Testing | Update after final pagination |
| 8 | System Implementation / Deployment | Update after final pagination |
| 9 | Conclusion and Future Enhancement | Update after final pagination |
| 10 | Appendices | Update after final pagination |
| 11 | References / Bibliography | Update after final pagination |

Page numbers are intentionally left for the final Word/PDF layout because signatures and replacement screenshots alter pagination.

# LIST OF TABLES

| Number | Caption |
| --- | --- |
| Table 1.1 | FaceAttend modules and responsibilities |
| Table 3.1 | Software configuration |
| Table 5.1 | Input validation summary |
| Table 5.2 | Principal database entities |
| Table 7.1 | Representative test cases |

# LIST OF FIGURES

| Number | Caption |
| --- | --- |
| Figure 2.1 | FaceAttend use case diagram |
| Figure 2.2 | Attendance confirmation sequence diagram |
| Figure 2.3 | Attendance activity diagram |
| Figure 5.1 | Three-layer system architecture |
| Figure 10.1 | Faculty dashboard screenshot supplied by project owner |

\pagebreak

# 1. INTRODUCTION

## 1.1 Problem Statement

Period-based attendance is difficult to manage when student details, class schedules, entry/exit evidence and final decisions are handled in separate records. Manual marking consumes class time and can produce omissions or disputed status changes. A face-matching result alone is not sufficient evidence of attendance because lighting, camera quality, pose and spoofing can affect it. The project therefore needs a controlled academic workflow that combines camera-assisted capture, a manual fallback, faculty review, student visibility and an auditable correction process.

## 1.2 Project Description and Modules

FaceAttend is a Flask web application whose pages are rendered with HTML templates and styled with CSS. Browser JavaScript handles interaction and camera capture. Flask routes validate requests and call service functions; MySQL stores academic, identity and attendance data. Table 1.1 summarizes the implemented modules.

Table 1.1: FaceAttend modules and responsibilities

| Module | Main responsibility |
| --- | --- |
| Authentication | Email/password login, password hashes, role-based dashboard routing and logout. |
| Academic setup | Programmes, academic years, semesters, sections and subjects. |
| People management | Student and faculty accounts, active status, placements and lifecycle history. |
| Teaching setup | Faculty-subject assignment and conflict-checked weekly timetable. |
| Face enrolment | Capture three face samples and store an averaged SFace descriptor. |
| Attendance sessions | Generate dated classes; faculty start, end, review and confirm them. |
| Attendance capture | Recognize an enrolled face for entry/exit; provide manual roster marking. |
| Reports | Student and staff filters, percentages, CSV and PDF export. |
| Corrections | Student request, faculty/admin decision and recorded audit details. |

The intended workflow is administrative setup → session generation → faculty capture and review → confirmation → student/staff reporting → correction if needed. The system is an academic demonstration, not a certified biometric security product.

\pagebreak

# 2. SYSTEM STUDY

## 2.1 Existing System

The baseline considered for this project is a manual or spreadsheet-based attendance process. It can record a final present/absent status, but it does not inherently link that status to a dated timetable period, capture entry and exit events, enforce role-specific access, or keep a structured approval trail for corrections. This is a comparison model, not a claim about a particular institution's existing software.

## 2.2 Proposed System

The proposed system centralizes programme and class configuration, account management, attendance capture and reporting. Administrators configure the academic structure and prepare students for enrolment. Faculty members control their own sessions and confirm the final roster. Students can inspect confirmed attendance and submit correction requests. Attendance results are restricted to the student's own records or to an authorized faculty/admin scope. A camera mismatch or unusable image does not prevent an authorized faculty member from using manual marking.

## 2.3 Use Case Diagram

The system boundary and actor actions are shown in Figure 2.1. “Recognize face” is part of the attendance-capture workflow; the faculty member still reviews and confirms the outcome.

```
          ADMIN                 FACEATTEND SYSTEM                    FACULTY
             |                         |                                |
             +----> Manage academic setup, students, faculty <---------+
             +----> Assign faculty and manage timetable                |
             +----> Generate attendance sessions                        |
             |       Register student faces <---------------------------+
             |                         |                                +----> Start/end own session
             |                         +<------ Record entry/exit <-----+
             |                         +<------ Review/confirm <--------+
             +----> View reports <-----+-----------------------> View own class reports
             +----> Review corrections +<---------------------- Review assigned corrections
                                       |
          STUDENT ---------------------+----> Log in; view own confirmed report
                   -------------------+----> Request/track correction
```

Figure 2.1: FaceAttend use case diagram (actor-to-function view)

All three actors log in. An administrator may review corrections across the selected academic context; faculty review only requests for their assigned classes; students cannot approve requests.

## 2.4 Sequential Diagram

Figure 2.2 describes the principal attendance sequence. It separates a camera event from the final attendance decision.

```
Admin          Browser/Flask          Services/OpenCV          MySQL          Faculty          Student
  | create timetable/session |             |                   |               |                 |
  +-------------------------> | ----------> | ----------------> |               |                 |
  |                           |             |                   |               |                 |
  |                           | <----------- start session ----+<--------------+
  |                           |             | ---- roster ----> |               |
  |                           | <---- face sample / manual ----+<--------------+
  |                           | ----------> | match/log event ->|               |
  |                           | <----------- review roster ----+<--------------+
  |                           | ----------> | confirm status -->|               |
  |                           | <---------------- report ------+---------------->+
```

Figure 2.2: Attendance confirmation sequence diagram

## 2.5 Activity Diagram

The state changes shown in Figure 2.3 correspond to the implemented session lifecycle. If a class is not conducted it can be marked accordingly; otherwise unmarked students must be resolved before confirmation.

```
Start → Select academic group/date → Generate scheduled session
  → Faculty starts session → Active session
  → Capture entry/exit by face OR mark manually
  → Faculty ends session → Review roster
  → Any NOT_MARKED records? ── Yes → Resolve each status → Review roster
                         └─ No  → Confirm attendance
  → Student/staff view report → Optional student correction request
  → Authorized review → Approve and update record OR reject → End
```

Figure 2.3: Attendance activity diagram

\pagebreak

# 3. SYSTEM CONFIGURATION

## 3.1 Hardware Configuration

FaceAttend can be developed on a standard laptop or desktop computer with a working webcam. The repository does not specify a measured minimum CPU, RAM or storage requirement, so none is claimed here. A local evaluation should record the actual machine specification, camera resolution, lighting conditions and browser used: **[enter measured test setup]**. For a multi-user deployment, server sizing and camera compatibility require performance testing with the intended number of classes and users.

## 3.2 Software Configuration

Table 3.1 lists the principal stack and the versions recommended or constrained by the repository. These are project configuration values, not claims about a machine on which this document was prepared.

Table 3.1: Software configuration

| Component | Project use / version |
| --- | --- |
| Python | 3.12 in the repository's macOS and deployment guides |
| Flask | 3.1 or later, below 4 |
| Flask-WTF | CSRF protection, version 1.2 or later, below 2 |
| MySQL | 8.4 in deployment guide; mysql-connector-python 9.x |
| OpenCV | opencv-python-headless 4.10 or later, below 5; YuNet and SFace ONNX models |
| NumPy | Numerical descriptor handling, version 2.x |
| Front end | HTML/Jinja templates, CSS and browser JavaScript |
| Test tools | pytest 8.x and pytest-cov 5–6.x |
| Production server | Gunicorn 23.x; HTTPS reverse proxy is a deployment responsibility |

The runtime values come from `requirements.txt`, `requirements-dev.txt`, `requirements-production.txt`, `config.py` and the deployment guide.

\pagebreak

# 4. SOFTWARE DESCRIPTION

## 4.1 Overview of Front End

The public home page introduces the attendance workflow. A common navigation bar and role-aware header lead to one login form and the appropriate Admin, Faculty or Student dashboard after authentication. Dashboard cards link to functions permitted for that role. Forms capture academic choices, student/faculty details, timetable periods and correction reasons. Browser JavaScript requests camera access for enrolment and attendance capture and sends image samples to Flask routes. Camera permission and a secure context are necessary on a remote host; a user should be informed and consenting before enrolment.

Admin screens manage academic structure, students, faculty, subjects, assignments, timetable, sessions, reports and corrections. Faculty screens show assigned sessions, a roster for manual review, face attendance, reports and corrections. Student screens show confirmed report views and correction history. The design remains responsive for narrow screens; user-facing errors appear when validation or access checks fail.

## 4.2 Overview of Back End

`app.py` creates the Flask application and registers route blueprints. `config.py` reads environment-based secrets and database connection settings. Authentication uses password hashes, a signed session and role guards; CSRF protection covers state-changing forms. Route functions handle HTTP input and call service modules. Services implement validation, transactions, reporting and face descriptor comparison. `db.py` opens MySQL connections. `init_db.py` creates the database schema and tracks versioned migrations in `schema_migrations`.

OpenCV YuNet finds the face and SFace produces a descriptor from an aligned crop. Three enrolled samples are averaged into a normalized descriptor. Recognition compares descriptors with cosine similarity. The code rejects missing, multiple, too-small or blurry faces and oversized/invalid sample data. The threshold is configured in `services/face_service.py`; it has not been calibrated on a representative population for production use. A positive match records a camera event, while faculty review determines the final attendance status.

\pagebreak

# 5. SYSTEM DESIGN

## 5.1 Architectural Design

Figure 5.1 shows the separation of browser, application and storage concerns.

```
  Browser (HTML/CSS/JavaScript; webcam)
                 |
                 | HTTPS for remote camera access
                 v
  Flask blueprints + authentication/role/CSRF guards
                 |
                 v
  Services: academic setup | sessions | OpenCV match | reports | corrections
                 |
                 v
  MySQL: users + academic data + face embeddings + events + final records
```

Figure 5.1: Three-layer system architecture

The browser never receives raw database credentials. All final report queries are restricted to confirmed sessions. Protected role routes and service-level scope checks are both necessary because hiding a dashboard link is not an authorization control.

## 5.2 Input Design

Table 5.1 identifies representative input controls. Client-side validation aids the user; server-side checks are authoritative.

Table 5.1: Input validation summary

| Input | Validation / handling |
| --- | --- |
| Login | Email and password required; hashed-password verification; inactive accounts rejected. |
| Academic group | Programme, year, semester and section resolved to an active group. |
| Timetable | Day, period, time, subject and faculty checked; conflicting periods rejected. |
| Student face | Exactly three samples; single face, size, blur and image-size limits. |
| Attendance event | Session must be valid and owned by the faculty member; duplicate entry/exit handling. |
| Faculty roster | Only allowed attendance statuses; unmarked records must be resolved before confirmation. |
| Correction request | Confirmed record, requested status and reason required; one request per record. |

## 5.3 Output Design

After confirmation, the student report provides semester, month and exact-date views with subject filtering, class counts, status details and an attendance percentage. Staff reports cover authorized classes or selected academic groups. CSV and text-based PDF exports support record sharing. Correction history displays the request status and review decision. Error messages and HTTP statuses distinguish missing data, invalid input, unavailable database and forbidden access. Report percentages derive from confirmed records, not from an unreviewed face event.

## 5.4 Database Design

Table 5.2 summarizes the principal entities from `database/schema.sql` and subsequent migrations. Primary keys are numerical IDs; foreign keys join users, academic groups, sessions and attendance records. Unique constraints guard email, register number, one final attendance record per student/session and one correction request per record.

Table 5.2: Principal database entities

| Entity | Key purpose and relationships |
| --- | --- |
| `users` | Name, email, password hash, role and active flag; linked to student/faculty profile. |
| `courses`, `semesters` | Programme and academic group (year/semester/section). |
| `students`, `faculty` | People and their portal links; students belong to an academic group. |
| `student_placement_history`, `student_lifecycle_history` | Audit of movement and active/graduated/withdrawn/archived status. |
| `subjects`, `faculty_subject_assignments`, `timetable_periods` | Teaching setup and assigned weekly periods. |
| `face_embeddings` | Model identifier and numerical descriptor for an enrolled student. |
| `attendance_sessions` | Dated period, subject, faculty and lifecycle status. |
| `attendance_events` | Entry/exit timestamps, source and optional match score. |
| `attendance_records` | Final per-student status, duration, marking method and override. |
| `attendance_correction_requests` | Requested change, reason, reviewer, decision and timestamps. |

The main relationship is programme → academic group → subject/timetable → dated session → attendance event and attendance record → optional correction. Transactional updates and foreign keys help keep related changes consistent. Production retention and deletion policy remains to be defined by the institution.

\pagebreak

# 6. SOURCE CODE

This chapter documents short, representative excerpts rather than copying the full repository. The complete implementation is organized under `routes/`, `services/`, `templates/`, `static/`, `database/` and `tests/`.

## 6.1 Application Factory and Role Routes

```python
def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    csrf.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    # Other functional blueprints are registered here.
    return app
```

The actual `app.py` registers the full set of admin, faculty, student, report and correction blueprints, as well as security headers and a database error handler. `routes/dashboard.py` restricts `/dashboard/admin`, `/dashboard/faculty` and `/dashboard/student` to their matching roles.

## 6.2 Session Generation and Faculty Review

```python
# Representative logic from services/session_service.py
if current["status"] != "SCHEDULED":
    return "invalid_status"
cursor.execute(
    "UPDATE attendance_sessions SET status='ACTIVE', started_at=NOW() WHERE id=%s",
    (session_id,),
)
```

When the faculty member starts a session, the service creates `NOT_MARKED` roster records for active students in that academic group. The lifecycle is `SCHEDULED → ACTIVE → REVIEW → CONFIRMED`, or `NOT_CONDUCTED` where applicable. Confirmation is blocked if unmarked records remain.

## 6.3 Face Matching

```python
def is_match(first, second, threshold=COSINE_MATCH_THRESHOLD):
    return cosine_similarity(first, second) >= threshold
```

The full service validates image data, detects and aligns a single face, computes SFace descriptors and compares them with the stored enrolment descriptor. The match is evidence for an event, not a replacement for faculty confirmation. `services/face_service.py` contains the exact threshold and capture-quality checks.

## 6.4 Corrections and Exports

`routes/correction_requests.py` accepts student submissions and authorizes admin/faculty review. `services/correction_service.py` validates eligibility and saves the decision and reviewer details. `services/report_service.py` constructs filtered reports; `services/csv_service.py` and `services/pdf_service.py` generate downloads. See the repository for complete source; excerpts here are illustrative and intentionally omit surrounding error handling.

\pagebreak

# 7. SYSTEM TESTING

## 7.1 Test Cases

Automated tests use pytest across unit, component, integration and system directories. Many tests mock MySQL calls or face-recognition responses; passing them does not certify a physical-camera or production installation. Table 7.1 contains representative scenarios. “Automated” means the repository contains a corresponding test journey; “Manual pending” means an operator must record a real browser result.

Table 7.1: Representative test cases

| ID | Scenario | Expected outcome | Evidence category |
| --- | --- | --- | --- |
| T01 | Incorrect login | Access denied without session | Automated auth/system |
| T02 | Admin opens faculty/student dashboard | Forbidden by role guard | Automated auth/system |
| T03 | Admin creates student and faculty | Validated profiles and linked accounts | Automated system |
| T04 | Admin configures subject, assignment and timetable | Valid group and conflict handling | Automated system |
| T05 | Faculty starts own scheduled session | Active session and roster created | Automated system |
| T06 | Enrolled face records entry/exit | Recognized event associated with session | Automated with mocked camera/model paths |
| T07 | Faculty confirms reviewed roster | No unresolved `NOT_MARKED` entries | Automated system |
| T08 | Student opens report | Only own confirmed records visible | Automated system |
| T09 | Student requests correction; reviewer decides | Decision retained and approved record updated | Automated system |
| T10 | Real webcam in chosen browser | Consent, capture, match and manual fallback work | Manual pending |
| T11 | CSV/PDF exports open correctly | Files match filtered report | Manual pending |
| T12 | Multiple users and database recovery | Acceptable concurrency and restorable data | Manual pending |

## 7.2 Test Execution and Result

At the time this report was prepared, the repository's virtual environment ran:

```
.venv/bin/pytest -q -p no:cacheprovider
407 passed
```

This is evidence of the automated suite only. Before final submission, add the test date, platform, exact command output and real-browser sign-off. The project supplies a presentation rehearsal in `docs/DEMO.md`. A responsible camera test needs a consenting volunteer, the expected lighting conditions and a record of false matches/non-matches. No numerical recognition accuracy is claimed without that study.

\pagebreak

# 8. SYSTEM IMPLEMENTATION / DEPLOYMENT

## 8.1 Local Installation

The repository's macOS guide recommends Python 3.12 and MySQL 8.4. From the project directory:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set local DB_HOST, DB_NAME, DB_USER and DB_PASSWORD in .env
python init_db.py
flask --app app create-admin
python app.py
```

Open `http://127.0.0.1:5000` and check `/health` and `/health/database`. The latter tests database connectivity, not the entire attendance workflow. Keep `.env` and passwords out of Git. The optional demo seed is for a disposable database only; do not reapply it to institutional data.

## 8.2 Deployment and Acceptance

For production, install `requirements-production.txt`, set a persistent random `SECRET_KEY`, disable debug mode, use a dedicated database account and take a verified backup before migrations. Run `python init_db.py` with a schema-migration account, then serve `wsgi:app` through Gunicorn and an HTTPS reverse proxy. HTTPS is necessary for camera use on a remote domain. Configure TLS, process restart, logging, access control, retention and monitoring for the host. The repository's `docs/DEPLOYMENT.md` gives operational details; it does not claim the system is already production-deployed.

The acceptance demonstration should show admin setup, three-sample face enrolment, session generation, faculty capture and manual fallback, faculty confirmation, student report/export, correction review and logout. Record actual browser and camera results separately from automated test output.

\pagebreak

# 9. CONCLUSION AND FUTURE ENHANCEMENT

## 9.1 Conclusion

FaceAttend implements a coherent three-role attendance workflow. Academic setup leads to dated sessions; camera-assisted or manual events support faculty review; confirmed records drive reports; corrections provide a traceable decision path. The project is suitable for a supervised academic demonstration. Its strongest design choice is to keep a human confirmation step instead of treating face recognition as an unquestionable final mark.

## 9.2 Limitations and Future Enhancement

Face recognition can be affected by pose, lighting, camera quality and look-alike faces. No liveness or anti-spoofing guarantee is implemented. The similarity threshold requires evaluation with consented, representative samples. The simplified seeded dataset is not a claim about actual degree durations. Real MySQL concurrency, multi-user load, camera behavior, backup restoration and privacy procedures need deployment-specific tests.

Future work could add institutional single sign-on, multi-factor authentication, login throttling, password recovery, more detailed analytics, notification of correction decisions, configurable retention and a consent/withdrawal workflow for biometric templates. Before institutional use, legal and privacy review, explicit consent, access controls and an incident-response process are required.

\pagebreak

# 10. APPENDICES

## 10.1 Screenshots

Figure 10.1 is a faculty dashboard screenshot supplied by the project owner on 14 October 2026. It shows the three faculty navigation cards, including Correction Requests beneath My Sessions. Replace it if the final submitted build differs. Add fresh screenshots of the public home page, admin dashboard, student report, faculty roster, correction form and exports after completing the real browser rehearsal. Do not use a mock-up as evidence of completed testing.

[[SCREENSHOT_FACULTY_DASHBOARD]]

Figure 10.1: Faculty dashboard screenshot supplied by project owner

## 10.2 Suggested Demonstration Checklist

- [ ] Record actual operating system, browser, Python and MySQL versions.
- [ ] Initialize a separate demonstration database and create role accounts.
- [ ] Check academic setup, timetable conflicts and session generation.
- [ ] Enrol consenting volunteer samples and check capture quality.
- [ ] Record an entry and exit; try duplicate and unknown-face cases.
- [ ] Use manual fallback, review all statuses and confirm a session.
- [ ] Open student and faculty reports, CSV and PDF exports.
- [ ] Submit and review a correction request, then check history.
- [ ] Check unauthorized role access and logout.
- [ ] Capture final screenshots and update the table of contents page numbers.

\pagebreak

# 11. REFERENCES / BIBLIOGRAPHY

1. FaceAttend repository: `README.md`, `app.py`, `config.py`, `database/schema.sql`, `database/migrations/`, `routes/`, `services/`, `templates/`, `static/` and `tests/`; inspected 14 October 2026.
2. FaceAttend, `docs/DEPLOYMENT.md`, `docs/DEMO.md` and `docs/PRESENTATION.md`; inspected 14 October 2026.
3. Supplied “Copy of PROJECT DOCUMENT STRUCTURE.docx”, report structure and formatting instructions; received 14 October 2026.
4. Flask documentation, https://flask.palletsprojects.com/ — framework concepts and deployment reference.
5. MySQL 8.4 Reference Manual, https://dev.mysql.com/doc/refman/8.4/en/ — SQL and database behavior.
6. OpenCV documentation, https://docs.opencv.org/ — YuNet/SFace API context.
7. pytest documentation, https://docs.pytest.org/ — automated test framework.

**Editorial note:** Replace all bracketed personal details, attach signed certificate/actual screenshots and update page numbers before academic submission. Automated tests must not be described as proof of production camera accuracy or deployment readiness.
