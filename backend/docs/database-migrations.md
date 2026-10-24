# Applying backend database migrations

Production database schema changes are applied with Alembic. Starting/restarting the FastAPI
application does **not** run migrations automatically.

## Fix for `Unknown column 'accounts.full_name'`

The ORM maps `Account.full_name` to `accounts.full_name`, while legacy databases may store the
same user-facing value in `accounts.display_name`. The additive migration `20261024_17` adds
`full_name` when absent and backfills each existing row in this order:

1. Preserve the existing non-empty `display_name`, when that column exists.
2. Otherwise use the email local-part as a fallback.
3. Use the account ID only as a final fallback.

The migration leaves `display_name` in place, preserves account rows, and makes `full_name`
non-nullable after backfilling. It does not recreate the table or delete account records.

Run the migration from the backend directory in the same deployed release and environment as
the API, using the environment variables configured for that environment:

```bash
cd backend
alembic current
alembic upgrade head
alembic current
```

Do not paste production credentials into a command or commit them to the repository. Ensure
`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` point to the intended
database before running the migration. Take the normal database backup before production
schema changes.

Verify the column and migration revision against the same database used by the API:

```sql
SHOW COLUMNS FROM accounts LIKE 'full_name';
SHOW COLUMNS FROM accounts LIKE 'display_name';
SELECT version_num FROM alembic_version;
```

The `full_name` column should exist and the migration revision should be `20261024_17` (or a
later head revision if the migration history is extended). If `alembic_version` does not exist
or does not match the repository history, stop and inspect the existing schema/history before
applying anything manually; do not stamp the database or recreate tables blindly.

After applying the migration, restart/redeploy the API if required by the deployment process
and retry login. A successful code push alone does not modify the live database.


## Institution identifiers and cohort enrollment activation

The repository's authoritative institution key contract is `VARCHAR(36)`, generated as a UUID
by the application. The forward migration `20261024_19` accommodates legacy installations where
`institutions.id` was manually created as a numeric key. On MySQL/MariaDB it preserves each
existing numeric identifier as its exact decimal string (for example, `11` becomes `"11"`),
discovers every foreign key referencing `institutions.id`, checks for orphan references, drops
those constraints, converts both sides to `VARCHAR(36)`, and restores the original constraints
and referential actions. It does not generate new IDs or rewrite account/cohort IDs. The migration
is intentionally forward-only; downgrade never attempts a potentially destructive numeric
conversion. It must not be applied to a database with unknown migration history or unresolved
orphan references. Back up the database first and review the schema before applying it.

The migration is a MySQL/MariaDB compatibility path. Clean-install databases already using the
repository's string IDs are left unchanged. The production legacy conversion cannot be considered
verified until the migration is run against a backup/clone of the actual deployed schema and the
resulting primary/foreign-key types and row relationships are inspected.

Migration `20261024_20` adds `cohorts.is_active` with a default of false. Existing cohorts
remain in the database but are not exposed for signup until reviewed and explicitly activated.
New cohorts also start inactive. An authenticated account with an active
`INSTITUTION_ADMIN` membership for that institution can activate or deactivate a cohort using
the existing institution-scoped endpoint:

```http
PATCH /api/v1/institutions/{institution_id}/cohorts/{cohort_id}
Content-Type: application/json

{"is_active": true}
```

The same endpoint accepts `{"is_active": false}` to remove a cohort from signup without deleting
student relationships. Only cohorts whose own activation flag is true, whose school/department/
programme are active, and whose academic year is current and belongs to the same institution are
eligible for new student registration. Existing student profiles and their cohort references are
not changed by either migration.

Before enabling student signup in production, an authorized administrator must verify that:
- The institution record is active and its ID matches the repository's string-key contract.
- The institution has a domain registered through the platform-admin domain workflow and marked verified.
- The institution has an academic year marked current, plus an active school, department, and programme.
- At least one cohort under that programme/year has been explicitly activated.
- `alembic current` reports the expected latest migration revision.

The repository integration does not provide direct access to the live production database. A push
does not apply these migrations; deploy the same code release and run Alembic against the intended
database only after backup and schema/history review.


## School activation compatibility

The ORM and institution administration API support `School.is_active`, and public academic
options intentionally exclude inactive schools. Migration `20261024_21` adds the missing
`schools.is_active` column to legacy databases when absent, with a non-null true default so
existing schools remain visible and their department/cohort relationships are preserved. It is
idempotent for databases where the column already exists. Apply it with the normal Alembic
upgrade process after taking the standard backup; the application does not migrate the database
on startup. The MySQL migration regression fixture intentionally starts without this column and
checks the added field and its backfilled/default visibility.
