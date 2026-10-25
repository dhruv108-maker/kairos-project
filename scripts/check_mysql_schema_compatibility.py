"""Load only CREATE TABLE DDL from the checked-in dump into disposable CI MySQL."""
from __future__ import annotations
import os
import re
from pathlib import Path
import pymysql

ROOT = Path(__file__).resolve().parents[1]
dump = (ROOT / "kairos_full_backup.sql").read_text(encoding="utf-8", errors="replace")
# Capture table definitions only; no INSERT statements or production rows are imported.
statements = re.findall(r"CREATE TABLE .*? ENGINE=.*?;", dump, flags=re.DOTALL)
if not statements:
    raise SystemExit("No CREATE TABLE statements found in schema reference")
connection = pymysql.connect(
    host=os.environ["MYSQL_HOST"], port=int(os.environ.get("MYSQL_PORT", "3306")),
    user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DATABASE"], autocommit=True, charset="utf8mb4",
)
try:
    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        for statement in statements:
            cursor.execute(statement)
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        expected = {
            "accounts": {"id", "email", "full_name"},
            "students": {"id", "account_id"},
            "faculty": {"id", "account_id"},
            "faculty_mentorships": {"faculty_id", "student_id", "starts_on", "ends_on", "status"},
            "industry_mentors": {"id", "account_id", "status"},
            "industry_mentor_assignments": {"participation_id", "industry_mentor_id", "starts_on", "ends_on", "status"},
            "internship_participations": {"id", "student_id", "starts_on", "ends_on", "status", "provider_id"},
            "internship_weekly_feedback": {"participation_id", "week_start", "reviewer_type", "reviewer_account_id", "industry_mentor_id", "status"},
            "internship_work_feedback": {"daily_log_id", "reviewer_type", "reviewer_account_id", "faculty_id", "industry_mentor_id", "decision"},
            "internship_daily_logs": {"id", "participation_id", "student_id", "log_date", "faculty_review_status", "industry_review_status"},
        }
        for table, expected_columns in expected.items():
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", (os.environ["MYSQL_DATABASE"], table))
            actual = {row[0] for row in cursor.fetchall()}
            missing = expected_columns - actual
            if missing:
                raise SystemExit(f"{table}: missing columns: {sorted(missing)}")
            print(f"PASS {table}: {len(actual)} columns loaded from schema-only DDL")
        print(f"PASS loaded {len(statements)} CREATE TABLE definitions; no dump data was imported")
finally:
    connection.close()
