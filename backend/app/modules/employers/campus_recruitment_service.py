"""Campus recruitment use cases and authorization invariants."""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import AcademicYear, Cohort, Department, Programme, School, StudentProfile
from app.models.employers import EmployerOrganization
from app.models.institutions import Institution
from app.models.internship import InternshipOpportunity, InternshipProvider
from app.models.recruitment import (
    RecruitmentDrive, RecruitmentDriveCohortTarget, RecruitmentDriveGraduationYearTarget,
    RecruitmentDriveOpportunity, RecruitmentDriveParticipation, RecruitmentDriveProgrammeTarget,
)
from app.modules.audit.service import AuditService
from app.modules.employers.service import EmployerError, EmployerService
from app.modules.institutions.service import InstitutionAccessError, InstitutionService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CampusRecruitmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.institutions = InstitutionService(db)
        self.employers = EmployerService(db)

    async def _drive(self, drive_id: str) -> RecruitmentDrive:
        item = await self.db.get(RecruitmentDrive, drive_id)
        if item is None:
            raise EmployerError(404, "Recruitment drive not found")
        return item

    async def _admin(self, institution_id: str, actor_id: str) -> None:
        try:
            await self.institutions.require_admin(institution_id, actor_id)
        except InstitutionAccessError as exc:
            raise EmployerError(exc.status_code, exc.message) from None

    async def _institution_academic_scope(self, institution_id: str) -> set[str]:
        stmt = select(Programme.id).join(Department, Department.id == Programme.department_id).join(
            School, School.id == Department.school_id
        ).where(School.institution_id == institution_id, School.is_active.is_(True),
            Department.is_active.is_(True), Programme.is_active.is_(True))
        return set((await self.db.scalars(stmt)).all())

    async def _replace_targets(self, drive: RecruitmentDrive, programmes: list[str], cohorts: list[str], years: list[int]) -> None:
        programmes, cohorts, years = list(dict.fromkeys(programmes)), list(dict.fromkeys(cohorts)), list(dict.fromkeys(years))
        valid_programmes = await self._institution_academic_scope(drive.institution_id)
        if not set(programmes) <= valid_programmes:
            raise EmployerError(422, "Every targeted programme must be active and belong to the drive institution")
        if cohorts:
            rows = await self.db.execute(select(Cohort.id, Programme.id, AcademicYear.institution_id)
                .join(Programme, Programme.id == Cohort.programme_id)
                .join(Department, Department.id == Programme.department_id)
                .join(School, School.id == Department.school_id)
                .join(AcademicYear, AcademicYear.id == Cohort.academic_year_id)
                .where(Cohort.id.in_(cohorts), School.institution_id == drive.institution_id,
                    School.is_active.is_(True), Department.is_active.is_(True), Programme.is_active.is_(True)))
            records = list(rows.all())
            if len(records) != len(cohorts) or any(year_institution not in (None, drive.institution_id) for _, _, year_institution in records):
                raise EmployerError(422, "Every targeted cohort and academic year must belong to the drive institution")
            if programmes and any(programme_id not in programmes for _, programme_id, _ in records):
                raise EmployerError(422, "Each targeted cohort must use one of the targeted programmes")
        if drive.academic_year_id:
            year = await self.db.get(AcademicYear, drive.academic_year_id)
            if year is None or year.institution_id not in (None, drive.institution_id):
                raise EmployerError(422, "Academic year must belong to the drive institution")
        for model in (RecruitmentDriveProgrammeTarget, RecruitmentDriveCohortTarget, RecruitmentDriveGraduationYearTarget):
            await self.db.execute(model.__table__.delete().where(model.drive_id == drive.id))
        self.db.add_all([RecruitmentDriveProgrammeTarget(drive_id=drive.id, programme_id=value) for value in programmes])
        self.db.add_all([RecruitmentDriveCohortTarget(drive_id=drive.id, cohort_id=value) for value in cohorts])
        self.db.add_all([RecruitmentDriveGraduationYearTarget(drive_id=drive.id, graduation_year=value) for value in years])
        await self.db.flush()

    async def create_drive(self, institution_id: str, actor_id: str, data: dict) -> RecruitmentDrive:
        await self._admin(institution_id, actor_id)
        if data.get("starts_on") and data.get("ends_on") and data["ends_on"] < data["starts_on"]:
            raise EmployerError(422, "ends_on must be on or after starts_on")
        if data.get("application_opens_at") and data.get("application_closes_at") and data["application_closes_at"] <= data["application_opens_at"]:
            raise EmployerError(422, "application_closes_at must be after application_opens_at")
        fields = {k: v for k, v in data.items() if k not in {"programme_ids", "cohort_ids", "graduation_years"}}
        item = RecruitmentDrive(id=str(uuid4()), institution_id=institution_id, created_by_account_id=actor_id, status="DRAFT", **fields)
        self.db.add(item)
        await self.db.flush()
        try:
            await self._replace_targets(item, data.get("programme_ids", []), data.get("cohort_ids", []), data.get("graduation_years", []))
            AuditService(self.db).record(actor_id, institution_id, "recruitment.drive_created", "recruitment_drive", item.id, {"name": item.name})
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise EmployerError(409, "Recruitment drive conflicts with existing data") from None
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(item)
        return item

    async def _target_ids(self, drive_id: str) -> dict:
        programmes = list((await self.db.scalars(select(RecruitmentDriveProgrammeTarget.programme_id).where(RecruitmentDriveProgrammeTarget.drive_id == drive_id))).all())
        cohorts = list((await self.db.scalars(select(RecruitmentDriveCohortTarget.cohort_id).where(RecruitmentDriveCohortTarget.drive_id == drive_id))).all())
        years = list((await self.db.scalars(select(RecruitmentDriveGraduationYearTarget.graduation_year).where(RecruitmentDriveGraduationYearTarget.drive_id == drive_id))).all())
        return {"programme_ids": programmes, "cohort_ids": cohorts, "graduation_years": years}

    async def drive_view(self, drive: RecruitmentDrive) -> dict:
        return {"id": drive.id, "institution_id": drive.institution_id, "academic_year_id": drive.academic_year_id,
            "name": drive.name, "description": drive.description, "starts_on": drive.starts_on, "ends_on": drive.ends_on,
            "application_opens_at": drive.application_opens_at, "application_closes_at": drive.application_closes_at,
            "status": drive.status, "created_by_account_id": drive.created_by_account_id,
            "created_at": drive.created_at, "updated_at": drive.updated_at, **(await self._target_ids(drive.id))}

    async def list_drives(self, institution_id: str, actor_id: str, limit: int = 50, offset: int = 0) -> list[RecruitmentDrive]:
        await self._admin(institution_id, actor_id)
        return list((await self.db.scalars(select(RecruitmentDrive).where(RecruitmentDrive.institution_id == institution_id)
            .order_by(RecruitmentDrive.created_at.desc()).limit(limit).offset(offset))).all())

    async def get_drive(self, drive_id: str, actor_id: str) -> RecruitmentDrive:
        drive = await self._drive(drive_id)
        await self._admin(drive.institution_id, actor_id)
        return drive

    async def update_drive(self, drive_id: str, actor_id: str, data: dict) -> RecruitmentDrive:
        drive = await self.get_drive(drive_id, actor_id)
        if drive.status != "DRAFT":
            raise EmployerError(409, "Only draft recruitment drives can be edited")
        target_keys = {"programme_ids", "cohort_ids", "graduation_years"}
        for key, value in data.items():
            if key not in target_keys:
                setattr(drive, key, value)
        if drive.starts_on and drive.ends_on and drive.ends_on < drive.starts_on:
            raise EmployerError(422, "ends_on must be on or after starts_on")
        if drive.application_opens_at and drive.application_closes_at and drive.application_closes_at <= drive.application_opens_at:
            raise EmployerError(422, "application close must follow open")
        if any(key in data for key in target_keys):
            targets = await self._target_ids(drive.id)
            await self._replace_targets(drive, data.get("programme_ids", targets["programme_ids"]),
                data.get("cohort_ids", targets["cohort_ids"]), data.get("graduation_years", targets["graduation_years"]))
        await self.db.commit()
        await self.db.refresh(drive)
        return drive

    async def transition_drive(self, drive_id: str, actor_id: str, action: str) -> RecruitmentDrive:
        drive = await self.get_drive(drive_id, actor_id)
        transitions = {"publish": {"DRAFT": "PUBLISHED"}, "activate": {"PUBLISHED": "ACTIVE"},
            "complete": {"ACTIVE": "COMPLETED"}, "cancel": {"DRAFT": "CANCELLED", "PUBLISHED": "CANCELLED", "ACTIVE": "CANCELLED"},
            "archive": {"COMPLETED": "ARCHIVED", "CANCELLED": "ARCHIVED"}}
        new_status = transitions.get(action, {}).get(drive.status)
        if new_status is None:
            raise EmployerError(409, f"Cannot {action} a drive in {drive.status} state")
        if action == "publish" and (not drive.name.strip() or not (drive.description or "").strip()):
            raise EmployerError(422, "A drive requires a name and description before publication")
        drive.status = new_status
        AuditService(self.db).record(actor_id, drive.institution_id, f"recruitment.drive_{action}d", "recruitment_drive", drive.id, {"status": new_status})
        await self.db.commit()
        await self.db.refresh(drive)
        return drive

    async def invite_employer(self, drive_id: str, actor_id: str, organization_id: str):
        drive = await self.get_drive(drive_id, actor_id)
        if drive.status not in {"DRAFT", "PUBLISHED", "ACTIVE"}:
            raise EmployerError(409, "Employers cannot be invited to a closed drive")
        if await self.db.get(EmployerOrganization, organization_id) is None:
            raise EmployerError(404, "Employer organization not found")
        item = RecruitmentDriveParticipation(id=str(uuid4()), drive_id=drive.id, organization_id=organization_id,
            invited_by_account_id=actor_id, status="INVITED")
        self.db.add(item)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise EmployerError(409, "This employer already has a participation record for the drive") from None
        await self.db.refresh(item)
        return item

    async def list_employer_invitations(self, organization_id: str, actor_id: str):
        organization, _ = await self.employers.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"})
        if organization.status != "ACTIVE":
            raise EmployerError(403, "Verified active employer organization required")
        return list((await self.db.scalars(select(RecruitmentDriveParticipation).where(
            RecruitmentDriveParticipation.organization_id == organization_id,
            RecruitmentDriveParticipation.status == "INVITED").order_by(RecruitmentDriveParticipation.invited_at.desc()))).all())

    async def respond_invitation(self, organization_id: str, actor_id: str, participation_id: str, decision: str):
        org, _ = await self.employers.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"})
        if org.status != "ACTIVE":
            raise EmployerError(403, "Verified active employer organization required")
        item = await self.db.scalar(select(RecruitmentDriveParticipation).where(
            RecruitmentDriveParticipation.id == participation_id, RecruitmentDriveParticipation.organization_id == organization_id))
        if item is None:
            raise EmployerError(404, "Drive invitation not found")
        if item.status != "INVITED":
            raise EmployerError(409, "This invitation has already been answered")
        if decision not in {"ACCEPTED", "DECLINED"}:
            raise EmployerError(422, "Decision must be ACCEPTED or DECLINED")
        drive = await self._drive(item.drive_id)
        if drive.status not in {"DRAFT", "PUBLISHED", "ACTIVE"}:
            raise EmployerError(409, "This drive no longer accepts employer participation")
        item.status, item.responded_by_account_id, item.responded_at = decision, actor_id, _now()
        AuditService(self.db).record(actor_id, None, "recruitment.participation_responded", "recruitment_drive_participation", item.id, {"decision": decision, "drive_id": drive.id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def associate_opportunity(self, organization_id: str, actor_id: str, drive_id: str, opportunity_id: str):
        org, _ = await self.employers.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"})
        if org.status != "ACTIVE":
            raise EmployerError(403, "Verified active employer organization required")
        drive = await self._drive(drive_id)
        if drive.status not in {"PUBLISHED", "ACTIVE"}:
            raise EmployerError(409, "Jobs can only be associated with published or active drives")
        participation = await self.db.scalar(select(RecruitmentDriveParticipation).where(
            RecruitmentDriveParticipation.drive_id == drive.id, RecruitmentDriveParticipation.organization_id == organization_id,
            RecruitmentDriveParticipation.status == "ACCEPTED"))
        if participation is None:
            raise EmployerError(403, "Your organization must have accepted this drive invitation")
        opportunity = await self.db.scalar(select(InternshipOpportunity).join(
            InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id).where(
            InternshipOpportunity.id == opportunity_id, InternshipProvider.employer_organization_id == organization_id))
        if opportunity is None:
            raise EmployerError(404, "Opportunity not found for this employer organization")
        if not opportunity.is_active or opportunity.lifecycle_status not in {"PUBLISHED", "ACTIVE"}:
            raise EmployerError(409, "Only published, active opportunities can be associated")
        item = RecruitmentDriveOpportunity(drive_id=drive.id, opportunity_id=opportunity.id, added_by_account_id=actor_id)
        self.db.add(item)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise EmployerError(409, "Opportunity is already associated with this drive") from None
        await self.db.refresh(item)
        return item

    async def eligibility(self, account_id: str, drive_id: str, opportunity_id: str | None = None) -> dict:
        drive = await self._drive(drive_id)
        student = await self.db.scalar(select(StudentProfile).where(StudentProfile.account_id == account_id))
        if student is None:
            return {"status": "incomplete", "reason_codes": ["ACADEMIC_DATA_MISSING"]}
        row = (await self.db.execute(select(Cohort, Programme, Department, School, AcademicYear)
            .join(Programme, Programme.id == Cohort.programme_id).join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id).join(AcademicYear, AcademicYear.id == Cohort.academic_year_id)
            .where(Cohort.id == student.cohort_id))).first()
        if row is None:
            return {"status": "incomplete", "reason_codes": ["ACADEMIC_DATA_MISSING"]}
        cohort, programme, department, school, academic_year = row
        reasons = []
        if school.institution_id != drive.institution_id:
            reasons.append("INSTITUTION_MISMATCH")
        if drive.status != "ACTIVE":
            reasons.append("DRIVE_NOT_ACTIVE")
        now = _now()
        if drive.application_opens_at and now < drive.application_opens_at:
            reasons.append("APPLICATION_WINDOW_NOT_OPEN")
        if drive.application_closes_at and now > drive.application_closes_at:
            reasons.append("APPLICATION_WINDOW_CLOSED")
        target_programmes = set((await self.db.scalars(select(RecruitmentDriveProgrammeTarget.programme_id).where(RecruitmentDriveProgrammeTarget.drive_id == drive.id))).all())
        target_cohorts = set((await self.db.scalars(select(RecruitmentDriveCohortTarget.cohort_id).where(RecruitmentDriveCohortTarget.drive_id == drive.id))).all())
        target_years = set((await self.db.scalars(select(RecruitmentDriveGraduationYearTarget.graduation_year).where(RecruitmentDriveGraduationYearTarget.drive_id == drive.id))).all())
        if target_programmes and programme.id not in target_programmes:
            reasons.append("PROGRAMME_NOT_TARGETED")
        if target_cohorts and cohort.id not in target_cohorts:
            reasons.append("COHORT_NOT_TARGETED")
        if target_years and cohort.graduation_year not in target_years:
            reasons.append("GRADUATION_YEAR_MISMATCH")
        if opportunity_id:
            association = await self.db.scalar(select(RecruitmentDriveOpportunity).where(
                RecruitmentDriveOpportunity.drive_id == drive.id, RecruitmentDriveOpportunity.opportunity_id == opportunity_id))
            if association is None:
                reasons.append("OPPORTUNITY_NOT_IN_DRIVE")
            else:
                organization_id = await self.db.scalar(select(InternshipProvider.employer_organization_id).join(
                    InternshipOpportunity, InternshipOpportunity.provider_id == InternshipProvider.id).where(
                    InternshipOpportunity.id == opportunity_id))
                participation = await self.db.scalar(select(RecruitmentDriveParticipation).where(
                    RecruitmentDriveParticipation.drive_id == drive.id, RecruitmentDriveParticipation.organization_id == organization_id,
                    RecruitmentDriveParticipation.status == "ACCEPTED"))
                organization = await self.db.get(EmployerOrganization, organization_id) if organization_id else None
                if participation is None or organization is None or organization.status != "ACTIVE":
                    reasons.append("EMPLOYER_NOT_ELIGIBLE")
        blocking = {"INSTITUTION_MISMATCH", "PROGRAMME_NOT_TARGETED", "COHORT_NOT_TARGETED", "GRADUATION_YEAR_MISMATCH",
            "OPPORTUNITY_NOT_IN_DRIVE", "EMPLOYER_NOT_ELIGIBLE", "DRIVE_NOT_ACTIVE", "APPLICATION_WINDOW_CLOSED"}
        status = "eligible" if not reasons else ("ineligible" if any(code in blocking for code in reasons) else "pending_verification")
        return {"status": status, "reason_codes": reasons, "drive_id": drive.id, "opportunity_id": opportunity_id,
            "institution_id": school.institution_id, "programme_id": programme.id, "cohort_id": cohort.id,
            "graduation_year": cohort.graduation_year}

    async def student_drives(self, account_id: str, limit: int, offset: int) -> list[dict]:
        student = await self.db.scalar(select(StudentProfile).where(StudentProfile.account_id == account_id))
        if student is None:
            return []
        row = (await self.db.execute(select(School.institution_id).join(Department, Department.school_id == School.id)
            .join(Programme, Programme.department_id == Department.id).join(Cohort, Cohort.programme_id == Programme.id)
            .where(Cohort.id == student.cohort_id))).first()
        if row is None or row[0] is None:
            return []
        drives = list((await self.db.scalars(select(RecruitmentDrive).where(
            RecruitmentDrive.institution_id == row[0], RecruitmentDrive.status == "ACTIVE")
            .order_by(RecruitmentDrive.created_at.desc()).limit(limit).offset(offset))).all())
        result = []
        for drive in drives:
            eligibility = await self.eligibility(account_id, drive.id)
            if eligibility["status"] == "eligible":
                public_drive = await self.drive_view(drive)
                for key in ("programme_ids", "cohort_ids", "graduation_years"):
                    public_drive.pop(key, None)
                result.append({**public_drive, "eligibility": eligibility})
        return result

    async def apply_guard(self, account_id: str, opportunity_id: str) -> None:
        drive_ids = list((await self.db.scalars(select(RecruitmentDriveOpportunity.drive_id).join(
            RecruitmentDrive, RecruitmentDrive.id == RecruitmentDriveOpportunity.drive_id).where(
            RecruitmentDriveOpportunity.opportunity_id == opportunity_id,
            RecruitmentDrive.status.in_({"PUBLISHED", "ACTIVE"})))).all())
        if not drive_ids:
            return
        results = [await self.eligibility(account_id, drive_id, opportunity_id) for drive_id in drive_ids]
        if any(result["status"] == "eligible" for result in results):
            return
        reasons = sorted({code for result in results for code in result["reason_codes"]})
        raise EmployerError(403 if any(result["status"] == "ineligible" for result in results) else 409,
            "Student is not eligible to apply to this campus opportunity: " + ",".join(reasons))

    async def revoke_participation(self, drive_id: str, actor_id: str, organization_id: str):
        drive = await self.get_drive(drive_id, actor_id)
        item = await self.db.scalar(select(RecruitmentDriveParticipation).where(
            RecruitmentDriveParticipation.drive_id == drive.id,
            RecruitmentDriveParticipation.organization_id == organization_id))
        if item is None:
            raise EmployerError(404, "Employer participation not found")
        if item.status == "REVOKED":
            raise EmployerError(409, "Employer participation is already revoked")
        item.status = "REVOKED"
        item.responded_by_account_id = actor_id
        item.responded_at = _now()
        AuditService(self.db).record(actor_id, drive.institution_id, "recruitment.participation_revoked",
            "recruitment_drive_participation", item.id, {"organization_id": organization_id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def remove_opportunity_association(self, organization_id: str, actor_id: str, drive_id: str, opportunity_id: str) -> None:
        org, _ = await self.employers.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"})
        if org.status != "ACTIVE":
            raise EmployerError(403, "Verified active employer organization required")
        drive = await self._drive(drive_id)
        item = await self.db.scalar(select(RecruitmentDriveOpportunity).where(
            RecruitmentDriveOpportunity.drive_id == drive.id,
            RecruitmentDriveOpportunity.opportunity_id == opportunity_id))
        if item is None:
            raise EmployerError(404, "Opportunity association not found")
        owner_id = await self.db.scalar(select(InternshipProvider.employer_organization_id).join(
            InternshipOpportunity, InternshipOpportunity.provider_id == InternshipProvider.id).where(
            InternshipOpportunity.id == opportunity_id))
        if owner_id != organization_id:
            raise EmployerError(404, "Opportunity association not found")
        await self.db.delete(item)
        await self.db.commit()

    async def student_opportunities(self, account_id: str, drive_id: str, limit: int, offset: int) -> list[dict]:
        drive = await self._drive(drive_id)
        if drive.status != "ACTIVE":
            return []
        rows = list((await self.db.execute(select(InternshipOpportunity, InternshipProvider).join(
            RecruitmentDriveOpportunity, RecruitmentDriveOpportunity.opportunity_id == InternshipOpportunity.id)
            .join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id)
            .where(RecruitmentDriveOpportunity.drive_id == drive.id, InternshipOpportunity.is_active.is_(True),
                InternshipOpportunity.lifecycle_status.in_({"PUBLISHED", "ACTIVE"}))
            .order_by(InternshipOpportunity.application_deadline.asc()).limit(limit).offset(offset))).all())
        result = []
        for opportunity, provider in rows:
            eligibility = await self.eligibility(account_id, drive.id, opportunity.id)
            if eligibility["status"] == "eligible":
                result.append({"id": opportunity.id, "title": opportunity.title, "summary": opportunity.summary,
                    "description": opportunity.description, "location": opportunity.location,
                    "opportunity_type": opportunity.opportunity_type, "employment_type": opportunity.employment_type,
                    "work_mode": opportunity.work_mode, "application_deadline": opportunity.application_deadline,
                    "company": provider.company_name, "eligibility": {"status": "eligible", "reason_codes": []}})
        return result

    async def student_application_eligibility(self, account_id: str, opportunity_id: str) -> dict:
        drive_ids = list((await self.db.scalars(select(RecruitmentDriveOpportunity.drive_id).join(
            RecruitmentDrive, RecruitmentDrive.id == RecruitmentDriveOpportunity.drive_id).where(
            RecruitmentDriveOpportunity.opportunity_id == opportunity_id,
            RecruitmentDrive.status.in_({"PUBLISHED", "ACTIVE"})))).all())
        if not drive_ids:
            return {"status": "eligible", "reason_codes": [], "opportunity_id": opportunity_id, "scope": "public"}
        results = [await self.eligibility(account_id, drive_id, opportunity_id) for drive_id in drive_ids]
        eligible = next((result for result in results if result["status"] == "eligible"), None)
        if eligible:
            return {**eligible, "scope": "campus"}
        return {"status": "ineligible" if any(result["status"] == "ineligible" for result in results) else "pending_verification",
            "reason_codes": sorted({code for result in results for code in result["reason_codes"]}),
            "opportunity_id": opportunity_id, "scope": "campus"}
