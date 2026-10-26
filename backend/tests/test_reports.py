from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import (
    Account, AcademicYear, Base, Cohort, Department, FacultyProfile, InternshipApplication,
    InternshipOpportunity, InternshipPlacement, InternshipProvider, Programme, School,
    StudentProfile, StorageFile,
)
from app.modules.reports.service import ReportService, ReportWorkflowError


@pytest_asyncio.fixture
async def report_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        school = School(id="school", code="SCH", name="School", is_active=True)
        department = Department(id="department", school_id="school", code="DEP", name="Department", is_active=True)
        programme = Programme(id="programme", department_id="department", code="PROG", name="Programme", degree_level="UG", duration_years=3, is_active=True)
        year = AcademicYear(id="year", year_label="2026-27", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), is_current=True)
        cohort = Cohort(id="cohort", programme_id="programme", academic_year_id="year", name="Batch", graduation_year=2029)
        student_account = Account(id="student-account", email="student@example.test", password_hash="x", full_name="Student", is_active=True, is_verified=True)
        faculty_account = Account(id="faculty-account", email="faculty@example.test", password_hash="x", full_name="Faculty", is_active=True, is_verified=True)
        student = StudentProfile(id="student", student_id=1001, account_id="student-account", enrollment_number="E-1", cohort_id="cohort", current_semester=1)
        faculty = FacultyProfile(id="faculty", account_id="faculty-account", employee_code="F-1", display_name="Faculty", department_id="department", designation="Mentor")
        provider = InternshipProvider(id="provider", company_name="Company")
        opportunity = InternshipOpportunity(id="opportunity", provider_id="provider", title="Intern", description="Role", location="Remote", stipend_amount=0, application_deadline=date(2027, 1, 1), is_active=True)
        application = InternshipApplication(id="application", opportunity_id="opportunity", student_id="student", status="OFFERED")
        placement = InternshipPlacement(id="placement", application_id="application", student_id="student", faculty_supervisor_id="faculty", start_date=date(2026, 10, 1), end_date=date(2027, 1, 1), status="ONGOING")
        file1 = StorageFile(id="file1", original_name="report.pdf", file_path="private/file1", file_size_bytes=10, mime_type="application/pdf", sha256_hash="a" * 64, uploaded_by_account_id="student-account")
        file2 = StorageFile(id="file2", original_name="report-v2.pdf", file_path="private/file2", file_size_bytes=12, mime_type="application/pdf", sha256_hash="b" * 64, uploaded_by_account_id="student-account")
        db.add_all([school, department, programme, year, cohort, student_account, faculty_account, student, faculty, provider, opportunity, application, placement, file1, file2])
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_report_submission_versions_are_immutable_after_submit(report_session):
    service = ReportService(report_session)
    report = await service.create("student-account", "placement", "Weekly report", "file1", "Initial draft")
    await service.submit(report.id, "student-account")
    with pytest.raises(ReportWorkflowError) as error:
        await service.add_version(report.id, "student-account", "file2", "Should not overwrite submitted version")
    assert error.value.status_code == 409
    faculty_review = await service.review(report.id, "faculty-account", "REVISION_REQUIRED", "Please revise the evidence and resubmit.")
    assert faculty_review.status == "REVISION_REQUIRED"
    assert faculty_review.review_feedback == "Please revise the evidence and resubmit."
    assert faculty_review.reviewed_by_account_id == "faculty-account"
    version = await service.add_version(report.id, "student-account", "file2", "Updated draft")
    assert version.version_number == 2
    resubmitted = await service.submit(report.id, "student-account")
    assert resubmitted.status == "SUBMITTED"


@pytest.mark.asyncio
async def test_report_cannot_be_created_for_another_students_placement(report_session):
    service = ReportService(report_session)
    with pytest.raises(ReportWorkflowError) as error:
        await service.create("faculty-account", "placement", "Not mine", "file1", None)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_only_assigned_supervisor_can_review(report_session):
    service = ReportService(report_session)
    report = await service.create("student-account", "placement", "Report", "file1", None)
    await service.submit(report.id, "student-account")
    with pytest.raises(ReportWorkflowError) as error:
        await service.review(report.id, "student-account", "APPROVED")
    assert error.value.status_code == 403


from sqlalchemy import select
from app.models.evaluation import GriffinEvaluation, GriffinEvaluationAttempt, ReportVersion
from app.modules.evaluations.adapter import GriffinIntegrationUnavailable
from app.modules.evaluations.service import EvaluationService, EvaluationWorkflowError


@pytest.mark.asyncio
async def test_missing_griffin_contract_is_recorded_as_failed_not_success(report_session):
    reports = ReportService(report_session)
    report = await reports.create("student-account", "placement", "Evaluation report", "file1", None)
    await reports.submit(report.id, "student-account")
    version = await report_session.scalar(select(ReportVersion).where(ReportVersion.submission_id == report.id))

    service = EvaluationService(report_session)
    with pytest.raises(EvaluationWorkflowError) as error:
        await service.request_evaluation(version.id, "faculty-account", "griffin-project", "griffin-report")
    assert error.value.status_code == 503

    evaluation = await report_session.scalar(select(GriffinEvaluation).where(GriffinEvaluation.report_version_id == version.id))
    attempt = await report_session.scalar(select(GriffinEvaluationAttempt).where(GriffinEvaluationAttempt.griffin_evaluation_id == evaluation.id))
    assert evaluation.current_status == "FAILED"
    assert attempt.execution_status == "FAILED"
    assert "contract" in attempt.error_message.lower()


