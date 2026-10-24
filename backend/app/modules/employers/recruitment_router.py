from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.employers.schemas import InterviewCreate, InterviewStatusUpdate, OfferCreate
from app.modules.employers.service import EmployerError
from app.modules.employers.recruitment_service import RecruitmentWorkflowService

router = APIRouter(tags=["recruitment-workflow"])


def _error(exc: EmployerError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _interview(item) -> dict:
    return {
        "id": item.id, "application_id": item.application_id,
        "scheduled_by_account_id": item.scheduled_by_account_id,
        "scheduled_at": item.scheduled_at, "duration_minutes": item.duration_minutes,
        "interview_type": item.interview_type, "meeting_url": item.meeting_url,
        "location": item.location, "status": item.status,
        "interviewer_notes": item.interviewer_notes,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }


def _offer(item) -> dict:
    return {
        "id": item.id, "application_id": item.application_id,
        "issued_by_account_id": item.issued_by_account_id, "status": item.status,
        "compensation_amount": item.compensation_amount,
        "compensation_currency": item.compensation_currency,
        "compensation_period": item.compensation_period, "start_date": item.start_date,
        "expires_at": item.expires_at, "terms": item.terms,
        "issued_at": item.issued_at, "responded_at": item.responded_at,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }


@router.post("/employers/organizations/{organization_id}/applications/{application_id}/interviews", status_code=status.HTTP_201_CREATED)
async def schedule_interview(organization_id: str, application_id: str, payload: InterviewCreate, account: CurrentAccount, db: DbSession):
    try:
        item = await RecruitmentWorkflowService(db).schedule_interview(
            organization_id, account.id, application_id, payload.model_dump()
        )
        return _interview(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/applications/{application_id}/interviews")
async def list_interviews(organization_id: str, application_id: str, account: CurrentAccount, db: DbSession):
    try:
        items = await RecruitmentWorkflowService(db).list_interviews(organization_id, account.id, application_id)
        return {"items": [_interview(item) for item in items]}
    except EmployerError as exc:
        raise _error(exc) from None


@router.patch("/employers/organizations/{organization_id}/applications/{application_id}/interviews/{interview_id}/status")
async def update_interview_status(organization_id: str, application_id: str, interview_id: str, payload: InterviewStatusUpdate, account: CurrentAccount, db: DbSession):
    try:
        item = await RecruitmentWorkflowService(db).update_interview_status(
            organization_id, account.id, application_id, interview_id, payload.status
        )
        return _interview(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/applications/{application_id}/offers", status_code=status.HTTP_201_CREATED)
async def issue_offer(organization_id: str, application_id: str, payload: OfferCreate, account: CurrentAccount, db: DbSession):
    try:
        item = await RecruitmentWorkflowService(db).issue_offer(
            organization_id, account.id, application_id, payload.model_dump()
        )
        return _offer(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/applications/{application_id}/offers")
async def list_offers(organization_id: str, application_id: str, account: CurrentAccount, db: DbSession):
    try:
        items = await RecruitmentWorkflowService(db).list_offers(organization_id, account.id, application_id)
        return {"items": [_offer(item) for item in items]}
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/applications/{application_id}/offers/{offer_id}/withdraw")
async def withdraw_offer(organization_id: str, application_id: str, offer_id: str, account: CurrentAccount, db: DbSession):
    try:
        item = await RecruitmentWorkflowService(db).withdraw_offer(
            organization_id, account.id, application_id, offer_id
        )
        return _offer(item)
    except EmployerError as exc:
        raise _error(exc) from None
