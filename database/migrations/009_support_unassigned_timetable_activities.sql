ALTER TABLE timetable_periods
    MODIFY subject_id BIGINT UNSIGNED NULL,
    MODIFY faculty_id BIGINT UNSIGNED NULL,
    ADD COLUMN activity_name VARCHAR(160) NULL AFTER faculty_id;
