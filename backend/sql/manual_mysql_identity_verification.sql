-- Kairos: separate email verification from Aadhaar identity verification
-- MANUAL REVIEW ONLY. This file has not been executed against any database.
-- Target: MySQL 8.0+ / MySQL 8.4 (BOOLEAN is a TINYINT(1) alias).
-- Required rollout: review pre-checks, apply ALTER only if the column is absent,
-- verify post-checks, then deploy backend/frontend code. Do not deploy code first.
-- Existing accounts are initialized to identity_verified = 0; no account is
-- marked identity-verified by this schema change.

-- ============================================================================
-- 1. PRE-CHECKS (read-only)
-- ============================================================================
SELECT DATABASE() AS current_database,
       VERSION() AS mysql_version,
       @@version_comment AS database_engine;

SHOW CREATE TABLE accounts;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'accounts'
  AND COLUMN_NAME IN ('id', 'is_verified', 'identity_verified')
ORDER BY ORDINAL_POSITION;

SELECT COUNT(*) AS identity_verified_column_exists
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'accounts'
  AND COLUMN_NAME = 'identity_verified';

-- STOP if accounts does not exist, if is_verified is absent, or if the existing
-- identity_verified column has a different definition. If the count above is 1,
-- DO NOT run the ALTER statement below; inspect its type/default/nullability and
-- continue to the validation queries instead.
-- If the count above is 0, the database owner may run the following statement.

-- ============================================================================
-- 2. UPDATE (run only when pre-check confirms the column is absent)
-- ============================================================================
ALTER TABLE accounts
    ADD COLUMN identity_verified BOOLEAN NOT NULL DEFAULT FALSE
    COMMENT 'Authoritative identity verification summary; separate from email is_verified';

-- This adds no historical positive identity claims. MySQL initializes existing
-- rows to FALSE using the NOT NULL DEFAULT FALSE definition.

-- ============================================================================
-- 3. POST-UPDATE VALIDATION (read-only; safe even when column pre-existed)
-- ============================================================================
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'accounts'
  AND COLUMN_NAME IN ('is_verified', 'identity_verified')
ORDER BY COLUMN_NAME;

-- Aggregate-only check: no personal data or individual account identifiers.
SELECT COUNT(*) AS total_accounts,
       SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) AS email_verified_accounts,
       SUM(CASE WHEN identity_verified = 1 THEN 1 ELSE 0 END) AS identity_verified_accounts,
       SUM(CASE WHEN identity_verified = 0 THEN 1 ELSE 0 END) AS identity_unverified_accounts,
       SUM(CASE WHEN identity_verified IS NULL THEN 1 ELSE 0 END) AS nullable_identity_flags
FROM accounts;

-- Distribution across the two independent states; aggregate counts only.
SELECT is_verified AS email_verified,
       identity_verified,
       COUNT(*) AS account_count
FROM accounts
GROUP BY is_verified, identity_verified
ORDER BY is_verified, identity_verified;

-- Expected definition: identity_verified is BOOLEAN/TINYINT(1), NOT NULL,
-- default 0/false. Immediately after a fresh column addition, identity_verified
-- is 0 for every existing account; existing is_verified values remain unchanged.
-- Do not update identity_verified to 1 to make test data look verified.

-- ============================================================================
-- 4. ROLLBACK (DESTRUCTIVE; only with explicit database-owner approval)
-- ============================================================================
-- WARNING: dropping this column permanently destroys all persisted identity
-- verification summary flags. Back up the table and confirm no flags need to be
-- retained before executing. This does not change email is_verified.
-- ALTER TABLE accounts DROP COLUMN identity_verified;
