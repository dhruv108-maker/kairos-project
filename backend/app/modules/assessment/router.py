from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import CurrentAccount, DbSession
from app.modules.assessment.schemas import RubricCreate, BlindAssignmentCreate, BlindScoreSave
from app.modules.assessment.service import BlindAssessmentService, BlindAssessmentError

router = APIRouter(tags=["blind assessment"])


async def _call(operation, db):
    try:
        return await operation
    except BlindAssessmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Assessment operation conflicts with existing data") from None


def _rubric(item):
    return {"id": item.id, "institution_id": item.institution_id, "name": item.name,
        "version_number": item.version_number, "status": item.status, "created_by_account_id": item.created_by_account_id,
        "approved_by_account_id": item.approved_by_account_id, "approved_at": item.approved_at, "created_at": item.created_at}


@router.post("/assessment-rubrics", status_code=201)
async def create_rubric(payload: RubricCreate, account: CurrentAccount, db: DbSession):
    item = await _call(BlindAssessmentService(db).create_rubric(payload.institution_id, account.id, payload.name,
        [criterion.model_dump() for criterion in payload.criteria]), db)
    return _rubric(item)


@router.post("/assessment-rubrics/{rubric_id}/approve")
async def approve_rubric(rubric_id: str, account: CurrentAccount, db: DbSession):
    return _rubric(await _call(BlindAssessmentService(db).approve_rubric(rubric_id, account.id), db))


@router.post("/blind-assessments/assignments", status_code=201)
async def assign_blind_assessment(payload: BlindAssignmentCreate, account: CurrentAccount, db: DbSession):
    item = await _call(BlindAssessmentService(db).assign(account.id, payload.report_version_id,
        payload.rubric_id, payload.evaluator_account_id), db)
    return {"id": item.id, "report_version_id": item.report_version_id, "rubric_id": item.rubric_id,
        "evaluator_account_id": item.evaluator_account_id, "status": item.status, "created_at": item.created_at}


@router.get("/blind-assessments/me")
async def my_blind_assessments(account: CurrentAccount, db: DbSession):
    return {"items": await _call(BlindAssessmentService(db).list_my_assignments(account.id), db)}


@router.put("/blind-assessments/assignments/{assignment_id}/scores")
async def save_blind_scores(assignment_id: str, payload: BlindScoreSave, account: CurrentAccount, db: DbSession):
    return await _call(BlindAssessmentService(db).save_scores(assignment_id, account.id,
        [score.model_dump() for score in payload.scores], payload.submit), db)
