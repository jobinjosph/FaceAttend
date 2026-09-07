INSERT INTO courses (code, name, total_semesters, is_active)
VALUES
    ('BCA', 'Bachelor of Computer Applications', 4, TRUE),
    ('MCA', 'Master of Computer Applications', 4, TRUE),
    ('BCOM', 'Bachelor of Commerce', 4, TRUE),
    ('MSW', 'Master of Social Work', 4, TRUE)
ON DUPLICATE KEY UPDATE
    name=VALUES(name),
    total_semesters=VALUES(total_semesters),
    is_active=TRUE;

UPDATE courses
SET is_active=FALSE
WHERE code NOT IN ('BCA', 'MCA', 'BCOM', 'MSW');

UPDATE semesters sem
JOIN courses c ON c.id=sem.course_id
SET sem.is_active=FALSE
WHERE c.code NOT IN ('BCA', 'MCA', 'BCOM', 'MSW')
   OR sem.semester_number > 4
   OR sem.section NOT IN ('A', 'B');

INSERT INTO semesters
    (course_id, semester_number, section, academic_year, is_active)
SELECT c.id, numbers.semester_number, sections.section, '2026-27', TRUE
FROM courses c
CROSS JOIN (
    SELECT 1 AS semester_number UNION ALL SELECT 2
    UNION ALL SELECT 3 UNION ALL SELECT 4
) numbers
CROSS JOIN (
    SELECT 'A' AS section UNION ALL SELECT 'B'
) sections
WHERE c.code IN ('BCA', 'MCA', 'BCOM', 'MSW')
ON DUPLICATE KEY UPDATE is_active=TRUE;
