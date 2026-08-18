ALTER TABLE attendance_sessions
    ADD CONSTRAINT uq_session_timetable_date
    UNIQUE (timetable_period_id, session_date);

CREATE INDEX idx_session_faculty_date_status
    ON attendance_sessions (faculty_id, session_date, status);