@pytest.mark.asyncio
async def test_griffin_job_dispatch_accepts_only_a_valid_job_id(report_session):
    class WorkingTestAdapter:
        async def dispatch(self, **kwargs):
            return {"job_id": "job-test-123"}

    reports = ReportService(report_session)
    report = await reports.create("student-account", "placement", "Evaluation report", "file1", None)
    await reports.submit(report.id, "student-account")
    version = await report_session.scalar(select(ReportVersion).where(ReportVersion.submission_id == report.id))

    evaluation = await EvaluationService(report_session, adapter=WorkingTestAdapter()).request_evaluation(
        version.id, "faculty-account", "griffin-project", "griffin-report"
    )
    assert evaluation.current_status == "PROCESSING"
    assert evaluation.griffin_job_id == "job-test-123"


from app.models.institutions import Institution, InstitutionMembership
from app.modules.organizations.service import OrganizationService, OrganizationWorkflowError


@pytest.mark.asyncio
async def test_team_and_campaign_workflows_are_institution_scoped(report_session):
    school = await report_session.get(School, "school")
    school.institution_id = "institution"
    report_session.add(Institution(id="institution", name="Institute", slug="institute", status="ACTIVE", created_by_account_id="faculty-account"))
    report_session.add(InstitutionMembership(institution_id="institution", account_id="faculty-account", role="INSTITUTION_ADMIN", status="ACTIVE"))
    await report_session.commit()

    service = OrganizationService(report_session)
    team = await service.create_team("institution", "faculty-account", "department", "Capstone Team")
    member = await service.add_team_member("institution", "faculty-account", team.id, "student-account", "LEAD")
    assert member.status == "ACTIVE"
    assert member.role_in_team == "LEAD"
    assert [item.id for item in await service.list_teams("institution", "faculty-account")] == [team.id]

    campaign = await service.create_campaign("institution", "faculty-account", "Autumn Assessment", None, date(2026, 10, 1), date(2026, 12, 1))
    assignment = await service.assign_faculty("institution", "faculty-account", campaign.id, "faculty-account", "MENTOR")
    assert assignment.assignment_status == "assigned"
    with pytest.raises(OrganizationWorkflowError) as error:
        await service.assign_faculty("institution", "faculty-account", campaign.id, "faculty-account", "DUPLICATE")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_team_cannot_reference_department_from_another_institution(report_session):
    school = await report_session.get(School, "school")
    school.institution_id = "institution"
    report_session.add(Institution(id="institution", name="Institute", slug="institute", status="ACTIVE", created_by_account_id="faculty-account"))
    report_session.add(InstitutionMembership(institution_id="institution", account_id="faculty-account", role="INSTITUTION_ADMIN", status="ACTIVE"))
    await report_session.commit()
    service = OrganizationService(report_session)
    with pytest.raises(OrganizationWorkflowError) as error:
        await service.create_team("institution", "faculty-account", "department-not-here", "Bad Team")
    assert error.value.status_code == 422


from app.modules.reports.service import ReportRequirementService


@pytest.mark.asyncio
async def test_institution_report_requirement_is_visible_and_linked_to_student_submission(report_session):
    school = await report_session.get(School, "school")
    school.institution_id = "institution"
    report_session.add(Institution(id="institution", name="Institute", slug="institute", status="ACTIVE", created_by_account_id="faculty-account"))
    report_session.add(InstitutionMembership(institution_id="institution", account_id="faculty-account", role="INSTITUTION_ADMIN", status="ACTIVE"))
    await report_session.commit()

    requirements = ReportRequirementService(report_session)
    requirement = await requirements.create("institution", "faculty-account", "Final internship report", "Final report PDF", date(2027, 2, 1), True)
    visible = await requirements.list_for_student("student-account")
    assert len(visible) == 1
    assert visible[0]["requirement"].id == requirement.id
    assert visible[0]["submission_status"] is None

    report = await ReportService(report_session).create("student-account", "placement", "Final report", "file1", None, requirement.id)
    visible_after_submit = await requirements.list_for_student("student-account")
    assert report.requirement_id == requirement.id
    assert visible_after_submit[0]["submission_status"] == "DRAFT"


@pytest.mark.asyncio
async def test_requirement_deadline_is_enforced(report_session):
    school = await report_session.get(School, "school")
    school.institution_id = "institution"
    report_session.add(Institution(id="institution", name="Institute", slug="institute", status="ACTIVE", created_by_account_id="faculty-account"))
    report_session.add(InstitutionMembership(institution_id="institution", account_id="faculty-account", role="INSTITUTION_ADMIN", status="ACTIVE"))
    await report_session.commit()
    requirement = await ReportRequirementService(report_session).create(
        "institution", "faculty-account", "Expired report", None, date(2020, 1, 1), True
    )
    with pytest.raises(ReportWorkflowError) as error:
        await ReportService(report_session).create("student-account", "placement", "Expired", "file1", None, requirement.id)
    assert error.value.status_code == 409

