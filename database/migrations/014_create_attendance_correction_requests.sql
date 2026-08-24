CREATE TABLE IF NOT EXISTS attendance_correction_requests (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    attendance_record_id BIGINT UNSIGNED NOT NULL UNIQUE,
    student_id BIGINT UNSIGNED NOT NULL,
    requested_status ENUM('PRESENT', 'ABSENT', 'LATE', 'LEFT_EARLY', 'ON_DUTY', 'MEDICAL') NOT NULL,
    reason VARCHAR(500) NOT NULL,
    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    reviewed_by_user_id BIGINT UNSIGNED NULL,
    reviewer_comment VARCHAR(500) NULL,
    reviewed_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_correction_status_created (status, created_at),
    INDEX idx_correction_student_created (student_id, created_at),
    CONSTRAINT fk_correction_record FOREIGN KEY (attendance_record_id)
        REFERENCES attendance_records(id) ON DELETE CASCADE,
    CONSTRAINT fk_correction_student FOREIGN KEY (student_id)
        REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_correction_reviewer FOREIGN KEY (reviewed_by_user_id)
        REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;
