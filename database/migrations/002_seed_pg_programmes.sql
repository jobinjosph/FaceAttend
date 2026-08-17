INSERT IGNORE INTO courses (code, name) VALUES
    ('MAENG', 'MA English Literature'),
    ('MAMC', 'MA Media & Communication'),
    ('MAPPI', 'MA Public Policy & International Relations'),
    ('MSCPSY', 'M.Sc Psychology'),
    ('MSCCLP', 'M.Sc Clinical Psychology'),
    ('MSCCOP', 'M.Sc Counselling Psychology'),
    ('MSCHRDP', 'M.Sc Human Resource Development Psychology'),
    ('MSW', 'Master of Social Work (MSW)'),
    ('MCA', 'Master of Computer Applications'),
    ('MSCDS', 'M.Sc Data Science'),
    ('MSCCS', 'M.Sc Cyber Security'),
    ('MSCPHY', 'M.Sc Physics'),
    ('MSCSTAT', 'M.Sc Applied Statistics & Data Analytics'),
    ('MSCECO', 'M.Sc Economics'),
    ('MCOMFA', 'M.Com Financial Analysis'),
    ('MCOMITAF', 'M.Com International Taxation & Applied Finance'),
    ('MSCBIOCHEM', 'M.Sc Biochemistry'),
    ('MSCBIOTECH', 'M.Sc Biotechnology'),
    ('MSCMICRO', 'M.Sc Microbiology'),
    ('MSCFS', 'M.Sc Forensic Science'),
    ('MSCBI', 'M.Sc Bioinformatics'),
    ('MSCDFIS', 'M.Sc Digital Forensics & Information Security'),
    ('LLMCAL', 'LL.M Constitutional & Administrative Law'),
    ('LLMIPRTL', 'LL.M IPR & Technology Law');

INSERT IGNORE INTO semesters
    (course_id, semester_number, section, academic_year)
SELECT
    courses.id,
    semester_numbers.semester_number,
    'A',
    '2026-27'
FROM courses
CROSS JOIN (
    SELECT 1 AS semester_number
    UNION ALL SELECT 2
    UNION ALL SELECT 3
    UNION ALL SELECT 4
) AS semester_numbers
WHERE courses.code IN (
    'MAENG', 'MAMC', 'MAPPI', 'MSCPSY', 'MSCCLP', 'MSCCOP',
    'MSCHRDP', 'MSW', 'MCA', 'MSCDS', 'MSCCS', 'MSCPHY',
    'MSCSTAT', 'MSCECO', 'MCOMFA', 'MCOMITAF', 'MSCBIOCHEM',
    'MSCBIOTECH', 'MSCMICRO', 'MSCFS', 'MSCBI', 'MSCDFIS',
    'LLMCAL', 'LLMIPRTL'
);
