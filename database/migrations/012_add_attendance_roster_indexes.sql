CREATE INDEX idx_attendance_record_session_status
    ON attendance_records (session_id, status);

CREATE INDEX idx_student_semester_active
    ON students (semester_id, is_active);
