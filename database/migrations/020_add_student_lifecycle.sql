ALTER TABLE students
    ADD COLUMN lifecycle_status
        ENUM('ACTIVE', 'GRADUATED', 'WITHDRAWN', 'ARCHIVED')
        NOT NULL DEFAULT 'ACTIVE' AFTER is_active;

UPDATE students
SET lifecycle_status=IF(is_active=TRUE, 'ACTIVE', 'ARCHIVED');

CREATE TABLE IF NOT EXISTS student_lifecycle_history (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id BIGINT UNSIGNED NOT NULL,
    previous_status ENUM('ACTIVE', 'GRADUATED', 'WITHDRAWN', 'ARCHIVED') NOT NULL,
    new_status ENUM('ACTIVE', 'GRADUATED', 'WITHDRAWN', 'ARCHIVED') NOT NULL,
    changed_by_user_id BIGINT UNSIGNED NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lifecycle_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_lifecycle_changed_by FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_lifecycle_student_time (student_id, changed_at)
) ENGINE=InnoDB;
