CREATE TEMPORARY TABLE current_mca_timetable (
    day_of_week TINYINT UNSIGNED NOT NULL,
    period_number TINYINT UNSIGNED NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    subject_code VARCHAR(50) NULL,
    employee_code VARCHAR(50) NULL,
    activity_name VARCHAR(160) NULL
);

INSERT INTO current_mca_timetable VALUES
(1,1,'10:00','10:50','MAD432','T01',NULL),
(1,2,'11:00','11:50','ECP434','T04',NULL),
(1,3,'12:00','12:50','ECP434','T04',NULL),
(1,4,'13:40','14:30','VSM434','T06',NULL),
(1,5,'14:40','15:30','VSM434','T06',NULL),
(1,6,'15:40','16:30','MADP433','T01',NULL),
(2,1,'10:00','10:50','MAD432','T01',NULL),
(2,2,'11:00','11:50','DA433','T05',NULL),
(2,3,'12:00','12:50','RM331','T02',NULL),
(2,4,'13:40','14:30','CC431','T03',NULL),
(2,5,'14:40','15:30',NULL,NULL,'Library'),
(2,6,'15:40','16:30','MADP433','T01',NULL),
(3,1,'10:00','10:50','CC431','T03',NULL),
(3,2,'11:00','11:50','RM331','T02',NULL),
(3,3,'12:00','12:50','MAD432','T01',NULL),
(3,4,'13:40','14:30','DA433','T05',NULL),
(3,5,'14:40','15:30',NULL,NULL,'Library'),
(3,6,'15:40','16:30','CCP432','T03',NULL),
(4,1,'10:00','10:50','CC431','T03',NULL),
(4,2,'11:00','11:50','ECP434','T04','ECP Practical'),
(4,3,'12:00','12:50','ECP434','T04','ECP Practical'),
(4,4,'13:40','14:30','VSM434','T06',NULL),
(4,5,'14:40','15:30','VSM434','T06',NULL),
(4,6,'15:40','16:30','MAD432','T01',NULL),
(5,1,'10:00','10:50','DA433','T05',NULL),
(5,2,'11:00','11:50','RM331','T02',NULL),
(5,3,'12:00','12:50','CC431','T03',NULL),
(5,4,'13:40','14:30','MAD432','T01',NULL),
(5,5,'14:40','15:30','ECP434','T04',NULL),
(5,6,'15:40','16:30','CCP432','T03',NULL),
(6,1,'10:00','10:50',NULL,NULL,'Placement Training'),
(6,2,'11:00','11:50',NULL,NULL,'Skill Development Activity'),
(6,3,'12:00','12:50','ECP434','T04',NULL);

INSERT INTO timetable_periods
    (semester_id, subject_id, faculty_id, activity_name,
     day_of_week, period_number, start_time, end_time)
SELECT sem.id, s.id, f.id, seed.activity_name,
       seed.day_of_week, seed.period_number, seed.start_time, seed.end_time
FROM current_mca_timetable seed
JOIN courses c ON c.code = 'MCA'
JOIN semesters sem ON sem.course_id = c.id AND sem.semester_number = 3
    AND sem.section = 'A' AND sem.academic_year = '2026-27'
LEFT JOIN subjects s ON s.subject_code = seed.subject_code
LEFT JOIN faculty f ON f.employee_code = seed.employee_code
ON DUPLICATE KEY UPDATE
    subject_id = VALUES(subject_id), faculty_id = VALUES(faculty_id),
    activity_name = VALUES(activity_name), start_time = VALUES(start_time),
    end_time = VALUES(end_time);

DROP TEMPORARY TABLE current_mca_timetable;
