from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.analytics.service import AnalyticsAccessError, AnalyticsService
from app.modules.institutions.service import InstitutionAccessError

router = APIRouter(tags=["dashboards and analytics"])


@router.get("/students/me/dashboard")
async def student_dashboard(account: CurrentAccount, db: DbSession):
    try:
        return await AnalyticsService(db).student_dashboard(account.id)
    except AnalyticsAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None


@router.get("/faculty/me/dashboard")
async def faculty_dashboard(account: CurrentAccount, db: DbSession):
    try:
        return await AnalyticsService(db).faculty_dashboard(account.id)
    except AnalyticsAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None


@router.get("/institutions/{institution_id}/dashboard")
async def institution_dashboard(institution_id: str, account: CurrentAccount, db: DbSession):
    try:
        return await AnalyticsService(db).institution_dashboard(institution_id, account.id)
    except (AnalyticsAccessError, InstitutionAccessError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=getattr(exc, "message", str(exc))) from None
