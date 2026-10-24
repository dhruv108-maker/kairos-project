-- Recovery for the partially applied 20261024_student_profile_compatibility.sql.
-- Use this script ONLY if the earlier script successfully added the compatibility columns
-- and backfilled them, but failed at the final ALTER TABLE with MySQL error 3780.
-- Take a database backup first. This script does not re-add columns or recreate rows.
-- The deployed academic catalogue IDs are BIGINT UNSIGNED.
--
-- Preflight: if this returns any rows, STOP and inspect the values before continuing.
SELECT id, department_id, programme_id, cohort_id
FROM student_profiles
WHERE (department_id IS NOT NULL AND department_id NOT REGEXP '^[0-9]+$')
   OR (programme_id IS NOT NULL AND programme_id NOT REGEXP '^[0-9]+$')
   OR (cohort_id IS NOT NULL AND cohort_id NOT REGEXP '^[0-9]+$');

-- Correct types to match departments.id, programmes.id, and cohorts.id.
ALTER TABLE student_profiles
    MODIFY COLUMN department_id BIGINT UNSIGNED NULL,
    MODIFY COLUMN programme_id BIGINT UNSIGNED NULL,
    MODIFY COLUMN cohort_id BIGINT UNSIGNED NULL;

-- Ensure identity fields are populated before requiring them.
UPDATE student_profiles AS p
JOIN students AS s ON s.id = p.student_id
SET p.account_id = s.account_id,
    p.enrollment_number = s.student_number
WHERE p.account_id IS NULL OR p.enrollment_number IS NULL;

-- Stop and investigate if this is nonzero before running the constraint statement.
SELECT COUNT(*) AS profiles_missing_identity
FROM student_profiles
WHERE account_id IS NULL OR enrollment_number IS NULL;

ALTER TABLE student_profiles
    MODIFY COLUMN account_id BIGINT UNSIGNED NOT NULL,
    MODIFY COLUMN enrollment_number VARCHAR(80) NOT NULL,
    ADD UNIQUE KEY uq_student_profiles_account (account_id),
    ADD UNIQUE KEY uq_student_profiles_enrollment_number (enrollment_number),
    ADD KEY ix_student_profiles_department (department_id),
    ADD KEY ix_student_profiles_programme (programme_id),
    ADD KEY ix_student_profiles_cohort (cohort_id),
    ADD CONSTRAINT fk_student_profiles_account
        FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_student_profiles_department
        FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_student_profiles_programme
        FOREIGN KEY (programme_id) REFERENCES programmes (id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_student_profiles_cohort
        FOREIGN KEY (cohort_id) REFERENCES cohorts (id) ON DELETE RESTRICT;

-- Final verification: expect 0 missing identities and four profile FK constraints.
SELECT COUNT(*) AS profiles_missing_identity
FROM student_profiles
WHERE account_id IS NULL OR enrollment_number IS NULL;

SHOW CREATE TABLE student_profiles;
