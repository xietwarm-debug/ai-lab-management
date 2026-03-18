ALTER TABLE reservation
ADD INDEX idx_reservation_lab_date_status (lab_name, date, status);

ALTER TABLE reservation
ADD INDEX idx_reservation_user_status (user_name, status);
