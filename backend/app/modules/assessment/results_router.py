from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import CurrentAccount, DbSession
from app.modules.assessment.results_schemas import GradingPolicyCreate, ResultPrepare
from app.modules.assessment.results_service import OfficialResultService, OfficialResultError

router = APIRouter(tags=["official academic results"])


async def _call(operation, db):
    try:
        return await operation
    except OfficialResultError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Result operation conflicts with an existing official record") from None


def _policy(item):
    return {"id": item.id, "institution_id": item.institution_id, "version_number": item.version_number,
        "status": item.status, "policy_json": item.policy_json, "created_by_account_id": item.created_by_account_id,
        "approved_by_account_id": item.approved_by_account_id, "approved_at": item.approved_at}


def _result(item):
    return {"id": item.id, "report_submission_id": item.report_submission_id, "report_version_id": item.report_version_id,
        "placement_id": item.placement_id, "student_profile_id": item.student_profile_id, "institution_id": item.institution_id,
        "academic_year_id": item.academic_year_id, "semester_number": item.semester_number,
        "curriculum_mapping_version_id": item.curriculum_mapping_version_id, "grading_policy_id": item.grading_policy_id,
        "status": item.status, "total_score": str(item.total_score), "final_grade": item.final_grade,
        "created_by_account_id": item.created_by_account_id, "approved_by_account_id": item.approved_by_account_id,
        "approved_at": item.approved_at, "published_by_account_id": item.published_by_account_id, "published_at": item.published_at}


@router.post("/grading-policies", status_code=201)
async def create_policy(payload: GradingPolicyCreate, account: CurrentAccount, db: DbSession):
    config = {"aggregation_method": "WEIGHTED_MEAN", "rounding_places": payload.rounding_places,
        "minimum_evaluators": payload.minimum_evaluators, "require_curriculum_review": payload.require_curriculum_review,
        "require_griffin": payload.require_griffin, "grade_bands": [band.model_dump(mode="json") for band in payload.grade_bands]}
    item = await _call(OfficialResultService(db).create_policy(payload.institution_id, account.id, config), db)
    return _policy(item)


@router.post("/grading-policies/{policy_id}/approve")
async def approve_policy(policy_id: str, account: CurrentAccount, db: DbSession):
    return _policy(await _call(OfficialResultService(db).approve_policy(policy_id, account.id), db))


@router.post("/reports/{submission_id}/official-result/preview")
async def preview_result(submission_id: str, payload: ResultPrepare, account: CurrentAccount, db: DbSession):
    return await _call(OfficialResultService(db).preview(submission_id, payload.grading_policy_id, account.id), db)


@router.post("/reports/{submission_id}/official-result/prepare", status_code=201)
async def prepare_result(submission_id: str, payload: ResultPrepare, account: CurrentAccount, db: DbSession):
    item = await _call(OfficialResultService(db).prepare(submission_id, payload.grading_policy_id, account.id), db)
    return _result(item)


@router.post("/official-results/{result_id}/approve")
async def approve_result(result_id: str, account: CurrentAccount, db: DbSession):
    return _result(await _call(OfficialResultService(db).approve(result_id, account.id), db))


@router.post("/official-results/{result_id}/publish")
async def publish_result(result_id: str, account: CurrentAccount, db: DbSession):
    return _result(await _call(OfficialResultService(db).publish(result_id, account.id), db))


@router.get("/academic-results/me")
async def list_my_academic_results(account: CurrentAccount, db: DbSession):
    items = await _call(OfficialResultService(db).list_mine(account.id), db)
    return {"items": [_result(item) for item in items]}
