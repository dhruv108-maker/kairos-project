-- Add missing student portfolio tables used by the student dashboard.
-- MySQL 8.4 / Kairos deployed schema: student_profiles.id and accounts.id are BIGINT UNSIGNED.
-- Table creation is idempotent; existing data/tables are not dropped.

USE kairos;

CREATE TABLE IF NOT EXISTS student_portfolio_entries (
    id VARCHAR(36) NOT NULL,
    student_profile_id BIGINT UNSIGNED NOT NULL,
    kind VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    organization VARCHAR(255) NULL,
    url VARCHAR(2048) NULL,
    credential_id VARCHAR(255) NULL,
    proficiency VARCHAR(64) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    issued_date DATE NULL,
    is_verified TINYINT(1) NOT NULL DEFAULT 0,
    verified_by_account_id BIGINT UNSIGNED NULL,
    verified_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_portfolio_entries_owner_kind (student_profile_id, kind),
    KEY ix_portfolio_entries_owner_dates (student_profile_id, start_date, end_date),
    KEY ix_student_portfolio_entries_verifier (verified_by_account_id),
    CONSTRAINT fk_student_portfolio_entries_profile
        FOREIGN KEY (student_profile_id) REFERENCES student_profiles (id) ON DELETE CASCADE,
    CONSTRAINT fk_student_portfolio_entries_verifier
        FOREIGN KEY (verified_by_account_id) REFERENCES accounts (id) ON DELETE SET NULL,
    CONSTRAINT ck_portfolio_entry_kind
        CHECK (kind IN ('skill','project','certification','experience','research','award','achievement','activity'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS student_academic_records (
    id VARCHAR(36) NOT NULL,
    student_profile_id BIGINT UNSIGNED NOT NULL,
    institution_name VARCHAR(255) NOT NULL,
    qualification VARCHAR(255) NOT NULL,
    field_of_study VARCHAR(255) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    semester VARCHAR(32) NULL,
    grade_value NUMERIC(8,3) NULL,
    grade_max NUMERIC(8,3) NULL,
    grading_scale VARCHAR(100) NULL,
    description TEXT NULL,
    is_verified TINYINT(1) NOT NULL DEFAULT 0,
    verified_by_account_id BIGINT UNSIGNED NULL,
    verified_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_student_academic_records_owner_dates (student_profile_id, start_date, end_date),
    KEY ix_student_academic_records_verifier (verified_by_account_id),
    CONSTRAINT fk_student_academic_records_profile
        FOREIGN KEY (student_profile_id) REFERENCES student_profiles (id) ON DELETE CASCADE,
    CONSTRAINT fk_student_academic_records_verifier
        FOREIGN KEY (verified_by_account_id) REFERENCES accounts (id) ON DELETE SET NULL,
    CONSTRAINT ck_academic_grade_nonnegative CHECK (grade_value IS NULL OR grade_value >= 0),
    CONSTRAINT ck_academic_grade_max_positive CHECK (grade_max IS NULL OR grade_max > 0),
    CONSTRAINT ck_academic_grade_within_max CHECK (grade_value IS NULL OR grade_max IS NULL OR grade_value <= grade_max)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Resumes are included because the same portfolio module exposes resume endpoints.
-- The deployed schema does not currently contain a `storage_files` table, so do not
-- declare a foreign key to it here. Keep the storage_file_id index; add the FK only
-- after the canonical storage table and its ID type are present in this deployment.
CREATE TABLE IF NOT EXISTS student_resumes (
    id VARCHAR(36) NOT NULL,
    student_profile_id BIGINT UNSIGNED NOT NULL,
    storage_file_id VARCHAR(36) NOT NULL,
    label VARCHAR(255) NOT NULL,
    is_primary TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_student_resume_storage (student_profile_id, storage_file_id),
    KEY ix_student_resumes_student_profile_id (student_profile_id),
    KEY ix_student_resumes_storage_file_id (storage_file_id)
    CONSTRAINT fk_student_resumes_profile
        FOREIGN KEY (student_profile_id) REFERENCES student_profiles (id) ON DELETE CASCADE,
    -- No storage FK yet: storage_files is absent from the deployed schema.
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SHOW TABLES LIKE 'student_portfolio_entries';
SHOW TABLES LIKE 'student_academic_records';
SHOW TABLES LIKE 'student_resumes';
