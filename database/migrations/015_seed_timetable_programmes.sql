INSERT IGNORE INTO courses (code, name) VALUES
    ('BCA', 'Bachelor of Computer Applications'),
    ('BCOM', 'Bachelor of Commerce');
INSERT IGNORE INTO semesters (course_id, semester_number, section, academic_year)
SELECT courses.id, semester_numbers.semester_number, 'A', '2026-27' FROM courses
CROSS JOIN (SELECT 1 AS semester_number UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6) semester_numbers
WHERE courses.code IN ('BCA', 'BCOM');
