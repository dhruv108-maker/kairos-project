from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.evaluations.schemas import EvaluationRequest
from app.modules.evaluations.service import EvaluationService, EvaluationWorkflowError

router = APIRouter(prefix="/evaluations", tags=["evaluations and Griffin integration"])


async def _call(operation, db):
    try:
        return await operation
    except EvaluationWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Evaluation conflicts with an existing job") from None


def _evaluation(item):
    return {"id": item.id, "report_version_id": item.report_version_id,
            "griffin_project_id": item.griffin_project_id, "griffin_report_id": item.griffin_report_id,
            "griffin_job_id": item.griffin_job_id, "current_status": item.current_status,
            "created_at": item.created_at, "updated_at": item.updated_at}


def _attempt(item):
    return {"id": item.id, "griffin_evaluation_id": item.griffin_evaluation_id,
            "attempt_number": item.attempt_number, "execution_status": item.execution_status,
            "error_message": item.error_message, "started_at": item.started_at,
            "completed_at": item.completed_at}


@router.post("/report-versions/{version_id}", status_code=202)
async def request_evaluation(version_id: str, payload: EvaluationRequest, account: CurrentAccount, db: DbSession):
    item = await _call(EvaluationService(db).request_evaluation(
        version_id, account.id, payload.griffin_project_id, payload.griffin_report_id
    ), db)
    return _evaluation(item)


@router.get("/{evaluation_id}")
async def get_evaluation(evaluation_id: str, account: CurrentAccount, db: DbSession):
    item = await _call(EvaluationService(db).get_for_faculty(evaluation_id, account.id), db)
    return _evaluation(item)


@router.get("/{evaluation_id}/attempts")
async def list_evaluation_attempts(evaluation_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(EvaluationService(db).attempts_for_faculty(evaluation_id, account.id), db)
    return {"items": [_attempt(item) for item in items]}
