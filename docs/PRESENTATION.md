# FaceAttend presentation outline

1. Problem: manual period attendance takes staff time and needs a clear correction trail.
2. Objective: record entry/exit, let faculty confirm attendance, and give students transparent reports.
3. Roles: Admin configures academic groups and enrolment; Faculty runs and reviews sessions; Students view their own reports and request corrections.
4. Architecture: browser forms and camera JavaScript → Flask routes and services → MySQL. OpenCV YuNet detects faces and SFace creates descriptors for comparison. Raw camera samples are processed into numerical embeddings stored in MySQL.
5. Data relationships: programme → academic group (year, semester, section) → subjects and timetable → dated sessions → attendance records/events. Students have placement/lifecycle history; correction decisions update records with an audit trail.
6. Demonstration: use DEMO.md to show the complete workflow.
7. Verification: show automated test output and separately record manual browser/camera results. Do not describe mocked tests as live deployment verification.
8. Conclusion: present the implemented academic demonstration and explain the future work below.

## Limitations and future enhancements

- Face recognition depends on lighting, pose and camera quality. There is no implemented liveness/anti-spoofing guarantee; manual faculty review remains necessary.
- The four-programme, four-semester demo is a simplified dataset, not a statement of real degree durations.
- Camera matching thresholds need evaluation on representative, consented samples before real institutional use.
- Login throttling, MFA, password recovery and immediate revocation of already-issued sessions after account changes remain future security work. Current role guards rely on the signed session; the previous security pass did not establish production security certification.
- Automated tests are mostly isolated/mocked; multi-user load, real database concurrency, backup restoration and physical camera trials need deployment-specific verification.
- HTTPS hosting, monitoring, privacy/retention procedures and institutional approval are required before a real college rollout.
- Potential enhancements: notifications, richer analytics, additional programmes, timetable automation and identity-provider integration.
