-- Kairos student profile compatibility migration.
-- Run once against the application database before deploying the matching backend.
-- Take a database backup first. The existing profile table remains canonical for
-- profile attributes; students remains canonical for student identity.

ALTER TABLE student_profiles
    ADD COLUMN account_id BIGINT UNSIGNED NULL AFTER student_id,
    ADD COLUMN enrollment_number VARCHAR(80) NULL AFTER account_id,
    ADD COLUMN department_id VARCHAR(36) NULL,
    ADD COLUMN programme_id VARCHAR(36) NULL,
    ADD COLUMN cohort_id VARCHAR(36) NULL,
    ADD COLUMN current_semester INT NOT NULL DEFAULT 1;

-- Ensure every existing student has a profile before applying NOT NULL constraints.
INSERT INTO student_profiles (student_id)
SELECT s.id
FROM students AS s
LEFT JOIN student_profiles AS p ON p.student_id = s.id
WHERE p.id IS NULL;

-- Backfill identity fields and current academic placement from the canonical tables.
UPDATE student_profiles AS p
JOIN students AS s ON s.id = p.student_id
SET p.account_id = s.account_id,
    p.enrollment_number = s.student_number;

UPDATE student_profiles AS p
JOIN student_enrollments AS se ON se.student_id = p.student_id
JOIN cohorts AS c ON c.id = se.cohort_id
JOIN programmes AS pr ON pr.id = c.programme_id
JOIN departments AS d ON d.id = pr.department_id
SET p.cohort_id = c.id,
    p.programme_id = pr.id,
    p.department_id = d.id
WHERE LOWER(se.enrollment_status) = 'active';

ALTER TABLE student_profiles
    MODIFY COLUMN account_id BIGINT UNSIGNED NOT NULL,
    MODIFY COLUMN enrollment_number VARCHAR(80) NOT NULL,
    ADD UNIQUE KEY uq_student_profiles_account (account_id),
    ADD UNIQUE KEY uq_student_profiles_enrollment_number (enrollment_number),
    ADD KEY ix_student_profiles_department (department_id),
    ADD KEY ix_student_profiles_programme (programme_id),
    ADD CONSTRAINT fk_student_profiles_account
        FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_student_profiles_department
        FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_student_profiles_programme
        FOREIGN KEY (programme_id) REFERENCES programmes (id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_student_profiles_cohort
        FOREIGN KEY (cohort_id) REFERENCES cohorts (id) ON DELETE RESTRICT;

-- Confirm that every profile has a matching student/account before application rollout.
SELECT COUNT(*) AS profiles_missing_identity
FROM student_profiles
WHERE account_id IS NULL OR enrollment_number IS NULL;
