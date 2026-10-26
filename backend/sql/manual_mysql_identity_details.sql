-- Kairos optional identity details: manual MySQL/TiDB schema update
-- Review and execute manually. This file has NOT been run against production.
-- Tested assumptions from the checked-in ORM: accounts.id is BIGINT UNSIGNED;
-- identity_details.account_id must match it exactly.
-- MySQL 8.0+ / compatible TiDB; InnoDB required for the foreign key.
-- Run pre-checks first. If an existing object has a different shape, STOP and
-- have a DBA reconcile it; CREATE TABLE IF NOT EXISTS does not repair drift.

-- ============================================================================
-- 1. PRE-CHECKS (read-only)
-- ============================================================================
SELECT DATABASE() AS current_database;

SELECT TABLE_NAME, ENGINE, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('accounts', 'identity_verifications', 'identity_details')
ORDER BY TABLE_NAME;

SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
       COLUMN_KEY, EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (
    (TABLE_NAME = 'accounts' AND COLUMN_NAME = 'id')
    OR (TABLE_NAME = 'identity_verifications' AND COLUMN_NAME IN
        ('id', 'account_id', 'provider', 'provider_reference', 'status',
         'consented_at', 'consent_notice_version', 'created_at', 'updated_at',
         'expires_at', 'completed_at', 'error_category', 'result_metadata'))
    OR (TABLE_NAME = 'identity_details' AND COLUMN_NAME IN
        ('id', 'account_id', 'declared_name', 'consented_at',
         'consent_notice_version', 'created_at', 'updated_at'))
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('accounts', 'identity_verifications', 'identity_details')
ORDER BY TABLE_NAME, CONSTRAINT_TYPE, CONSTRAINT_NAME;

SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('identity_verifications', 'identity_details')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- DBA review gate:
-- The checked-in Account model declares accounts.id BIGINT UNSIGNED, but the
-- older identity_verification Alembic file declares identity_verifications.account_id
-- VARCHAR(36). This repository mismatch cannot establish the live DB's actual type.
-- Inspect the results above. Do not run a guessed ALTER on identity_verifications.
-- If its account_id is not BIGINT UNSIGNED, stop and review its existing FK and
-- stored values with a DBA before changing it. This script intentionally preserves
-- that existing table and its records.

-- ============================================================================
-- 2. UPDATE
-- ============================================================================
-- Creates only the optional details table if it is absent. It does not backfill
-- any accounts or verification records and never marks any identity as verified.
-- If the table already exists, IF NOT EXISTS leaves it untouched; compare its
-- columns/constraints from the pre-check output before proceeding.

CREATE TABLE IF NOT EXISTS identity_details (
    id VARCHAR(36) NOT NULL,
    account_id BIGINT UNSIGNED NOT NULL,
    declared_name VARCHAR(200) NULL,
    consented_at TIMESTAMP NOT NULL,
    consent_notice_version VARCHAR(40) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_identity_details_account UNIQUE (account_id),
    CONSTRAINT fk_identity_details_account_id_accounts
        FOREIGN KEY (account_id) REFERENCES accounts (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- 3. VALIDATION (read-only)
-- ============================================================================
SELECT TABLE_NAME, ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'identity_details';

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY, EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'identity_details'
ORDER BY ORDINAL_POSITION;

SELECT tc.CONSTRAINT_NAME, tc.CONSTRAINT_TYPE,
       kcu.COLUMN_NAME, kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME
FROM information_schema.TABLE_CONSTRAINTS AS tc
LEFT JOIN information_schema.KEY_COLUMN_USAGE AS kcu
  ON kcu.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
 AND kcu.TABLE_NAME = tc.TABLE_NAME
 AND kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
WHERE tc.CONSTRAINT_SCHEMA = DATABASE()
  AND tc.TABLE_NAME = 'identity_details'
ORDER BY tc.CONSTRAINT_TYPE, tc.CONSTRAINT_NAME;

SELECT COUNT(*) AS optional_identity_details_rows
FROM identity_details;

-- Expected: table exists; account_id is BIGINT UNSIGNED NOT NULL; declared_name
-- is nullable; unique account_id and FK to accounts.id with ON DELETE CASCADE.
-- Row count is zero on a newly-created table. Existing rows are preserved.

-- ============================================================================
-- 4. ROLLBACK (DESTRUCTIVE; only if this script created the table and it has no
--    user data that must be retained)
-- ============================================================================
-- First inspect:
-- SELECT COUNT(*) AS rows_to_be_deleted FROM identity_details;
-- DROP TABLE identity_details;
--
-- Do not run the DROP if users have saved details. Back up/export the table first.
-- The CREATE TABLE operation is reversible only before any details are stored.
