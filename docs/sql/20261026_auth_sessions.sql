-- Kairos persistent auth sessions (MySQL 8.0+)
-- Run only after a backup and after confirming the accounts.id type.
-- This is intentionally manual SQL; do not run against production without approval.

-- PRE-CHECK: confirm accounts exists and inspect the referenced key type.
SHOW CREATE TABLE accounts;
SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'auth_sessions';

-- APPLY: execute only if the pre-check confirms auth_sessions does not exist.
CREATE TABLE auth_sessions (
    id CHAR(36) NOT NULL,
    account_id BIGINT UNSIGNED NOT NULL,
    refresh_token_hash CHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP NULL DEFAULT NULL,
    token_version INT NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_auth_sessions_refresh_token_hash UNIQUE (refresh_token_hash),
    CONSTRAINT fk_auth_sessions_account
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    INDEX ix_auth_sessions_account_expires (account_id, expires_at),
    INDEX ix_auth_sessions_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- VALIDATE: expect one row and the listed indexes/foreign key.
SHOW CREATE TABLE auth_sessions;
SELECT COUNT(*) AS session_count FROM auth_sessions;

-- ROLLBACK (destructive to active login sessions): run manually only if reverting.
-- DROP TABLE auth_sessions;
