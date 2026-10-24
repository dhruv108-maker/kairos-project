from alembic import command
from alembic.config import Config
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect
from pathlib import Path

def test_student_portfolio_and_institution_migrations_upgrade_and_downgrade(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", database_url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    # Core identity tables predate this additive migration chain in the application.
    # Seed the referenced account key so SQLite can rebuild FK-bearing tables during downgrade.
    engine = create_engine(database_url)
    metadata = MetaData()
    Table("accounts", metadata, Column("id", String(36), primary_key=True))
    metadata.create_all(engine)

    command.upgrade(config, "head")
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"student_academic_records", "student_portfolio_entries", "student_resumes"} <= tables
        assert {"institution_domains"} <= tables
        assert {
            "institutions", "institution_memberships", "report_requirements", "institution_invitations",
            "employer_organizations", "employer_memberships", "employer_invitations",
            "recruitment_stage_events", "recruitment_notes", "recruitment_interviews", "recruitment_offers",
            "recruitment_drives", "recruitment_drive_programme_targets", "recruitment_drive_cohort_targets",
            "recruitment_drive_graduation_year_targets", "recruitment_drive_participations", "recruitment_drive_opportunities",
        } <= tables
        indexes = {
            index["name"]
            for table in ("student_academic_records", "student_portfolio_entries", "student_resumes")
            for index in inspect(engine).get_indexes(table)
        }
        assert "ix_student_academic_records_owner_dates" in indexes
        assert "ix_portfolio_entries_owner_kind" in indexes
        assert "ix_portfolio_entries_owner_dates" in indexes
        assert "ix_student_resumes_student_profile_id" in indexes

        command.downgrade(config, "base")
        tables_after_downgrade = set(inspect(engine).get_table_names())
        assert not {
            "student_academic_records", "student_portfolio_entries", "student_resumes", "institution_domains",
            "institutions", "institution_memberships", "report_requirements", "institution_invitations",
            "employer_organizations", "employer_memberships", "employer_invitations",
            "recruitment_stage_events", "recruitment_notes", "recruitment_interviews", "recruitment_offers",
        }.intersection(tables_after_downgrade)
    finally:
        engine.dispose()
