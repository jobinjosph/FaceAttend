ALTER TABLE semesters
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER academic_year,
    ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP AFTER created_at;

ALTER TABLE subjects
    DROP FOREIGN KEY fk_subject_semester;

ALTER TABLE subjects
    ADD CONSTRAINT fk_subject_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE RESTRICT;

ALTER TABLE timetable_periods
    DROP FOREIGN KEY fk_timetable_semester;

ALTER TABLE timetable_periods
    ADD CONSTRAINT fk_timetable_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE RESTRICT;
