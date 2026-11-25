"""Seed clearly labelled Kairos demo records into the configured MySQL database.

Run from backend/: python scripts/seed_demo_data.py
Safety: requires KAIROS_SEED_DEMO=true. Inserts only deterministic demo IDs and never deletes rows.
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.core.config import settings
from app.models import (
    Account, Institution, StudentProfile, FacultyProfile, EmployerOrganization,
    InternshipProvider, InternshipOpportunity, InternshipApplication,
    RecruitmentDrive, RecruitmentDriveOpportunity, RecruitmentInterview,
    RecruitmentOffer, InternshipPlacement, ReportRequirement, StorageFile,
    ReportSubmission, ReportVersion, GriffinEvaluation, GriffinEvaluationAttempt,
    EvaluationWorkflow, EvaluationStageResult,
)

DEMO_KEY = "kairos-demo-v1"


def did(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"{DEMO_KEY}:{name}"))


def get_or_add(session: Session, model, identity: dict, values: dict):
    row = session.scalar(select(model).filter_by(**identity))
    if row is not None:
        return row, False
    row = model(**values)
    session.add(row)
    session.flush()
    return row, True


def main() -> None:
    if os.getenv("KAIROS_SEED_DEMO", "").lower() != "true":
        raise SystemExit("Safety stop: set KAIROS_SEED_DEMO=true to insert demo data.")
    url = URL.create(
        "mysql+pymysql",
        username=settings.DB_USER,
        password=settings.DB_PASSWORD.get_secret_value(),
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        query={"charset": "utf8mb4"},
    )
    engine = create_engine(url, pool_pre_ping=True)
    counts: dict[str, int] = {}

    with Session(engine) as session, session.begin():
        account = session.scalar(select(Account).order_by(Account.id).limit(1))
        institution = session.scalar(select(Institution).order_by(Institution.created_at).limit(1))
        if account is None or institution is None:
            raise SystemExit(
                "Seed prerequisite missing: Kairos needs at least one existing account "
                "and one institution. No rows were committed."
            )
        actor_id = account.id

        employer, made = get_or_add(session, EmployerOrganization,
            {"normalized_name": "kairos demo systems private limited"},
            {"id": did("employer"), "legal_name": "Kairos Demo Systems Private Limited",
             "display_name": "Kairos Demo Systems", "normalized_name": "kairos demo systems private limited",
             "organization_type": "COMPANY", "industry": "Software & Education Technology",
             "description": "DEMO DATA ONLY. Fictional employer for workflow testing.",
             "business_email": "demo-employer@example.invalid", "country": "India",
             "state": "Gujarat", "city": "Vadodara", "status": "VERIFIED",
             "created_by_account_id": actor_id})
        counts["employer_organizations"] = int(made)

        provider, made = get_or_add(session, InternshipProvider,
            {"employer_organization_id": employer.id},
            {"id": did("provider"), "company_name": "Kairos Demo Systems",
             "website": "https://example.invalid", "industry_sector": "Software",
             "contact_person_name": "Demo Recruiter", "contact_email": "demo-employer@example.invalid",
             "employer_organization_id": employer.id})
        counts["internship_providers"] = int(made)

        today = date.today()
        opportunity, made = get_or_add(session, InternshipOpportunity,
            {"id": did("internship-opportunity")},
            {"id": did("internship-opportunity"), "provider_id": provider.id,
             "title": "[DEMO] Software Engineering Intern",
             "description": "Fictional role for testing the Kairos application and recruitment pipeline.",
             "location": "Vadodara, Gujarat", "stipend_amount": Decimal("15000"),
             "application_deadline": today + timedelta(days=45),
             "starts_on": today + timedelta(days=60), "ends_on": today + timedelta(days=150),
             "is_active": True, "summary": "DEMO ONLY: backend and frontend workflow testing.",
             "lifecycle_status": "PUBLISHED", "opportunity_type": "INTERNSHIP",
             "employment_type": "INTERNSHIP", "work_mode": "HYBRID", "department": "Engineering",
             "compensation_currency": "INR", "compensation_period": "MONTH",
             "openings": 8, "required_skills": ["Python", "React", "SQL"],
             "preferred_skills": ["FastAPI", "TypeScript"], "created_by_account_id": actor_id})
        counts["internship_opportunities"] = int(made)

        drive, made = get_or_add(session, RecruitmentDrive,
            {"id": did("recruitment-drive")},
            {"id": did("recruitment-drive"), "institution_id": institution.id,
             "name": "[DEMO] 2026 Campus Recruitment Drive",
             "description": "DEMO ONLY. Exercises campus recruitment and employer participation.",
             "starts_on": today, "ends_on": today + timedelta(days=60),
             "application_opens_at": datetime.now(),
             "application_closes_at": datetime.combine(today + timedelta(days=45), datetime.min.time()),
             "status": "ACTIVE", "created_by_account_id": actor_id})
        counts["recruitment_drives"] = int(made)

        link, made = get_or_add(session, RecruitmentDriveOpportunity,
            {"drive_id": drive.id, "opportunity_id": opportunity.id},
            {"drive_id": drive.id, "opportunity_id": opportunity.id, "added_by_account_id": actor_id})
        counts["recruitment_drive_opportunities"] = int(made)

        profiles = list(session.scalars(select(StudentProfile).order_by(StudentProfile.id).limit(4)))
        faculty = session.scalar(select(FacultyProfile).order_by(FacultyProfile.id).limit(1))
        statuses = ["SUBMITTED", "SHORTLISTED", "ACCEPTED", "REJECTED"]
        stages = ["SUBMITTED", "SHORTLISTED", "OFFERED", "REJECTED"]
        applications = []
        for index, profile in enumerate(profiles):
            app, made = get_or_add(session, InternshipApplication,
                {"opportunity_id": opportunity.id, "student_id": profile.id},
                {"id": did(f"application-{profile.id}"), "opportunity_id": opportunity.id,
                 "student_id": profile.id, "status": statuses[index],
                 "recruitment_stage": stages[index]})
            applications.append((app, profile, index))
            counts["internship_applications"] = counts.get("internship_applications", 0) + int(made)

        for app, profile, index in applications:
            if index == 1:
                _, made = get_or_add(session, RecruitmentInterview,
                    {"id": did(f"interview-{app.id}")},
                    {"id": did(f"interview-{app.id}"), "application_id": app.id,
                     "scheduled_by_account_id": actor_id,
                     "scheduled_at": datetime.now() + timedelta(days=3),
                     "duration_minutes": 30, "interview_type": "VIDEO",
                     "meeting_url": "https://example.invalid/demo-interview", "status": "SCHEDULED",
                     "interviewer_notes": "DEMO ONLY: shortlist interview."})
                counts["recruitment_interviews"] = counts.get("recruitment_interviews", 0) + int(made)
            if index == 2:
                _, made = get_or_add(session, RecruitmentOffer,
                    {"id": did(f"offer-{app.id}")},
                    {"id": did(f"offer-{app.id}"), "application_id": app.id,
                     "issued_by_account_id": actor_id, "status": "ISSUED",
                     "compensation_amount": Decimal("18000"), "compensation_currency": "INR",
                     "compensation_period": "MONTH", "start_date": today + timedelta(days=60),
                     "expires_at": datetime.now() + timedelta(days=14),
                     "terms": "DEMO ONLY. Non-binding sample internship offer.",
                     "issued_at": datetime.now()})
                counts["recruitment_offers"] = counts.get("recruitment_offers", 0) + int(made)
                if faculty is not None:
                    placement, made = get_or_add(session, InternshipPlacement,
                        {"id": did(f"placement-{app.id}")},
                        {"id": did(f"placement-{app.id}"), "application_id": app.id,
                         "student_id": profile.id, "faculty_supervisor_id": faculty.id,
                         "start_date": today - timedelta(days=7),
                         "end_date": today + timedelta(days=83), "status": "ONGOING"})
                    counts["internship_placements"] = counts.get("internship_placements", 0) + int(made)

        if faculty is not None and profiles:
            # A synthetic report chain is created only when a demo placement exists.
            placement = session.scalar(select(InternshipPlacement).where(
                InternshipPlacement.id == did(f"placement-{applications[2][0].id}")
            )) if len(applications) > 2 else None
            if placement is not None:
                requirement, made = get_or_add(session, ReportRequirement,
                    {"institution_id": institution.id, "title": "[DEMO] Internship Final Report"},
                    {"id": did("report-requirement"), "institution_id": institution.id,
                     "title": "[DEMO] Internship Final Report",
                     "description": "Fictional requirement for testing report submission and review.",
                     "due_date": today + timedelta(days=90), "is_required": True,
                     "is_active": True, "created_by_account_id": actor_id})
                counts["report_requirements"] = int(made)

                file, made = get_or_add(session, StorageFile,
                    {"id": did("report-file")},
                    {"id": did("report-file"), "original_name": "DEMO-internship-report.pdf",
                     "file_path": "demo-seed/DEMO-internship-report.pdf", "file_size_bytes": 2048,
                     "mime_type": "application/pdf",
                     "sha256_hash": hashlib.sha256(b"kairos-demo-report-file-v1").hexdigest(),
                     "uploaded_by_account_id": actor_id})
                counts["storage_files"] = int(made)

                submission, made = get_or_add(session, ReportSubmission,
                    {"id": did("report-submission")},
                    {"id": did("report-submission"), "placement_id": placement.id,
                     "requirement_id": requirement.id, "title": "[DEMO] Internship Final Report",
                     "latest_version_number": 1, "status": "UNDER_EVALUATION",
                     "review_feedback": "DEMO ONLY: sample report awaiting evaluation."})
                counts["report_submissions"] = int(made)

                version, made = get_or_add(session, ReportVersion,
                    {"id": did("report-version")},
                    {"id": did("report-version"), "submission_id": submission.id,
                     "version_number": 1, "file_id": file.id,
                     "submission_notes": "DEMO ONLY: placeholder PDF metadata; no physical file is uploaded."})
                counts["report_versions"] = int(made)

                evaluation, made = get_or_add(session, GriffinEvaluation,
                    {"id": did("griffin-evaluation")},
                    {"id": did("griffin-evaluation"), "report_version_id": version.id,
                     "griffin_project_id": "DEMO-KAIROS-PROJECT",
                     "griffin_report_id": "DEMO-KAIROS-REPORT",
                     "griffin_job_id": "DEMO-KAIROS-JOB", "current_status": "COMPLETED"})
                counts["griffin_evaluations"] = int(made)

                _, made = get_or_add(session, GriffinEvaluationAttempt,
                    {"id": did("griffin-attempt")},
                    {"id": did("griffin-attempt"), "griffin_evaluation_id": evaluation.id,
                     "attempt_number": 1, "request_payload": {"demo": True},
                     "response_payload": {"demo": True, "status": "completed"},
                     "execution_status": "COMPLETED", "completed_at": datetime.now()})
                counts["griffin_evaluation_attempts"] = int(made)

                workflow, made = get_or_add(session, EvaluationWorkflow,
                    {"id": did("evaluation-workflow")},
                    {"id": did("evaluation-workflow"), "report_submission_id": submission.id,
                     "current_stage_number": 2, "total_stages": 2, "is_completed": False})
                counts["evaluation_workflows"] = int(made)

                for number, name, status, score in [
                    (1, "Griffin Analysis", "PASSED", Decimal("82.00")),
                    (2, "Faculty Review", "PENDING", None),
                ]:
                    _, made = get_or_add(session, EvaluationStageResult,
                        {"workflow_id": workflow.id, "stage_number": number},
                        {"id": did(f"evaluation-stage-{number}"), "workflow_id": workflow.id,
                         "stage_number": number, "stage_name": name,
                         "evaluator_account_id": actor_id if number == 2 else None,
                         "stage_status": status, "score": score,
                         "feedback_comments": "DEMO ONLY: sample workflow stage."})
                    counts["evaluation_stage_results"] = counts.get("evaluation_stage_results", 0) + int(made)

    engine.dispose()
    print("Kairos demo seed committed successfully.")
    print("Inserted row counts (existing deterministic demo rows are left unchanged):")
    for table, count in sorted(counts.items()):
        print(f"  {table}: {count}")
    print("All inserted records are fictional and labelled [DEMO] or DEMO metadata.")


if __name__ == "__main__":
    main()
