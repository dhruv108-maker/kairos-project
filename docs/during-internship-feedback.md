# During-internship feedback API

Weekly feedback persists in the existing `internship_weekly_feedback` table. Daily-log reviews persist in `internship_work_feedback`; the corresponding `internship_daily_logs` review fields are updated in the same transaction.

All routes are mounted under `/api/v1/internship-feedback` and require an authenticated account.

- `GET /participations`: lists participations scoped to the authenticated student, assigned faculty supervision/mentorship, or active industry mentor assignment.
- `GET /participations/{participation_id}?week_start=YYYY-MM-DD`: retrieves authorized weekly feedback records.
- `PUT /participations/{participation_id}/weeks/{week_start}`: saves or updates the caller's draft. Reviewer role and identity are derived server-side.
- `POST /participations/{participation_id}/weeks/{week_start}/submit`: submits a saved draft or returned record.
- `POST /participations/{participation_id}/weeks/{week_start}/records/{feedback_id}/return`: assigned faculty mentor returns a submitted student reflection for correction.
- `POST /participations/{participation_id}/weeks/{week_start}/records/{feedback_id}/lock`: assigned faculty mentor locks a submitted student reflection.
- `POST /daily-logs/{daily_log_id}/feedback`: appends authorized faculty/industry feedback to daily-log history and updates denormalized review fields atomically.

The API uses the existing tables from `kairos_full_backup.sql`; no feedback table or migration is added. The save operation locks the parent participation while checking the existing reviewer key because MySQL permits duplicate rows for unique keys containing NULL values. The current state policy allows draft edits, submitted records to be returned/locked by the assigned faculty mentor, returned records to be corrected/resubmitted, and submitted/locked records to be read-only for ordinary save operations.

Verify the deployed database matches the checked-in schema dump before deployment. Remote repository access cannot prove that the production database has this exact schema or that migrations have been applied.
