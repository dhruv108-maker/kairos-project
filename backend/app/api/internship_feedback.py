"""Authorized weekly internship feedback and daily-log review endpoints."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import CurrentAccount, DbSession, account_roles

router = APIRouter(prefix="/internship-feedback", tags=["internship-feedback"])
ReviewerType = Literal["student_self", "faculty_mentor", "industry_mentor"]

class WeeklyFeedbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overall_rating: Decimal | None = Field(None, ge=0, le=5, max_digits=4, decimal_places=2)
    attendance_rating: int | None = Field(None, ge=1, le=5)
    technical_rating: int | None = Field(None, ge=1, le=5)
    communication_rating: int | None = Field(None, ge=1, le=5)
    strengths: str | None = Field(None, max_length=10000)
    improvement_areas: str | None = Field(None, max_length=10000)
    feedback_text: str | None = Field(None, max_length=20000)
    @field_validator("strengths", "improvement_areas", "feedback_text")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None: return None
        return value.strip() or None

class DailyLogFeedbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["acknowledged", "revision_required"]
    feedback_text: str = Field(min_length=1, max_length=20000)
    @field_validator("feedback_text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("Feedback text cannot be blank")
        return value

def _account_id(account: object) -> int:
    try: return int(getattr(account, "id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=403, detail="Account is not mapped to the internship identity schema") from None

def _json(row) -> dict:
    result = dict(row._mapping)
    for key, value in tuple(result.items()):
        if isinstance(value, (date, datetime)): result[key] = value.isoformat()
        elif isinstance(value, Decimal): result[key] = float(value)
    return result

async def _reviewer(db: AsyncSession, account_id: int, roles: list[str]) -> tuple[str, int | None]:
    normalized = {role.upper() for role in roles}
    if "STUDENT" in normalized: return "student_self", None
    if "FACULTY" in normalized:
        profile = await db.scalar(text("SELECT id FROM faculty WHERE account_id=:account_id AND employment_status='active' LIMIT 1"), {"account_id": account_id})
        if profile is None: raise HTTPException(403, "No active faculty profile is linked to this account")
        return "faculty_mentor", int(profile)
    profile = await db.scalar(text("SELECT id FROM industry_mentors WHERE account_id=:account_id AND status='active' LIMIT 1"), {"account_id": account_id})
    if profile is None: raise HTTPException(403, "No active industry mentor profile is linked to this account")
    return "industry_mentor", int(profile)

async def _participation(db: AsyncSession, participation_id: int):
    return (await db.execute(text("""
        SELECT p.id, p.student_id, p.title, p.provider_id, p.starts_on, p.ends_on, p.status,
               s.account_id AS student_account_id, COALESCE(ip.company_name, '') AS company_name
        FROM internship_participations p JOIN students s ON s.id=p.student_id
        LEFT JOIN internship_providers ip ON ip.id=p.provider_id WHERE p.id=:id
    """), {"id": participation_id})).first()

async def _authorize(db: AsyncSession, account_id: int, kind: str, profile_id: int | None, participation_id: int, week_start: date):
    p = await _participation(db, participation_id)
    if p is None: raise HTTPException(404, "Internship participation not found")
    if week_start.weekday() != 0: raise HTTPException(422, "week_start must be a Monday")
    week_end = week_start + timedelta(days=6)
    if (p.ends_on is not None and week_start > p.ends_on) or week_end < p.starts_on:
        raise HTTPException(422, "Selected feedback week is outside the internship date range")
    if kind == "student_self":
        allowed = int(p.student_account_id) == account_id
    elif kind == "faculty_mentor":
        allowed = bool(await db.scalar(text("""
            SELECT 1 FROM faculty_mentorships fm JOIN faculty f ON f.id=fm.faculty_id
            WHERE f.account_id=:account_id AND fm.student_id=:student_id AND fm.status='active'
              AND fm.starts_on<=:week_end AND (fm.ends_on IS NULL OR fm.ends_on>=:week_start) LIMIT 1
        """), {"account_id": account_id, "student_id": p.student_id, "week_start": week_start, "week_end": week_end}))
        if not allowed:
            allowed = bool(await db.scalar(text("""
                SELECT 1 FROM internship_placements pl JOIN faculty f ON f.id=pl.faculty_supervisor_id
                WHERE pl.student_id=:student_id AND f.account_id=:account_id
                  AND pl.start_date<=:week_end AND pl.end_date>=:week_start LIMIT 1
            """), {"account_id": account_id, "student_id": p.student_id, "week_start": week_start, "week_end": week_end}))
    else:
        allowed = bool(await db.scalar(text("""
            SELECT 1 FROM industry_mentor_assignments a
            WHERE a.participation_id=:participation_id AND a.industry_mentor_id=:mentor_id
              AND a.status='active' AND a.starts_on<=:week_end
              AND (a.ends_on IS NULL OR a.ends_on>=:week_start) LIMIT 1
        """), {"participation_id": participation_id, "mentor_id": profile_id, "week_start": week_start, "week_end": week_end}))
    if not allowed: raise HTTPException(404, "Internship participation not found")
    return p

async def _feedback_rows(db: AsyncSession, participation_id: int, week_start: date | None):
    sql = """SELECT id, participation_id, week_start, reviewer_type, reviewer_account_id, industry_mentor_id,
      overall_rating, strengths, improvement_areas, attendance_rating, technical_rating, communication_rating,
      feedback_text, status, submitted_at, created_at, updated_at
      FROM internship_weekly_feedback WHERE participation_id=:id"""
    params = {"id": participation_id}
    if week_start is not None:
        sql += " AND week_start=:week_start"
        params["week_start"] = week_start
    sql += " ORDER BY week_start DESC, reviewer_type"
    return [_json(row) for row in (await db.execute(text(sql), params)).all()]

@router.get("/participations")
async def list_feedback_participations(account: CurrentAccount, db: DbSession) -> dict:
    account_id = _account_id(account)
    kind, profile_id = await _reviewer(db, account_id, await account_roles(db, str(account.id)))
    if kind == "student_self":
        sql = """SELECT p.id,p.student_id,p.title,p.starts_on,p.ends_on,p.status,COALESCE(ip.company_name,'') company_name
          FROM internship_participations p JOIN students s ON s.id=p.student_id
          LEFT JOIN internship_providers ip ON ip.id=p.provider_id WHERE s.account_id=:account_id ORDER BY p.starts_on DESC"""
        params = {"account_id": account_id}
    elif kind == "faculty_mentor":
        sql = """SELECT DISTINCT p.id,p.student_id,p.title,p.starts_on,p.ends_on,p.status,COALESCE(ip.company_name,'') company_name
          FROM internship_participations p JOIN faculty_mentorships fm ON fm.student_id=p.student_id
          JOIN faculty f ON f.id=fm.faculty_id LEFT JOIN internship_providers ip ON ip.id=p.provider_id
          WHERE f.account_id=:account_id AND fm.status='active' ORDER BY p.starts_on DESC"""
        params = {"account_id": account_id}
    else:
        sql = """SELECT DISTINCT p.id,p.student_id,p.title,p.starts_on,p.ends_on,p.status,COALESCE(ip.company_name,'') company_name
          FROM internship_participations p JOIN industry_mentor_assignments a ON a.participation_id=p.id
          LEFT JOIN internship_providers ip ON ip.id=p.provider_id
          WHERE a.industry_mentor_id=:mentor_id AND a.status='active' ORDER BY p.starts_on DESC"""
        params = {"mentor_id": profile_id}
    rows = (await db.execute(text(sql), params)).all()
    return {"items": [_json(row) for row in rows], "reviewer_type": kind}

@router.get("/participations/{participation_id}")
async def get_weekly_feedback(participation_id: int, account: CurrentAccount, db: DbSession, week_start: date | None = Query(None)) -> dict:
    account_id = _account_id(account)
    kind, profile_id = await _reviewer(db, account_id, await account_roles(db, str(account.id)))
    p = await _participation(db, participation_id)
    if p is None: raise HTTPException(404, "Internship participation not found")
    anchor = week_start or (p.starts_on - timedelta(days=p.starts_on.weekday()))
    await _authorize(db, account_id, kind, profile_id, participation_id, anchor)
    return {"participation": _json(p), "reviewer_type": kind, "items": await _feedback_rows(db, participation_id, week_start)}

@router.put("/participations/{participation_id}/weeks/{week_start}")
async def save_weekly_feedback(participation_id: int, week_start: date, payload: WeeklyFeedbackInput, account: CurrentAccount, db: DbSession) -> dict:
    account_id = _account_id(account)
    kind, profile_id = await _reviewer(db, account_id, await account_roles(db, str(account.id)))
    p = await _authorize(db, account_id, kind, profile_id, participation_id, week_start)
    if p.status not in {"active", "completed"}: raise HTTPException(409, "Feedback is available only for active or completed internships")
    params = {"participation_id": participation_id, "week_start": week_start, "reviewer_type": kind,
              "account_id": account_id, "mentor_id": profile_id if kind == "industry_mentor" else None}
    existing = (await db.execute(text("""
      SELECT id,status FROM internship_weekly_feedback WHERE participation_id=:participation_id AND week_start=:week_start
      AND reviewer_type=:reviewer_type AND reviewer_account_id=:account_id
      AND ((industry_mentor_id IS NULL AND :mentor_id IS NULL) OR industry_mentor_id=:mentor_id) LIMIT 1 FOR UPDATE
    """), params)).first()
    if existing and existing.status in {"submitted", "locked"}: raise HTTPException(409, "Submitted or locked feedback cannot be edited")
    try:
        if existing:
            await db.execute(text("""UPDATE internship_weekly_feedback SET overall_rating=:overall_rating,strengths=:strengths,
              improvement_areas=:improvement_areas,attendance_rating=:attendance_rating,technical_rating=:technical_rating,
              communication_rating=:communication_rating,feedback_text=:feedback_text,status='draft',updated_at=CURRENT_TIMESTAMP
              WHERE id=:id"""), {**payload.model_dump(), "id": existing.id})
            record_id = int(existing.id)
        else:
            result = await db.execute(text("""INSERT INTO internship_weekly_feedback
              (participation_id,week_start,reviewer_type,reviewer_account_id,industry_mentor_id,overall_rating,strengths,
               improvement_areas,attendance_rating,technical_rating,communication_rating,feedback_text,status)
              VALUES (:participation_id,:week_start,:reviewer_type,:account_id,:mentor_id,:overall_rating,:strengths,
               :improvement_areas,:attendance_rating,:technical_rating,:communication_rating,:feedback_text,'draft')""",
              {**params, **payload.model_dump()}))
            record_id = int(result.lastrowid)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Feedback changed concurrently; refresh and retry") from None
    row = (await db.execute(text("SELECT * FROM internship_weekly_feedback WHERE id=:id"), {"id": record_id})).first()
    return _json(row)

@router.post("/participations/{participation_id}/weeks/{week_start}/submit")
async def submit_weekly_feedback(participation_id: int, week_start: date, account: CurrentAccount, db: DbSession) -> dict:
    account_id = _account_id(account)
    kind, profile_id = await _reviewer(db, account_id, await account_roles(db, str(account.id)))
    await _authorize(db, account_id, kind, profile_id, participation_id, week_start)
    mentor_id = profile_id if kind == "industry_mentor" else None
    row = (await db.execute(text("""SELECT id,status FROM internship_weekly_feedback
      WHERE participation_id=:participation_id AND week_start=:week_start AND reviewer_type=:reviewer_type
      AND reviewer_account_id=:account_id AND ((industry_mentor_id IS NULL AND :mentor_id IS NULL) OR industry_mentor_id=:mentor_id)
      LIMIT 1 FOR UPDATE"""), {"participation_id": participation_id, "week_start": week_start, "reviewer_type": kind,
      "account_id": account_id, "mentor_id": mentor_id})).first()
    if row is None: raise HTTPException(404, "Save a draft before submitting feedback")
    if row.status not in {"draft", "returned"}: raise HTTPException(409, "Only draft or returned feedback can be submitted")
    await db.execute(text("UPDATE internship_weekly_feedback SET status='submitted',submitted_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=:id"), {"id": row.id})
    await db.commit()
    saved = (await db.execute(text("SELECT * FROM internship_weekly_feedback WHERE id=:id"), {"id": row.id})).first()
    return _json(saved)

@router.post("/daily-logs/{daily_log_id}/feedback")
async def review_daily_log(daily_log_id: int, payload: DailyLogFeedbackInput, account: CurrentAccount, db: DbSession) -> dict:
    account_id = _account_id(account)
    kind, profile_id = await _reviewer(db, account_id, await account_roles(db, str(account.id)))
    if kind == "student_self": raise HTTPException(403, "Students cannot review daily logs")
    log = (await db.execute(text("""SELECT id,participation_id,log_date,status FROM internship_daily_logs WHERE id=:id"""), {"id": daily_log_id})).first()
    if log is None: raise HTTPException(404, "Daily log not found")
    if log.status != "submitted": raise HTTPException(409, "Only submitted daily logs can be reviewed")
    await _authorize(db, account_id, kind, profile_id, int(log.participation_id), log.log_date - timedelta(days=log.log_date.weekday()))
    faculty_id = profile_id if kind == "faculty_mentor" else None
    mentor_id = profile_id if kind == "industry_mentor" else None
    try:
        result = await db.execute(text("""INSERT INTO internship_work_feedback
          (daily_log_id,reviewer_type,reviewer_account_id,faculty_id,industry_mentor_id,decision,feedback_text)
          VALUES (:daily_log_id,:reviewer_type,:account_id,:faculty_id,:mentor_id,:decision,:feedback_text)"""),
          {"daily_log_id": daily_log_id, "reviewer_type": kind, "account_id": account_id, "faculty_id": faculty_id,
           "mentor_id": mentor_id, "decision": payload.decision, "feedback_text": payload.feedback_text})
        if kind == "faculty_mentor":
            await db.execute(text("""UPDATE internship_daily_logs SET faculty_review_status=:decision,faculty_feedback=:feedback,
              faculty_reviewed_by_faculty_id=:profile_id,faculty_reviewed_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=:id"""),
              {"decision": payload.decision, "feedback": payload.feedback_text, "profile_id": profile_id, "id": daily_log_id})
        else:
            await db.execute(text("""UPDATE internship_daily_logs SET industry_review_status=:decision,industry_feedback=:feedback,
              industry_reviewed_by_mentor_id=:profile_id,industry_reviewed_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=:id"""),
              {"decision": payload.decision, "feedback": payload.feedback_text, "profile_id": profile_id, "id": daily_log_id})
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Daily-log review could not be saved; refresh and retry") from None
    return {"id": int(result.lastrowid), "daily_log_id": daily_log_id, "reviewer_type": kind,
            "decision": payload.decision, "feedback_text": payload.feedback_text}
