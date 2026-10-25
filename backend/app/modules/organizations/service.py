"""Institution-scoped team and assessment campaign workflows."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account, Cohort, Department, FacultyProfile, Programme, School, StudentProfile
from app.models.organizations import AssessmentCampaign, FacultyAssessmentAssignment, Team, TeamMembership
from app.modules.institutions.service import InstitutionAccessError, InstitutionService
from app.modules.audit.service import AuditService
from app.services.email import send_workflow_notification


class OrganizationWorkflowError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.institutions = InstitutionService(db)

    async def _team(self, institution_id: str, team_id: str) -> Team:
        team = await self.db.get(Team, team_id)
        if team is None:
            raise OrganizationWorkflowError(404, "Team not found")
        school = await self.db.scalar(select(School).join(Department, Department.school_id == School.id).where(
            Department.id == team.department_id, School.institution_id == institution_id
        ))
        if school is None:
            raise OrganizationWorkflowError(404, "Team not found in this institution")
        return team

    async def _account_in_institution(self, account_id: str, institution_id: str) -> bool:
        student = await self.db.scalar(
            select(StudentProfile.id).join(Cohort, Cohort.id == StudentProfile.cohort_id)
            .join(Programme, Programme.id == Cohort.programme_id)
            .join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id)
            .where(StudentProfile.account_id == account_id, School.institution_id == institution_id)
        )
        if student is not None:
            return True
        faculty = await self.db.scalar(
            select(FacultyProfile.id).join(Department, Department.id == FacultyProfile.department_id)
            .join(School, School.id == Department.school_id)
            .where(FacultyProfile.account_id == account_id, School.institution_id == institution_id)
        )
        return faculty is not None

    async def create_team(self, institution_id: str, actor_id: str, department_id: str, name: str) -> Team:
        await self.institutions.require_admin(institution_id, actor_id)
        school = await self.db.scalar(select(School).join(Department, Department.school_id == School.id).where(
            Department.id == department_id, School.institution_id == institution_id
        ))
        if school is None:
            raise OrganizationWorkflowError(422, "Department must belong to this institution")
        item = Team(id=str(uuid4()), name=name.strip(), department_id=department_id, created_by_account_id=actor_id)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "team.created", "team", item.id, {"department_id": department_id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_teams(self, institution_id: str, actor_id: str) -> list[Team]:
        await self.institutions.membership(institution_id, actor_id)
        result = await self.db.execute(select(Team).join(Department, Department.id == Team.department_id)
            .join(School, School.id == Department.school_id).where(School.institution_id == institution_id)
            .order_by(Team.name))
        return list(result.scalars().all())

    async def add_team_member(self, institution_id: str, actor_id: str, team_id: str, account_id: str, role: str) -> TeamMembership:
        await self.institutions.require_admin(institution_id, actor_id)
        team = await self._team(institution_id, team_id)
        if role not in {"LEAD", "MEMBER"}:
            raise OrganizationWorkflowError(422, "Team role must be LEAD or MEMBER")
        if not await self._account_in_institution(account_id, institution_id):
            raise OrganizationWorkflowError(422, "Team member must be a student or faculty member in this institution")
        item = await self.db.get(TeamMembership, (team.id, account_id))
        if item is None:
            item = TeamMembership(team_id=team.id, account_id=account_id, role_in_team=role, status="ACTIVE")
            self.db.add(item)
        else:
            item.role_in_team, item.status = role, "ACTIVE"
        AuditService(self.db).record(actor_id, institution_id, "team.member_added", "team_membership", account_id, {"team_id": team.id, "role": role})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_team_members(self, institution_id: str, actor_id: str, team_id: str) -> list[TeamMembership]:
        await self.institutions.membership(institution_id, actor_id)
        team = await self._team(institution_id, team_id)
        result = await self.db.execute(select(TeamMembership).where(
            TeamMembership.team_id == team.id, TeamMembership.status == "ACTIVE"
        ).order_by(TeamMembership.joined_at))
        return list(result.scalars().all())

    async def remove_team_member(self, institution_id: str, actor_id: str, team_id: str, account_id: str) -> None:
        await self.institutions.require_admin(institution_id, actor_id)
        team = await self._team(institution_id, team_id)
        item = await self.db.get(TeamMembership, (team.id, account_id))
        if item is None or item.status != "ACTIVE":
            raise OrganizationWorkflowError(404, "Active team membership not found")
        item.status = "REMOVED"
        AuditService(self.db).record(actor_id, institution_id, "team.member_removed", "team_membership", account_id, {"team_id": team.id})
        await self.db.commit()

    async def create_campaign(self, institution_id: str, actor_id: str, title: str, description, start_date, end_date) -> AssessmentCampaign:
        await self.institutions.require_admin(institution_id, actor_id)
        if end_date < start_date:
            raise OrganizationWorkflowError(422, "Campaign end_date must be on or after start_date")
        item = AssessmentCampaign(institution_id=institution_id, title=title.strip(),
                                  description=description, start_date=start_date, end_date=end_date, is_active=True)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "assessment.campaign_created", "assessment_campaign", item.id, {"title": item.title})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_campaigns(self, institution_id: str, actor_id: str) -> list[AssessmentCampaign]:
        await self.institutions.membership(institution_id, actor_id)
        result = await self.db.execute(select(AssessmentCampaign).where(
            AssessmentCampaign.institution_id == institution_id
        ).order_by(AssessmentCampaign.start_date.desc()))
        return list(result.scalars().all())

    async def set_campaign_active(self, institution_id: str, actor_id: str, campaign_id: str, is_active: bool) -> AssessmentCampaign:
        await self.institutions.require_admin(institution_id, actor_id)
        item = await self.db.get(AssessmentCampaign, campaign_id)
        if item is None or item.institution_id != institution_id:
            raise OrganizationWorkflowError(404, "Campaign not found in this institution")
        item.is_active = is_active
        AuditService(self.db).record(actor_id, institution_id, "assessment.campaign_status_changed", "assessment_campaign", item.id, {"is_active": is_active})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def assign_faculty(self, institution_id: str, actor_id: str, campaign_id: str, faculty_account_id: str, selection_key: str | None) -> FacultyAssessmentAssignment:
        await self.institutions.require_admin(institution_id, actor_id)
        campaign = await self.db.get(AssessmentCampaign, campaign_id)
        if campaign is None or campaign.institution_id != institution_id:
            raise OrganizationWorkflowError(404, "Campaign not found in this institution")
        if not campaign.is_active:
            raise OrganizationWorkflowError(409, "Cannot assign faculty to an inactive campaign")
        faculty = await self.db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == faculty_account_id))
        if faculty is None or not await self._account_in_institution(faculty_account_id, institution_id):
            raise OrganizationWorkflowError(422, "Faculty member must belong to this institution")
        existing = await self.db.scalar(select(FacultyAssessmentAssignment.id).where(
            FacultyAssessmentAssignment.campaign_id == campaign_id,
            FacultyAssessmentAssignment.faculty_id == faculty.id,
        ))
        if existing is not None:
            raise OrganizationWorkflowError(409, "Faculty member is already assigned to this campaign")
        item = FacultyAssessmentAssignment(campaign_id=campaign.id, faculty_id=faculty.id, selection_key=selection_key.strip() if selection_key else None)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "assessment.faculty_assigned", "faculty_assessment_assignment", item.id, {"campaign_id": campaign_id, "faculty_id": faculty.id})
        await self.db.commit()
        await self.db.refresh(item)
        faculty_account = await self.db.get(Account, faculty.account_id)
        if faculty_account is not None and faculty_account.email:
            try:
                await send_workflow_notification(faculty_account.email, "Kairos assessment assignment", "You have been assigned to an assessment campaign in Kairos.")
            except Exception:
                # Notification failure must not undo a committed assignment.
                pass
        return item

    async def list_assignments(self, institution_id: str, actor_id: str, campaign_id: str) -> list[FacultyAssessmentAssignment]:
        await self.institutions.membership(institution_id, actor_id)
        campaign = await self.db.get(AssessmentCampaign, campaign_id)
        if campaign is None or campaign.institution_id != institution_id:
            raise OrganizationWorkflowError(404, "Campaign not found in this institution")
        result = await self.db.execute(select(FacultyAssessmentAssignment).where(
            FacultyAssessmentAssignment.campaign_id == campaign_id
        ).order_by(FacultyAssessmentAssignment.assigned_at))
        return list(result.scalars().all())


    async def update_assignment(self, institution_id: str, actor_id: str, campaign_id: str, assignment_id: str,
                                target_status: str) -> FacultyAssessmentAssignment:
        campaign = await self.db.get(AssessmentCampaign, campaign_id)
        if campaign is None or campaign.institution_id != institution_id:
            raise OrganizationWorkflowError(404, "Campaign not found in this institution")
        item = await self.db.get(FacultyAssessmentAssignment, assignment_id)
        if item is None or item.campaign_id != campaign.id:
            raise OrganizationWorkflowError(404, "Assignment not found in this campaign")
        faculty = await self.db.get(FacultyProfile, item.faculty_id)
        is_assigned_faculty = faculty is not None and faculty.account_id == actor_id
        is_admin = False
        try:
            await self.institutions.require_admin(institution_id, actor_id)
            is_admin = True
        except InstitutionAccessError:
            is_admin = False
        if not is_assigned_faculty and not is_admin:
            raise OrganizationWorkflowError(403, "Only the assigned faculty member or institution administrator may update this assignment")
        transitions = {"assigned": {"started"}, "started": {"submitted"}}
        if target_status not in transitions.get(item.assignment_status, set()):
            raise OrganizationWorkflowError(409, "Invalid assessment assignment status transition")
        item.assignment_status = target_status
        AuditService(self.db).record(actor_id, institution_id, "assessment.assignment_status_changed", "assessment_assignment", str(item.id), {"to": target_status})
        await self.db.commit()
        await self.db.refresh(item)
        return item
