from alembic import command
from alembic.config import Config
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect, text as sa_text
from pathlib import Path

from app.models import Base, Institution

def test_student_portfolio_and_institution_migrations_upgrade_and_downgrade(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", database_url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    # Core identity tables predate this additive migration chain in the application.
    # Seed the referenced account key so SQLite can rebuild FK-bearing tables during downgrade.
    engine = create_engine(database_url)
    metadata = MetaData()
    Table("accounts", metadata, Column("id", String(36), primary_key=True))
    legacy_cohorts = Table(
        "cohorts", metadata,
        Column("id", String(36), primary_key=True),
        Column("name", String(100), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(legacy_cohorts.insert().values(id="legacy-cohort", name="Legacy cohort"))

    command.upgrade(config, "head")
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"student_academic_records", "student_portfolio_entries", "student_resumes"} <= tables
        assert {"institution_domains"} <= tables
        cohort_columns = {column["name"]: column for column in inspect(engine).get_columns("cohorts")}
        assert cohort_columns["is_active"]["nullable"] is False
        with engine.connect() as connection:
            legacy = connection.execute(sa_text("SELECT id, name, is_active FROM cohorts WHERE id = 'legacy-cohort'")).one()
        assert tuple(legacy) == ("legacy-cohort", "Legacy cohort", 0)
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


def test_institution_primary_and_foreign_key_types_follow_string_contract():
    assert isinstance(Institution.__table__.c.id.type, String)
    references = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            for foreign_key in column.foreign_keys:
                if foreign_key.target_fullname == "institutions.id":
                    references.append(f"{table.name}.{column.name}")
                    assert isinstance(column.type, String), (
                        f"{table.name}.{column.name} must use the same string type as institutions.id"
                    )
    assert references, "Expected institution foreign-key relationships to be registered in ORM metadata"
