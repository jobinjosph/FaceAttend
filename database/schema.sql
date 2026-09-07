-- FaceAttend database schema
-- Phase 1 includes the full core data model so later phases can build on it.

CREATE TABLE IF NOT EXISTS courses (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS semesters (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id BIGINT UNSIGNED NOT NULL,
    semester_number TINYINT UNSIGNED NOT NULL,
    section VARCHAR(20) NOT NULL DEFAULT 'A',
    academic_year VARCHAR(20) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_semester_course
        FOREIGN KEY (course_id) REFERENCES courses(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_course_semester_section
        UNIQUE (course_id, semester_number, section, academic_year)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'FACULTY', 'STUDENT') NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS students (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NULL UNIQUE,
    register_number VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(190) NULL,
    course_id BIGINT UNSIGNED NOT NULL,
    semester_id BIGINT UNSIGNED NOT NULL,
    face_registered BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    lifecycle_status ENUM('ACTIVE', 'GRADUATED', 'WITHDRAWN', 'ARCHIVED') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_student_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_student_course
        FOREIGN KEY (course_id) REFERENCES courses(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_student_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;

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

CREATE TABLE IF NOT EXISTS faculty (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NULL UNIQUE,
    employee_code VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(190) NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_faculty_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS subjects (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(50) NOT NULL UNIQUE,
    subject_name VARCHAR(160) NOT NULL,
    semester_id BIGINT UNSIGNED NOT NULL,
    activity_type ENUM('LECTURE', 'THEORY', 'PRACTICAL', 'PROJECT') NOT NULL DEFAULT 'LECTURE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_subject_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS timetable_periods (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    semester_id BIGINT UNSIGNED NOT NULL,
    subject_id BIGINT UNSIGNED NOT NULL,
    faculty_id BIGINT UNSIGNED NOT NULL,
    day_of_week TINYINT UNSIGNED NOT NULL,
    period_number TINYINT UNSIGNED NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_day_of_week CHECK (day_of_week BETWEEN 1 AND 7),
    CONSTRAINT chk_period_number CHECK (period_number >= 1),
    CONSTRAINT fk_timetable_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_timetable_subject
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_timetable_faculty
        FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS face_embeddings (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id BIGINT UNSIGNED NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    embedding_data JSON NOT NULL,
    sample_count SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_embedding_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_student_model UNIQUE (student_id, model_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    semester_id BIGINT UNSIGNED NOT NULL,
    subject_id BIGINT UNSIGNED NOT NULL,
    faculty_id BIGINT UNSIGNED NOT NULL,
    timetable_period_id BIGINT UNSIGNED NULL,
    session_date DATE NOT NULL,
    period_number TINYINT UNSIGNED NOT NULL,
    scheduled_start TIME NOT NULL,
    scheduled_end TIME NOT NULL,
    started_at DATETIME NULL,
    ended_at DATETIME NULL,
    status ENUM('SCHEDULED', 'ACTIVE', 'REVIEW', 'CONFIRMED', 'NOT_CONDUCTED')
        NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_session_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_session_subject
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_session_faculty
        FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_session_timetable
        FOREIGN KEY (timetable_period_id) REFERENCES timetable_periods(id)
        ON DELETE SET NULL,
    CONSTRAINT uq_session_subject_period
        UNIQUE (semester_id, subject_id, session_date, period_number)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    event_type ENUM('ENTRY', 'EXIT') NOT NULL,
    event_time DATETIME NOT NULL,
    similarity_score DECIMAL(6,5) NULL,
    source ENUM('FACE', 'MANUAL') NOT NULL DEFAULT 'FACE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_attendance_event_session_student_time
        (session_id, student_id, event_time),
    CONSTRAINT fk_event_session
        FOREIGN KEY (session_id) REFERENCES attendance_sessions(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_event_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_records (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    first_entry DATETIME NULL,
    last_exit DATETIME NULL,
    total_present_seconds INT UNSIGNED NOT NULL DEFAULT 0,
    status ENUM(
        'PRESENT',
        'ABSENT',
        'LATE',
        'LEFT_EARLY',
        'ON_DUTY',
        'MEDICAL',
        'NOT_MARKED',
        'NOT_CONDUCTED'
    ) NOT NULL DEFAULT 'NOT_MARKED',
    marking_method ENUM('FACE', 'MANUAL', 'ADMIN_CORRECTION')
        NOT NULL DEFAULT 'FACE',
    teacher_override BOOLEAN NOT NULL DEFAULT FALSE,
    notes VARCHAR(255) NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_attendance_session_student UNIQUE (session_id, student_id),
    CONSTRAINT fk_record_session
        FOREIGN KEY (session_id) REFERENCES attendance_sessions(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_record_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;
