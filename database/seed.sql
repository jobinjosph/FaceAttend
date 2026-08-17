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

INSERT IGNORE INTO subjects
(subject_code, subject_name, semester_id, activity_type)
VALUES
('CC431', 'Cloud Computing', @semester_id, 'LECTURE'),
('RM331', 'Research Methodology', @semester_id, 'LECTURE'),
('MAD432', 'Mobile Application Development', @semester_id, 'LECTURE');
