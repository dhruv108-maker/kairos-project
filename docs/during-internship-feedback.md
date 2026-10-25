# During-internship feedback API

The weekly workflow uses the existing `internship_weekly_feedback` table. Daily-log review history uses `internship_work_feedback`; review status and compatibility fields on `internship_daily_logs` are updated in the same transaction.

All routes are mounted under `/api/v1/internship-feedback` and require an authenticated account.

- `GET /participations`: participation list scoped to the authenticated student's account, active faculty supervision/mentorship, or active industry mentor assignments.
- `GET /participations/{participation_id}?week_start=YYYY-MM-DD`: authorized weekly feedback cards for a participation and optional Monday week anchor.
- `PUT /participations/{participation_id}/weeks/{week_start}`: save/update the caller's draft. Reviewer type and identity are derived server-side.
- `POST /participations/{participation_id}/weeks/{week_start}/submit`: submit a saved draft or returned record.
- `POST /daily-logs/{daily_log_id}/feedback`: append a faculty/industry review to the daily work-feedback history and update the matching denormalized review fields atomically.

The API intentionally does not add a feedback table or schema migration; the checked-in MySQL dump already defines the required tables. Verify the deployed schema matches `kairos_full_backup.sql` before deployment. `returned` records can be edited and resubmitted; `submitted` and `locked` records are read-only through ordinary draft operations. No API to return or lock feedback is introduced because the current documented workflow does not define an authorized actor for those transitions.
