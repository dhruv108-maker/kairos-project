"""Policy-driven post-internship assessment endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.post_internship.schemas import (
    AssessmentAssignmentCreate, CurriculumMappingBatch, CurriculumOutcomeCreate,
    PolicyCreate, ScoresUpdate,
)
from app.modules.post_internship.service import PostInternshipError, PostInternshipService

router = APIRouter(prefix="/internship-assessments", tags=["post-internship assessment"])


async def _call(operation, db):
    try:
        return await operation
    except PostInternshipError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Assessment operation conflicts with existing records") from None


def _policy(item):
    return {
        "id": item.id, "institution_id": item.institution_id, "programme_id": item.programme_id,
        "version": item.version, "name": item.name, "criteria": item.criteria_json,
        "component_weights": item.component_weights_json, "griffin_score_max": float(item.griffin_score_max),
        "curriculum_status_scores": item.curriculum_status_scores_json, "grade_bands": item.grade_bands_json,
        "passing_score": float(item.passing_score), "final_approver_role": item.final_approver_role,
        "required_evaluator_count": item.required_evaluator_count,
        "show_curriculum_mapping_to_evaluator": item.show_curriculum_mapping_to_evaluator,
        "is_active": item.is_active, "created_at": item.created_at,
    }


def _outcome(item):
    return {
        "id": item.id, "institution_id": item.institution_id, "programme_id": item.programme_id,
        "semester": item.semester, "outcome_code": item.outcome_code, "title": item.title,
        "expected_competency": item.expected_competency, "source_reference": item.source_reference,
        "is_active": item.is_active,
    }


def _assignment(item):
    return {
        "id": item.id, "packet_code": item.packet_code, "report_version_id": item.report_version_id,
        "status": item.status, "assigned_at": item.assigned_at, "submitted_at": item.submitted_at,
        "total_score": float(item.total_score) if item.total_score is not None else None,
    }


def _result(item):
    return {
        "id": item.id, "report_submission_id": item.report_submission_id,
        "report_version_id": item.report_version_id, "semester": item.academic_semester,
        "academic_year_id": item.academic_year_id, "revision_number": item.revision_number,
        "component_breakdown": item.component_breakdown_json, "total_score": float(item.total_score),
        "grade": item.grade, "status": item.status, "finalized_at": item.finalized_at,
        "published_at": item.published_at,
    }


@router.post("/policies", status_code=201)
async def create_policy(payload: PolicyCreate, account: CurrentAccount, db: DbSession):
    item = await _call(PostInternshipService(db).create_policy(account.id, payload.model_dump()), db)
    return _policy(item)


@router.get("/policies")
async def list_policies(institution_id: str, programme_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(PostInternshipService(db).list_policies(institution_id, programme_id, account.id), db)
    return {"items": [_policy(item) for item in items]}


@router.post("/curriculum-outcomes", status_code=201)
async def create_curriculum_outcome(payload: CurriculumOutcomeCreate, account: CurrentAccount, db: DbSession):
    item = await _call(PostInternshipService(db).create_outcome(account.id, payload.model_dump()), db)
    return _outcome(item)


@router.get("/submissions/{submission_id}/mappings")
async def list_curriculum_mappings(submission_id: str, account: CurrentAccount, db: DbSession):
    return await _call(PostInternshipService(db).list_mappings(submission_id, account.id), db)


@router.put("/submissions/{submission_id}/mappings")
async def save_curriculum_mappings(
    submission_id: str, payload: CurriculumMappingBatch, account: CurrentAccount, db: DbSession
):
    return await _call(
        PostInternshipService(db).save_mappings(
            submission_id, account.id, [item.model_dump() for item in payload.items]
        ), db,
    )


@router.get("/submissions/{submission_id}/assignment-options")
async def get_assessment_assignment_options(submission_id: str, account: CurrentAccount, db: DbSession):
    return await _call(PostInternshipService(db).assignment_options(submission_id, account.id), db)


@router.post("/assignments", status_code=201)
async def assign_blind_assessment(
    payload: AssessmentAssignmentCreate, account: CurrentAccount, db: DbSession
):
    item = await _call(PostInternshipService(db).assign_assessment(account.id, payload.model_dump()), db)
    return _assignment(item)


@router.get("/assignments/me")
async def list_my_blind_assessments(account: CurrentAccount, db: DbSession):
    items = await _call(PostInternshipService(db).list_assessments_for_faculty(account.id), db)
    return {"items": [_assignment(item) for item in items]}


@router.get("/assignments/{assignment_id}")
async def get_blind_assessment_packet(assignment_id: str, account: CurrentAccount, db: DbSession):
    return await _call(PostInternshipService(db).assessment_packet(assignment_id, account.id), db)


@router.put("/assignments/{assignment_id}/scores")
async def save_blind_assessment_draft(
    assignment_id: str, payload: ScoresUpdate, account: CurrentAccount, db: DbSession
):
    item = await _call(PostInternshipService(db).save_scores(
        assignment_id, account.id, payload.model_dump(), submit=False
    ), db)
    return _assignment(item)


@router.post("/assignments/{assignment_id}/submit")
async def submit_blind_assessment(
    assignment_id: str, payload: ScoresUpdate, account: CurrentAccount, db: DbSession
):
    item = await _call(PostInternshipService(db).save_scores(
        assignment_id, account.id, payload.model_dump(), submit=True
    ), db)
    return _assignment(item)


@router.get("/assignments/{assignment_id}/files/{kind}")
async def download_blind_assessment_file(
    assignment_id: str, kind: str, account: CurrentAccount, db: DbSession
):
    item, path, safe_filename = await _call(
        PostInternshipService(db).assessment_file(assignment_id, account.id, kind), db
    )
    # Content type is safe to expose; the original filename and storage metadata are not.
    return FileResponse(
        path=path, filename=safe_filename, media_type=item.mime_type, content_disposition_type="attachment",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/submissions/{submission_id}/result-preview")
async def get_result_preview(submission_id: str, account: CurrentAccount, db: DbSession):
    return await _call(PostInternshipService(db).result_preview(submission_id, account.id), db)


@router.post("/submissions/{submission_id}/finalize")
async def finalize_internship_result(submission_id: str, account: CurrentAccount, db: DbSession):
    item = await _call(PostInternshipService(db).finalize_result(submission_id, account.id), db)
    return _result(item)


@router.post("/results/{result_id}/publish")
async def publish_internship_result(result_id: str, account: CurrentAccount, db: DbSession):
    item = await _call(PostInternshipService(db).publish_result(result_id, account.id), db)
    return _result(item)


@router.get("/results/me")
async def get_my_published_results(account: CurrentAccount, db: DbSession):
    items = await _call(PostInternshipService(db).student_results(account.id), db)
    return {"items": items}


@router.get("/supervised-submissions")
async def list_supervised_submissions(account: CurrentAccount, db: DbSession):
    items = await _call(PostInternshipService(db).supervised_submissions(account.id), db)
    return {"items": items}


@router.get("/supervised-students")
async def list_authorized_supervised_students(account: CurrentAccount, db: DbSession):
    items = await _call(PostInternshipService(db).supervised_students(account.id), db)
    return {"items": items}


@router.get("/results/students/{student_profile_id}")
async def get_authorized_student_results(
    student_profile_id: int, account: CurrentAccount, db: DbSession
):
    items = await _call(PostInternshipService(db).faculty_student_results(student_profile_id, account.id), db)
    return {"items": items}


@router.get("/submissions/{submission_id}/progress")
async def get_assessment_progress(submission_id: str, account: CurrentAccount, db: DbSession):
    return await _call(PostInternshipService(db).student_progress(submission_id, account.id), db)
