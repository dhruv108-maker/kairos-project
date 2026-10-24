-- Fix schema drift reported by the internship API.
-- Run against the kairos database after confirming the referenced parent tables exist.
-- This is a manual MySQL migration; no Alembic command is required.

-- 1) Restore the association table used to exclude opportunities already linked
--    to an active/published recruitment drive.
CREATE TABLE IF NOT EXISTS recruitment_drive_opportunities (
    drive_id VARCHAR(36) NOT NULL,
    opportunity_id VARCHAR(36) NOT NULL,
    added_by_account_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (drive_id, opportunity_id),
    CONSTRAINT uq_drive_opportunity UNIQUE (drive_id, opportunity_id),
    KEY ix_drive_opportunity_opportunity (opportunity_id),
    CONSTRAINT fk_rdo_drive
        FOREIGN KEY (drive_id) REFERENCES recruitment_drives (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rdo_opportunity
        FOREIGN KEY (opportunity_id) REFERENCES internship_opportunities (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_rdo_added_by
        FOREIGN KEY (added_by_account_id) REFERENCES accounts (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Add the recruitment stage expected by InternshipApplication ORM queries.
--    Run this ALTER once; omit it if the column already exists.
ALTER TABLE internship_applications
    ADD COLUMN recruitment_stage VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED';

-- 3) Index the stage for recruitment-stage filtering.
--    Run once; omit if this index already exists.
CREATE INDEX ix_internship_applications_recruitment_stage
    ON internship_applications (recruitment_stage);

-- 4) Verify the repaired schema.
SHOW COLUMNS FROM internship_applications LIKE 'recruitment_stage';
SHOW CREATE TABLE recruitment_drive_opportunities;
