-- Optional development data.
-- Run only after database/schema.sql has been applied.

INSERT IGNORE INTO courses (code, name)
VALUES ('MCA', 'Master of Computer Applications');

SET @course_id = (SELECT id FROM courses WHERE code = 'MCA' LIMIT 1);

INSERT IGNORE INTO semesters (course_id, semester_number, section, academic_year)
VALUES (@course_id, 3, 'A', '2026-27');

SET @semester_id = (
    SELECT id
    FROM semesters
    WHERE course_id = @course_id
      AND semester_number = 3
      AND section = 'A'
      AND academic_year = '2026-27'
    LIMIT 1
);

INSERT INTO subjects
(subject_code, subject_name, semester_id, activity_type, is_active)
VALUES
('CC431', 'Cloud Computing', @semester_id, 'THEORY', TRUE),
('CCP432', 'Cloud Computing Practical', @semester_id, 'PRACTICAL', TRUE),
('DA433', 'Digital Analytics', @semester_id, 'THEORY', TRUE),
('ECP434', 'Enterprise Computing Project', @semester_id, 'PROJECT', TRUE),
('IPP435', 'Internship Project Presentation', @semester_id, 'PROJECT', TRUE),
('MAD432', 'Mobile Application Development', @semester_id, 'THEORY', TRUE)
ON DUPLICATE KEY UPDATE
subject_name = VALUES(subject_name),
semester_id = VALUES(semester_id),
activity_type = VALUES(activity_type),
is_active = TRUE;

UPDATE subjects
SET is_active = FALSE
WHERE semester_id = @semester_id
  AND subject_code NOT IN ('CC431', 'CCP432', 'DA433', 'ECP434', 'IPP435', 'MAD432');
