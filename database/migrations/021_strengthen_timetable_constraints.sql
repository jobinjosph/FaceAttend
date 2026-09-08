ALTER TABLE timetable_periods
    DROP CHECK chk_day_of_week,
    DROP CHECK chk_period_number,
    ADD CONSTRAINT chk_day_of_week CHECK (day_of_week BETWEEN 1 AND 6),
    ADD CONSTRAINT chk_period_number CHECK (period_number BETWEEN 1 AND 20),
    ADD CONSTRAINT chk_timetable_time_order CHECK (start_time < end_time);
