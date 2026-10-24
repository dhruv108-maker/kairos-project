from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select

from app.api.dependencies import CurrentAccount, DbSession
from app.models.academic import StudentProfile
from app.models.employers import RecruitmentOffer
from app.models.internship import InternshipApplication, RecruitmentStageEvent
from app.modules.audit.service import AuditService

router = APIRouter(tags=["student-recruitment"])


class OfferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    response: str

    @field_validator("response")
    @classmethod
    def valid_response(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"ACCEPTED", "DECLINED"}:
            raise ValueError("response must be ACCEPTED or DECLINED")
        return value


@router.post("/students/applications/{application_id}/offers/{offer_id}/respond")
async def respond_to_offer(application_id: str, offer_id: str, payload: OfferResponse, account: CurrentAccount, db: DbSession):
    student = await db.scalar(select(StudentProfile).where(StudentProfile.account_id == account.id))
    if student is None:
        raise HTTPException(status_code=403, detail="A student profile is required")
    application = await db.get(InternshipApplication, application_id)
    if application is None or application.student_id != student.id:
        raise HTTPException(status_code=404, detail="Application not found")
    offer = await db.get(RecruitmentOffer, offer_id)
    if offer is None or offer.application_id != application.id:
        raise HTTPException(status_code=404, detail="Offer not found for this application")
    if offer.status != "ISSUED":
        raise HTTPException(status_code=409, detail="Only an issued offer can be accepted or declined")
    now = datetime.now(UTC).replace(tzinfo=None)
    if offer.expires_at is not None and offer.expires_at <= now:
        offer.status = "EXPIRED"
        offer.responded_at = now
        await db.commit()
        raise HTTPException(status_code=409, detail="This offer has expired")
    offer.status = payload.response
    offer.responded_at = now
    if payload.response == "ACCEPTED":
        old_stage = application.recruitment_stage or "OFFER"
        if old_stage == "OFFER":
            application.recruitment_stage = "HIRED"
            application.status = "OFFERED"
            db.add(RecruitmentStageEvent(
                id=str(uuid4()), application_id=application.id, actor_account_id=account.id,
                from_stage="OFFER", to_stage="HIRED", note="Candidate accepted offer",
            ))
    AuditService(db).record(account.id, None, "recruitment.offer_responded", "recruitment_offer", offer.id,
        {"application_id": application.id, "response": payload.response})
    await db.commit()
    await db.refresh(offer)
    return {
        "offer_id": offer.id, "status": offer.status, "responded_at": offer.responded_at,
        "application_stage": application.recruitment_stage,
    }
