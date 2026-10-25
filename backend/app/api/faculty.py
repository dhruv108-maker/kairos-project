from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.auth import _account_public
from app.api.dependencies import CurrentAccount, DbSession, require_role
from app.api.schemas import FacultyProfileResponse, ProfileUpdate
from app.models.academic import FacultyProfile
from app.models.internship import InternshipPlacement

router = APIRouter(prefix="/faculty", tags=["faculty"])


@router.get("/me", response_model=FacultyProfileResponse)
async def get_my_faculty_profile(
    account: CurrentAccount, db: DbSession
) -> FacultyProfileResponse:
    await require_role(db, account, "FACULTY")
    profile = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    return FacultyProfileResponse(
        account=await _account_public(db, account),
        faculty={
            "id": profile.id,
            "employee_code": profile.employee_code,
            "department_id": profile.department_id,
            "designation": profile.designation,
            "employment_status": "pending_approval" if not account.is_active else "active",
        },
    )


@router.patch("/me", response_model=FacultyProfileResponse)
async def update_my_faculty_profile(
    payload: ProfileUpdate, account: CurrentAccount, db: DbSession
) -> FacultyProfileResponse:
    await require_role(db, account, "FACULTY")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="No profile fields supplied")
    for key, value in changes.items():
        setattr(account, key, value)
    await db.commit()
    await db.refresh(account)
    return await get_my_faculty_profile(account, db)


@router.get("/me/affiliations")
async def get_my_faculty_affiliations(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "FACULTY")
    # Keep the current response explicit until the deployed affiliation columns are fully mapped.
    return {
        "items": [{"department_id": (await db.scalar(
            select(FacultyProfile.department_id).where(FacultyProfile.account_id == account.id)
        ))}],
        "schema_supported": True,
        "note": "The primary department is available; additional affiliation history is not included in this response yet.",
    }

from typing import Any
from app.models.evaluation import ReportSubmission
from app.models.internship import InternshipPlacement

@router.get("/me/placements")
async def list_my_internship_placements(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    await require_role(db, account, "FACULTY")
    profile = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    rows = (await db.execute(
        select(InternshipPlacement)
        .where(InternshipPlacement.faculty_supervisor_id == profile.id)
        .order_by(InternshipPlacement.start_date.desc())
    )).scalars().all()
    return {"items": [
        {"id": item.id, "application_id": item.application_id, "student_id": item.student_id,
         "faculty_supervisor_id": item.faculty_supervisor_id, "start_date": item.start_date,
         "end_date": item.end_date, "status": item.status}
        for item in rows
    ]}
