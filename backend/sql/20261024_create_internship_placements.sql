-- Create internship placements using the deployed Kairos schema types.
-- Source schema: internship_applications.id, students.id, and faculty.id are BIGINT UNSIGNED.
-- Safe to rerun if the table already exists; if a previous incompatible version exists,
-- drop/recreate only if it is empty and has not been used, otherwise migrate it explicitly.

USE kairos;

CREATE TABLE IF NOT EXISTS internship_placements (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    application_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    faculty_supervisor_id BIGINT UNSIGNED NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('ONGOING', 'COMPLETED', 'TERMINATED') NOT NULL DEFAULT 'ONGOING',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_internship_placements_application (application_id),
    KEY ix_internship_placements_student (student_id),
    KEY ix_internship_placements_supervisor (faculty_supervisor_id),
    CONSTRAINT fk_internship_placements_application
        FOREIGN KEY (application_id)
        REFERENCES internship_applications (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_internship_placements_student
        FOREIGN KEY (student_id)
        REFERENCES students (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_internship_placements_supervisor
        FOREIGN KEY (faculty_supervisor_id)
        REFERENCES faculty (id)
        ON DELETE SET NULL,
    CONSTRAINT chk_internship_placements_dates
        CHECK (end_date >= start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SHOW CREATE TABLE internship_placements;
