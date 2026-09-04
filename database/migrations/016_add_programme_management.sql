ALTER TABLE courses
    ADD COLUMN total_semesters TINYINT UNSIGNED NOT NULL DEFAULT 1 AFTER name,
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER total_semesters,
    ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP AFTER created_at;

UPDATE courses c
SET total_semesters = GREATEST(
    total_semesters,
    COALESCE((SELECT MAX(sem.semester_number) FROM semesters sem WHERE sem.course_id = c.id), 1)
);

ALTER TABLE semesters
    DROP FOREIGN KEY fk_semester_course;

ALTER TABLE semesters
    ADD CONSTRAINT fk_semester_course
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE RESTRICT;