@pytest.mark.asyncio
async def test_report_and_presentation_are_linked_to_the_same_immutable_version(report_session):
    service = ReportService(report_session)
    report = await service.create(
        "student-account", "placement", "Final assessment package", "file1",
        "Report and presentation", presentation_file_id="file2",
    )
    version = await report_session.scalar(
        select(ReportVersion).where(ReportVersion.submission_id == report.id)
    )
    assert version is not None
    assert version.file_id == "file1"
    assert version.presentation_file_id == "file2"

    # A presentation uploaded by a different account must not be attachable.
    report_session.add(StorageFile(
        id="foreign-presentation", original_name="presentation.pdf",
        file_path="private/foreign-presentation", file_size_bytes=10,
        mime_type="application/pdf", sha256_hash="c" * 64,
        uploaded_by_account_id="faculty-account",
    ))
    await report_session.commit()
    with pytest.raises(ReportWorkflowError) as error:
        await service.create(
            "student-account", "placement", "Invalid package", "file1", None,
            presentation_file_id="foreign-presentation",
        )
    assert error.value.status_code == 422

@pytest.mark.asyncio
async def test_presentation_attachment_is_downloadable_to_supervisor_and_not_deletable(report_session, tmp_path):
    from app.modules.storage.service import StorageService, StorageWorkflowError

    reports = ReportService(report_session)
    report = await reports.create(
        "student-account", "placement", "Assessment package", "file1", None,
        presentation_file_id="file2",
    )
    file_path = tmp_path / "private" / "file2"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"%PDF-1.7\npresentation")
    storage = StorageService(report_session, root=tmp_path)
    metadata, downloaded_path = await storage.get_download("file2", "faculty-account")
    assert metadata.id == "file2"
    assert downloaded_path == file_path

    with pytest.raises(StorageWorkflowError) as error:
        await storage.delete("file2", "student-account")
    assert error.value.status_code == 409



from app.models.curriculum import LearningOutcome
from app.modules.curriculum.service import CurriculumService, CurriculumWorkflowError


@pytest.mark.asyncio
async def test_curriculum_mapping_is_versioned_and_supervisor_review_is_auditable(report_session):
    from app.models.institutions import Institution

    school = await report_session.get(School, "school")
    school.institution_id = "institution"
    report_session.add(Institution(id="institution", name="Institute", slug="institute", status="ACTIVE", created_by_account_id="faculty-account"))
    await report_session.commit()
    report_session.add(LearningOutcome(id="outcome-1", institution_id="institution", programme_id=None,
        code="LO-1", title="Demonstrate practical skills", description="Apply concepts in practice",
        is_active=True, created_by_account_id="faculty-account"))
    await report_session.commit()

    reports = ReportService(report_session)
    report = await reports.create("student-account", "placement", "Assessment report", "file1", None, presentation_file_id="file2")
    await reports.submit(report.id, "student-account")
    curriculum = CurriculumService(report_session)
    submitted = await curriculum.create_mapping(report.id, "student-account", [
        {"learning_outcome_id": "outcome-1", "evidence_type": "PRESENTATION"}
    ])
    first = submitted["items"][0]
    assert first["status"] == "SUBMITTED"
    reviewed = await curriculum.review_mapping(report.id, first["id"], "faculty-account", "Evidence supports the outcome", [
        {"learning_outcome_id": "outcome-1", "evidence_status": "EVIDENCED", "reviewer_notes": "Clear demonstration"}
    ])
    assert [item["version_number"] for item in reviewed["items"]] == [2, 1]
    assert reviewed["items"][0]["items"][0]["evidence_status"] == "EVIDENCED"
    assert reviewed["items"][0]["reviewed_by_account_id"] == "faculty-account"


@pytest.mark.asyncio
async def test_curriculum_mapping_rejects_cross_institution_outcome(report_session):
    from app.models.institutions import Institution

    school = await report_session.get(School, "school")
    school.institution_id = "institution-a"
    report_session.add_all([
        Institution(id="institution-a", name="Institute A", slug="institute-a", status="ACTIVE", created_by_account_id="faculty-account"),
        Institution(id="institution-b", name="Institute B", slug="institute-b", status="ACTIVE", created_by_account_id="faculty-account"),
        LearningOutcome(id="outcome-b", institution_id="institution-b", programme_id=None, code="LO-X", title="Other institution", is_active=True, created_by_account_id="faculty-account"),
    ])
    await report_session.commit()
    reports = ReportService(report_session)
    report = await reports.create("student-account", "placement", "Assessment report", "file1", None)
    await reports.submit(report.id, "student-account")
    with pytest.raises(CurriculumWorkflowError) as error:
        await CurriculumService(report_session).create_mapping(report.id, "student-account", [
            {"learning_outcome_id": "outcome-b", "evidence_type": "REPORT"}
        ])
    assert error.value.status_code == 422
