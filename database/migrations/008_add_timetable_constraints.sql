ALTER TABLE timetable_periods
    ADD CONSTRAINT uq_timetable_semester_day_period
    UNIQUE (semester_id, day_of_week, period_number);

CREATE INDEX idx_timetable_semester_day_time
    ON timetable_periods (semester_id, day_of_week, start_time, end_time);

CREATE INDEX idx_timetable_faculty_day_time
    ON timetable_periods (faculty_id, day_of_week, start_time, end_time);
