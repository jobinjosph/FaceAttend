CREATE TABLE IF NOT EXISTS student_placement_history (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id BIGINT UNSIGNED NOT NULL,
    from_semester_id BIGINT UNSIGNED NOT NULL,
    to_semester_id BIGINT UNSIGNED NOT NULL,
    moved_by_user_id BIGINT UNSIGNED NULL,
    moved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_placement_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_placement_from_semester FOREIGN KEY (from_semester_id) REFERENCES semesters(id) ON DELETE RESTRICT,
    CONSTRAINT fk_placement_to_semester FOREIGN KEY (to_semester_id) REFERENCES semesters(id) ON DELETE RESTRICT,
    CONSTRAINT fk_placement_moved_by FOREIGN KEY (moved_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_placement_student_time (student_id, moved_at)
) ENGINE=InnoDB;
