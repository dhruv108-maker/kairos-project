from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import CurrentAccount, DbSession
from app.modules.curriculum.schemas import LearningOutcomeCreate, CurriculumMappingCreate, CurriculumMappingReview
from app.modules.curriculum.service import CurriculumService, CurriculumWorkflowError

router = APIRouter(tags=["curriculum mapping"])


async def _call(operation, db):
    try:
        return await operation
    except CurriculumWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Curriculum mapping conflicts with existing data") from None


def _outcome(item):
    return {"id": item.id, "institution_id": item.institution_id, "programme_id": item.programme_id,
        "code": item.code, "title": item.title, "description": item.description, "is_active": item.is_active,
        "created_by_account_id": item.created_by_account_id, "created_at": item.created_at}


@router.post("/institutions/{institution_id}/curriculum-outcomes", status_code=201)
async def create_outcome(institution_id: str, payload: LearningOutcomeCreate, account: CurrentAccount, db: DbSession):
    item = await _call(CurriculumService(db).create_outcome(institution_id, account.id, payload.programme_id,
        payload.code, payload.title, payload.description), db)
    return _outcome(item)


@router.get("/institutions/{institution_id}/curriculum-outcomes")
async def list_outcomes(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(CurriculumService(db).list_outcomes(institution_id, account.id), db)
    return {"items": [_outcome(item) for item in items]}


@router.post("/reports/{submission_id}/curriculum-mappings", status_code=201)
async def create_mapping(submission_id: str, payload: CurriculumMappingCreate, account: CurrentAccount, db: DbSession):
    return await _call(CurriculumService(db).create_mapping(submission_id, account.id,
        [item.model_dump() for item in payload.items]), db)


@router.get("/reports/{submission_id}/curriculum-mappings")
async def get_mapping(submission_id: str, account: CurrentAccount, db: DbSession):
    return await _call(CurriculumService(db).get_mapping(submission_id, account.id), db)


@router.post("/reports/{submission_id}/curriculum-mappings/{mapping_id}/review")
async def review_mapping(submission_id: str, mapping_id: str, payload: CurriculumMappingReview,
                         account: CurrentAccount, db: DbSession):
    return await _call(CurriculumService(db).review_mapping(submission_id, mapping_id, account.id,
        payload.reviewer_notes, [item.model_dump() for item in payload.items]), db)
