SET @mca_semester_three_id = (
    SELECT sem.id
    FROM semesters sem
    JOIN courses c ON c.id = sem.course_id
    WHERE c.code = 'MCA' AND sem.semester_number = 3
      AND sem.section = 'A' AND sem.academic_year = '2026-27'
    LIMIT 1
);

INSERT INTO subjects
    (subject_code, subject_name, semester_id, activity_type, is_active)
VALUES
    ('CC431', 'Cloud Computing', @mca_semester_three_id, 'THEORY', TRUE),
    ('CCP432', 'Cloud Computing Practical', @mca_semester_three_id, 'PRACTICAL', TRUE),
    ('ECP434', 'Enterprise Computing Project', @mca_semester_three_id, 'PROJECT', TRUE),
    ('MAD432', 'Mobile Application Development', @mca_semester_three_id, 'THEORY', TRUE),
    ('MADP433', 'Mobile Application Development Practical', @mca_semester_three_id, 'PRACTICAL', TRUE),
    ('DA433', 'Digital Analytics', @mca_semester_three_id, 'THEORY', TRUE),
    ('RM331', 'Research Methodology', @mca_semester_three_id, 'THEORY', TRUE),
    ('VSM434', 'Ventureship and Startup Management', @mca_semester_three_id, 'THEORY', TRUE)
ON DUPLICATE KEY UPDATE
    subject_name = VALUES(subject_name), semester_id = VALUES(semester_id),
    activity_type = VALUES(activity_type), is_active = TRUE;

UPDATE subjects s
JOIN semesters sem ON sem.id = s.semester_id
JOIN courses c ON c.id = sem.course_id
SET s.is_active = FALSE
WHERE c.code = 'MCA' AND sem.semester_number = 3
  AND s.subject_code NOT IN (
    'CC431', 'CCP432', 'ECP434', 'MAD432', 'MADP433', 'DA433', 'RM331', 'VSM434'
  );
