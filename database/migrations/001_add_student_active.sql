ALTER TABLE students
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER face_registered;
