# Applying backend database migrations

Production database schema changes are applied with Alembic. Starting/restarting the FastAPI
application does **not** run migrations automatically.

## Fix for `Unknown column 'accounts.full_name'`

The ORM maps `Account.full_name` to the `accounts.full_name` column. The additive migration
`20261024_17` adds this column when absent, backfills existing rows from the email local-part,
and then makes it non-nullable. It does not recreate the table or delete account records.

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
SELECT version_num FROM alembic_version;
```

The column should exist and the migration revision should be `20261024_17` (or a later head
revision if the migration history is extended). If `alembic_version` does not exist or does
not match the repository history, stop and inspect the existing schema/history before applying
anything manually; do not stamp the database or recreate tables blindly.

After applying the migration, restart/redeploy the API if required by the deployment process
and retry login. A successful code push alone does not modify the live database.
