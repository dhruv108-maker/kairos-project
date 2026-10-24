-- Create the internship placement table required by the student placement dashboard/API.
-- Target: MySQL 8.4. Safe to run more than once.
-- A placement is created from an internship application; each application can produce
-- at most one placement. student_id references student_profiles.id (BIGINT UNSIGNED).

CREATE TABLE IF NOT EXISTS internship_placements (
    id VARCHAR(36) NOT NULL,
    application_id VARCHAR(36) NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    faculty_supervisor_id VARCHAR(36) NULL,
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
        REFERENCES student_profiles (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_internship_placements_supervisor
        FOREIGN KEY (faculty_supervisor_id)
        REFERENCES faculty_profiles (id)
        ON DELETE SET NULL,
    CONSTRAINT chk_internship_placements_dates
        CHECK (end_date >= start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verify table creation.
SHOW CREATE TABLE internship_placements;
