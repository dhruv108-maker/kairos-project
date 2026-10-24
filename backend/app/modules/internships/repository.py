"""SQLAlchemy 2.0 async persistence queries for internship entities."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.academic import FacultyProfile, StudentProfile
from app.models.internship import InternshipApplication, InternshipOpportunity, InternshipPlacement, InternshipProvider
from app.models.recruitment import RecruitmentDrive, RecruitmentDriveOpportunity
from app.modules.shared.base_repository import BaseRepository

class InternshipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.providers = BaseRepository(session, InternshipProvider)
        self.opportunities = BaseRepository(session, InternshipOpportunity)
        self.applications = BaseRepository(session, InternshipApplication)
        self.placements = BaseRepository(session, InternshipPlacement)

    async def get_provider(self, provider_id: str): return await self.providers.get(provider_id)
    async def create_provider(self, provider: InternshipProvider): return await self.providers.add(provider)
    async def get_opportunity(self, opportunity_id: str): return await self.opportunities.get(opportunity_id)
    async def create_opportunity(self, opportunity: InternshipOpportunity): return await self.opportunities.add(opportunity)
    async def get_student_by_account(self, account_id: str) -> StudentProfile | None:
        return await self.session.scalar(select(StudentProfile).where(StudentProfile.account_id == account_id))
    async def get_application(self, application_id: str): return await self.applications.get(application_id)
    async def find_application(self, opportunity_id: str, student_id: str):
        return await self.session.scalar(select(InternshipApplication).where(InternshipApplication.opportunity_id == opportunity_id, InternshipApplication.student_id == student_id))
    async def list_active_opportunities(self, *, query: str | None = None, location: str | None = None, limit: int = 50, offset: int = 0):
        campus_link = select(RecruitmentDriveOpportunity.opportunity_id).join(RecruitmentDrive, RecruitmentDrive.id == RecruitmentDriveOpportunity.drive_id).where(RecruitmentDriveOpportunity.opportunity_id == InternshipOpportunity.id, RecruitmentDrive.status.in_({"PUBLISHED", "ACTIVE"})).exists()
        stmt = select(InternshipOpportunity, InternshipProvider).join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id).where(~campus_link, InternshipOpportunity.is_active.is_(True)).order_by(InternshipOpportunity.application_deadline.asc(), InternshipOpportunity.created_at.desc()).limit(limit).offset(offset)
        if query: stmt = stmt.where(InternshipOpportunity.title.ilike(f"%{query.strip()}%"))
        if location: stmt = stmt.where(InternshipOpportunity.location.ilike(f"%{location.strip()}%"))
        return list((await self.session.execute(stmt)).all())
    async def get_opportunity_with_provider(self, opportunity_id: str):
        return (await self.session.execute(select(InternshipOpportunity, InternshipProvider).join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id).where(InternshipOpportunity.id == opportunity_id))).first()
    async def list_applications_for_student(self, student_id: str):
        stmt = select(InternshipApplication, InternshipOpportunity, InternshipProvider).join(InternshipOpportunity, InternshipOpportunity.id == InternshipApplication.opportunity_id).join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id).where(InternshipApplication.student_id == student_id).order_by(InternshipApplication.applied_at.desc())
        return list((await self.session.execute(stmt)).all())
    async def transition_application(self, application_id: str, expected_status: str, new_status: str) -> bool:
        result = await self.session.execute(update(InternshipApplication).where(InternshipApplication.id == application_id, InternshipApplication.status == expected_status).values(status=new_status))
        return bool(result.rowcount)
    async def get_faculty(self, faculty_id: str) -> FacultyProfile | None: return await self.session.get(FacultyProfile, faculty_id)
    async def get_placement_for_application(self, application_id: str):
        return await self.session.scalar(select(InternshipPlacement).where(InternshipPlacement.application_id == application_id))
