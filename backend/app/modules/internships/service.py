"""Internship use cases, state-machine validation, and transaction boundaries."""
from datetime import date
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.internship import InternshipApplication, InternshipOpportunity, InternshipPlacement, InternshipProvider
from app.modules.internships.exceptions import DuplicateApplicationError, InternshipConflictError, InternshipNotFoundError, InternshipValidationError, InvalidInternshipStateTransitionError, ProviderNotFoundError
from app.modules.internships.repository import InternshipRepository

# Values are constrained by the supplied MySQL DDL. Add ACCEPTED only with a DDL migration.
APPLICATION_TRANSITIONS = {
    "APPLIED": frozenset({"SHORTLISTED", "REJECTED", "WITHDRAWN"}),
    "SHORTLISTED": frozenset({"OFFERED", "REJECTED", "WITHDRAWN"}),
    "OFFERED": frozenset({"REJECTED"}), "REJECTED": frozenset(), "WITHDRAWN": frozenset(),
}

class InternshipService:
    def __init__(self, session: AsyncSession, repository: InternshipRepository | None = None) -> None:
        self.session, self.repository = session, repository or InternshipRepository(session)

    async def create_provider(self, data: dict) -> InternshipProvider:
        provider = InternshipProvider(id=str(uuid4()), **data)
        self.session.add(provider)
        try: await self.session.commit()
        except Exception: await self.session.rollback(); raise
        await self.session.refresh(provider)
        return provider

    async def create_opportunity(self, data: dict) -> tuple[InternshipOpportunity, InternshipProvider]:
        provider = await self.repository.get_provider(data["provider_id"])
        if provider is None: raise ProviderNotFoundError("Unknown provider_id")
        if data["application_deadline"] < date.today(): raise InternshipValidationError("application_deadline cannot be in the past")
        opportunity = InternshipOpportunity(id=str(uuid4()), is_active=True, **data)
        self.session.add(opportunity)
        try: await self.session.commit()
        except Exception: await self.session.rollback(); raise
        await self.session.refresh(opportunity)
        return opportunity, provider

    async def apply(self, account_id: str, opportunity_id: str) -> InternshipApplication:
        student = await self.repository.get_student_by_account(account_id)
        if student is None: raise InternshipNotFoundError("Student profile not found")
        opportunity = await self.repository.get_opportunity(opportunity_id)
        if opportunity is None or not opportunity.is_active: raise InternshipNotFoundError("Internship opportunity not found")
        if opportunity.application_deadline < date.today(): raise InternshipConflictError("The application deadline has passed")
        # Restricted campus opportunities must re-evaluate eligibility from persisted academic relationships.
        from app.modules.employers.campus_recruitment_service import CampusRecruitmentService
        from app.modules.employers.service import EmployerError
        try:
            await CampusRecruitmentService(self.session).apply_guard(account_id, opportunity_id)
        except EmployerError as exc:
            raise InternshipConflictError(exc.message) from None
        if await self.repository.find_application(opportunity_id, student.id): raise DuplicateApplicationError("You have already applied to this opportunity")
        item = InternshipApplication(id=str(uuid4()), opportunity_id=opportunity_id, student_id=student.id, status="APPLIED")
        self.session.add(item)
        try: await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateApplicationError("You have already applied to this opportunity") from None
        await self.session.refresh(item)
        return item

    async def _change_status(self, item: InternshipApplication, new_status: str) -> InternshipApplication:
        if new_status not in APPLICATION_TRANSITIONS.get(item.status, frozenset()):
            raise InvalidInternshipStateTransitionError(f"Invalid application transition: {item.status} -> {new_status}")
        changed = await self.repository.transition_application(item.id, item.status, new_status)
        if not changed:
            await self.session.rollback()
            raise InvalidInternshipStateTransitionError("Application state changed concurrently; reload and retry")
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def transition_application(self, application_id: str, new_status: str) -> InternshipApplication:
        item = await self.repository.get_application(application_id)
        if item is None: raise InternshipNotFoundError("Application not found")
        return await self._change_status(item, new_status)

    async def withdraw(self, account_id: str, application_id: str) -> InternshipApplication:
        student = await self.repository.get_student_by_account(account_id)
        item = await self.repository.get_application(application_id)
        if student is None or item is None or item.student_id != student.id: raise InternshipNotFoundError("Application not found")
        return await self._change_status(item, "WITHDRAWN")

    async def create_placement(self, application_id: str, data: dict) -> InternshipPlacement:
        item = await self.repository.get_application(application_id)
        if item is None: raise InternshipNotFoundError("Application not found")
        if item.status != "OFFERED": raise InvalidInternshipStateTransitionError("Only an OFFERED application can become a placement")
        if data["end_date"] < data["start_date"]: raise InternshipValidationError("end_date must be on or after start_date")
        supervisor_id = data.get("faculty_supervisor_id")
        if supervisor_id and await self.repository.get_faculty(supervisor_id) is None: raise InternshipValidationError("Unknown faculty_supervisor_id")
        if await self.repository.get_placement_for_application(application_id): raise InternshipConflictError("A placement already exists for this application")
        placement = InternshipPlacement(id=str(uuid4()), application_id=item.id, student_id=item.student_id, faculty_supervisor_id=supervisor_id, start_date=data["start_date"], end_date=data["end_date"], status="ONGOING")
        self.session.add(placement)
        try: await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise InternshipConflictError("A placement already exists for this application") from None
        await self.session.refresh(placement)
        return placement
