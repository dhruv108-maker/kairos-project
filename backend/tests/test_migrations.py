from alembic import command
from alembic.config import Config
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect, text as sa_text
from pathlib import Path
import os

import pytest

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


def test_mysql_legacy_numeric_institution_keys_migrate_without_losing_relationships(monkeypatch):
    database_url = os.getenv("MYSQL_LEGACY_MIGRATION_URL")
    if not database_url:
        pytest.skip("MYSQL_LEGACY_MIGRATION_URL is only configured for the disposable MySQL CI service")

    engine = create_engine(database_url)
    try:
        # This URL must point only at the disposable migration-test database.
        with engine.begin() as connection:
            for table in ("cohorts", "academic_years", "schools", "institution_domains", "institutions", "alembic_version"):
                connection.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
            connection.exec_driver_sql("""
                CREATE TABLE institutions (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    name VARCHAR(200) NOT NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB
            """)
            connection.exec_driver_sql("INSERT INTO institutions (id, name) VALUES (11, 'Legacy University')")
            connection.exec_driver_sql("""
                CREATE TABLE institution_domains (
                    id VARCHAR(36) NOT NULL,
                    institution_id BIGINT UNSIGNED NOT NULL,
                    normalized_domain VARCHAR(253) NOT NULL,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_institution_domains_domain (normalized_domain),
                    CONSTRAINT fk_legacy_domain_institution FOREIGN KEY (institution_id)
                        REFERENCES institutions(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
            """)
            connection.exec_driver_sql("""
                CREATE TABLE schools (
                    id VARCHAR(36) NOT NULL,
                    institution_id BIGINT UNSIGNED NULL,
                    code VARCHAR(32) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    PRIMARY KEY (id),
                    CONSTRAINT fk_legacy_school_institution FOREIGN KEY (institution_id)
                        REFERENCES institutions(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB
            """)
            connection.exec_driver_sql("""
                CREATE TABLE academic_years (
                    id VARCHAR(36) NOT NULL,
                    institution_id BIGINT UNSIGNED NULL,
                    year_label VARCHAR(32) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_current BOOLEAN NOT NULL DEFAULT FALSE,
                    PRIMARY KEY (id),
                    CONSTRAINT fk_legacy_year_institution FOREIGN KEY (institution_id)
                        REFERENCES institutions(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB
            """)
            connection.exec_driver_sql("""
                CREATE TABLE cohorts (
                    id VARCHAR(36) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB
            """)
            connection.exec_driver_sql("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    PRIMARY KEY (version_num)
                )
            """)
            connection.exec_driver_sql("INSERT INTO institution_domains (id, institution_id, normalized_domain, is_verified) VALUES ('domain-11', 11, 'legacy.example.test', TRUE)")
            connection.exec_driver_sql("INSERT INTO schools (id, institution_id, code, name) VALUES ('school-11', 11, 'LEG', 'Legacy School')")
            connection.exec_driver_sql("INSERT INTO academic_years (id, institution_id, year_label, start_date, end_date, is_current) VALUES ('year-11', 11, '2026-2027', '2026-06-01', '2027-05-31', TRUE)")
            connection.exec_driver_sql("INSERT INTO cohorts (id, name) VALUES ('cohort-11', 'Legacy Cohort')")
            connection.exec_driver_sql("INSERT INTO alembic_version (version_num) VALUES ('20261024_18')")

        monkeypatch.setenv("ALEMBIC_DATABASE_URL", database_url)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")

        inspector = inspect(engine)
        assert isinstance({c["name"]: c for c in inspector.get_columns("institutions")}["id"]["type"], String)
        for table in ("institution_domains", "schools", "academic_years"):
            column = {c["name"]: c for c in inspector.get_columns(table)}["institution_id"]
            assert isinstance(column["type"], String), f"{table}.institution_id must match institutions.id"
            assert any(fk["referred_table"] == "institutions" for fk in inspector.get_foreign_keys(table))

        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT id FROM institutions").scalar_one() == "11"
            assert connection.exec_driver_sql("SELECT institution_id FROM institution_domains").scalar_one() == "11"
            assert connection.exec_driver_sql("SELECT institution_id FROM schools").scalar_one() == "11"
            assert connection.exec_driver_sql("SELECT institution_id FROM academic_years").scalar_one() == "11"
            assert connection.exec_driver_sql("SELECT id, name, is_active FROM cohorts").one() == ("cohort-11", "Legacy Cohort", 0)
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "20261024_20"
    finally:
        engine.dispose()
