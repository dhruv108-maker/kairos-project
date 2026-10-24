from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account
from app.models.employers import RecruitmentInterview, RecruitmentOffer
from app.models.internship import InternshipApplication, RecruitmentStageEvent
from app.modules.audit.service import AuditService
from app.modules.employers.service import EmployerError, EmployerService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise EmployerError(422, "Datetime must include a timezone offset")
    return value.astimezone(UTC).replace(tzinfo=None)


class RecruitmentWorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.employers = EmployerService(db)

    async def _application(self, organization_id: str, actor_id: str, application_id: str, write: bool = False):
        return await self.employers._application_in_org(organization_id, actor_id, application_id, write=write)

    async def schedule_interview(self, organization_id: str, actor_id: str, application_id: str, data: dict) -> RecruitmentInterview:
        application, opportunity = await self._application(organization_id, actor_id, application_id, write=True)
        if application.recruitment_stage not in {"SHORTLISTED", "INTERVIEW"}:
            raise EmployerError(409, "Interviews can only be scheduled for shortlisted or interview-stage applicants")
        scheduled_at = _utc_naive(data["scheduled_at"])
        if scheduled_at <= _now():
            raise EmployerError(422, "Interview must be scheduled in the future")
        interview_type = data.get("interview_type", "VIDEO").upper()
        meeting_url = str(data["meeting_url"]) if data.get("meeting_url") else None
        item = RecruitmentInterview(
            id=str(uuid4()), application_id=application.id, scheduled_by_account_id=actor_id,
            scheduled_at=scheduled_at, duration_minutes=data.get("duration_minutes", 30),
            interview_type=interview_type, meeting_url=meeting_url, location=data.get("location"),
            status="SCHEDULED", interviewer_notes=data.get("interviewer_notes"),
        )
        self.db.add(item)
        AuditService(self.db).record(actor_id, None, "recruitment.interview_scheduled", "recruitment_interview", item.id,
            {"organization_id": organization_id, "application_id": application.id, "opportunity_id": opportunity.id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_interviews(self, organization_id: str, actor_id: str, application_id: str) -> list[RecruitmentInterview]:
        await self._application(organization_id, actor_id, application_id)
        result = await self.db.execute(select(RecruitmentInterview).where(
            RecruitmentInterview.application_id == application_id
        ).order_by(RecruitmentInterview.scheduled_at, RecruitmentInterview.id))
        return list(result.scalars().all())

    async def update_interview_status(self, organization_id: str, actor_id: str, application_id: str, interview_id: str, new_status: str) -> RecruitmentInterview:
        application, _ = await self._application(organization_id, actor_id, application_id, write=True)
        item = await self.db.get(RecruitmentInterview, interview_id)
        if item is None or item.application_id != application.id:
            raise EmployerError(404, "Interview not found for this application")
        new_status = new_status.upper()
        transitions = {"SCHEDULED": {"COMPLETED", "CANCELLED", "NO_SHOW"}}
        if new_status not in transitions.get(item.status, set()):
            raise EmployerError(409, f"Invalid interview status transition: {item.status} -> {new_status}")
        old_status = item.status
        item.status = new_status
        AuditService(self.db).record(actor_id, None, "recruitment.interview_status_changed", "recruitment_interview", item.id,
            {"organization_id": organization_id, "application_id": application.id, "from": old_status, "to": new_status})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def issue_offer(self, organization_id: str, actor_id: str, application_id: str, data: dict) -> RecruitmentOffer:
        application, opportunity = await self._application(organization_id, actor_id, application_id, write=True)
        if application.recruitment_stage not in {"SHORTLISTED", "INTERVIEW"}:
            raise EmployerError(409, "An offer can only be issued to a shortlisted or interview-stage applicant")
        if data.get("expires_at"):
            expires_at = _utc_naive(data["expires_at"])
            if expires_at <= _now():
                raise EmployerError(422, "Offer expiry must be in the future")
        else:
            expires_at = None
        existing = await self.db.scalar(select(RecruitmentOffer).where(
            RecruitmentOffer.application_id == application.id,
            RecruitmentOffer.status.in_({"DRAFT", "ISSUED"}),
        ))
        if existing is not None:
            raise EmployerError(409, "An active offer already exists for this application")
        now = _now()
        item = RecruitmentOffer(
            id=str(uuid4()), application_id=application.id, issued_by_account_id=actor_id,
            status="ISSUED", compensation_amount=data.get("compensation_amount"),
            compensation_currency=data.get("compensation_currency", "INR").upper(),
            compensation_period=data.get("compensation_period", "YEAR").upper(),
            start_date=data.get("start_date"), expires_at=expires_at, terms=data.get("terms"),
            issued_at=now,
        )
        old_stage = application.recruitment_stage or "SUBMITTED"
        application.recruitment_stage = "OFFER"
        application.status = "OFFERED"
        self.db.add(item)
        self.db.add(RecruitmentStageEvent(id=str(uuid4()), application_id=application.id, actor_account_id=actor_id,
            from_stage=old_stage, to_stage="OFFER", note="Offer issued"))
        AuditService(self.db).record(actor_id, None, "recruitment.offer_issued", "recruitment_offer", item.id,
            {"organization_id": organization_id, "application_id": application.id, "opportunity_id": opportunity.id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_offers(self, organization_id: str, actor_id: str, application_id: str) -> list[RecruitmentOffer]:
        await self._application(organization_id, actor_id, application_id)
        result = await self.db.execute(select(RecruitmentOffer).where(
            RecruitmentOffer.application_id == application_id
        ).order_by(RecruitmentOffer.created_at.desc(), RecruitmentOffer.id))
        return list(result.scalars().all())

    async def withdraw_offer(self, organization_id: str, actor_id: str, application_id: str, offer_id: str) -> RecruitmentOffer:
        application, _ = await self._application(organization_id, actor_id, application_id, write=True)
        item = await self.db.get(RecruitmentOffer, offer_id)
        if item is None or item.application_id != application.id:
            raise EmployerError(404, "Offer not found for this application")
        if item.status != "ISSUED":
            raise EmployerError(409, "Only an issued offer can be withdrawn")
        item.status = "WITHDRAWN"
        item.responded_at = _now()
        AuditService(self.db).record(actor_id, None, "recruitment.offer_withdrawn", "recruitment_offer", item.id,
            {"organization_id": organization_id, "application_id": application.id})
        await self.db.commit()
        await self.db.refresh(item)
        return item
