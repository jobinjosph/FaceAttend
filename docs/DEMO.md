# Presentation rehearsal

Use a separate demonstration database and consenting volunteers for camera enrolment. The following are proposed sample identities, not existing login credentials. Choose passwords locally; do not put them in slides or Git.

| Role | Email | Create through |
| --- | --- | --- |
| Admin | demo.admin@example.com | flask --app app create-admin |
| Faculty | demo.faculty@example.com | Admin → Manage Faculty, employee DEMOF001 |
| Student | demo.student@example.com | Admin → Manage Students, register DEMOS001 |

In Academic Structure choose an active programme/year/semester/section. Use a dedicated group for rehearsal. Add subject DEMO101 (Attendance Demonstration), assign the demo faculty member, and add a period on today's weekday. Schedule Monday–Saturday; on Sunday rehearse using a selected teaching date and explain that choice. Create a second student DEMOS002 to show absent attendance. Add them before generating sessions so they appear in the roster.

## Ten-minute demonstration

1. Admin: show Academic Structure and the shared programme/year/semester/section selectors. Show the demonstration subject, faculty assignment and timetable. Attempt an overlapping period and show its rejection.
2. Admin: register three face samples for the consenting demo student, then generate sessions for the selected date.
3. Faculty: log in, start the session, open face attendance and record entry. Later record exit. Show duplicate-entry handling. Use manual attendance if camera conditions fail, and explain the fallback.
4. Faculty: end the session, review the roster, mark every student, then confirm it. Do not leave unmarked records.
5. Student: log in and show semester/month/date attendance and CSV/PDF downloads. Submit a correction with a reason.
6. Faculty or Admin: review that request. Student: refresh the report and show the updated record.
7. Admin: demonstrate placement history and lifecycle on a disposable demo student. Explain that archived data is retained.
8. Log out and request a protected dashboard again; verify login is required.

## Manual sign-off

Record browser, date and actual result for each item. These remain pending until performed in a real browser:

- [ ] Admin, Faculty and Student logins succeed; incorrect credentials fail.
- [ ] Role and record ownership restrictions work.
- [ ] Home and portal navigation work in each role.
- [ ] Programme/group selectors and timetable conflict messages work.
- [ ] Camera permission, enrolment, entry and exit work with a volunteer.
- [ ] Faculty review, confirmation, student report and correction complete.
- [ ] CSV/PDF downloads open correctly.
- [ ] Logout prevents further protected requests.

Automated tests mock many database calls and recognition responses; they do not replace this physical-camera and real-database rehearsal. Keep backup screenshots for presentation, but identify them as screenshots if used.
