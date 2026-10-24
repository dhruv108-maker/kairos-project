"""Persistence and business rules for student portfolio records.

HTTP request validation and response serialization stay in the API adapter;
this service owns student-scoped reads, writes, and transaction rollback.
"""
from __future__ import annotations
from typing import Any
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.internship import InternshipApplication, InternshipOpportunity, InternshipPlacement, InternshipProvider
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.academic import Account, StudentProfile
from app.models.portfolio import StudentAcademicRecord, StudentPortfolioEntry, StudentResume
from app.models.storage import StorageFile
from app.modules.academics.service import AcademicService
from app.modules.shared.exceptions import DomainConflictError, ResourceNotFoundError

COLLECTION_KIND = {
    "skills": "skill", "projects": "project", "certifications": "certification",
    "experience": "experience", "research": "research", "awards": "award",
    "achievements": "achievement", "activities": "activity",
}


def _row(row, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    return {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name not in excluded}


class StudentPortfolioService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.academics = AcademicService(session)

    async def _commit(self, conflict_message: str = "Request conflicts with existing data") -> None:
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise DomainConflictError(conflict_message) from None
        except Exception:
            await self.session.rollback()
            raise

    async def student(self, account_id: str) -> StudentProfile:
        profile = await self.academics.student_profile_for_account(account_id)
        if profile is None:
            raise ResourceNotFoundError("Student profile not found")
        return profile

    async def list_entries(self, profile_id: str, kind: str, limit: int, offset: int) -> list[StudentPortfolioEntry]:
        result = await self.session.scalars(
            select(StudentPortfolioEntry)
            .where(StudentPortfolioEntry.student_profile_id == profile_id, StudentPortfolioEntry.kind == kind)
            .order_by(StudentPortfolioEntry.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.all())

    async def get_entry(self, profile_id: str, kind: str, entry_id: str) -> StudentPortfolioEntry:
        item = await self.session.scalar(select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.id == entry_id,
            StudentPortfolioEntry.student_profile_id == profile_id,
            StudentPortfolioEntry.kind == kind,
        ))
        if item is None:
            raise ResourceNotFoundError("Portfolio record not found")
        return item

    async def create_entry(self, profile_id: str, kind: str, data: dict[str, Any]) -> StudentPortfolioEntry:
        item = StudentPortfolioEntry(id=str(uuid4()), student_profile_id=profile_id, kind=kind, **data)
        self.session.add(item)
        await self._commit()
        await self.session.refresh(item)
        return item

    async def update_entry(self, profile_id: str, kind: str, entry_id: str, data: dict[str, Any]) -> StudentPortfolioEntry:
        item = await self.get_entry(profile_id, kind, entry_id)
        for key, value in data.items():
            setattr(item, key, value)
        await self._commit()
        await self.session.refresh(item)
        return item

    async def delete_entry(self, profile_id: str, kind: str, entry_id: str) -> None:
        item = await self.get_entry(profile_id, kind, entry_id)
        await self.session.delete(item)
        await self._commit()

    async def list_academic_records(self, profile_id: str, limit: int, offset: int) -> list[StudentAcademicRecord]:
        result = await self.session.scalars(
            select(StudentAcademicRecord).where(StudentAcademicRecord.student_profile_id == profile_id)
            .order_by(StudentAcademicRecord.start_date.desc(), StudentAcademicRecord.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.all())

    async def get_academic_record(self, profile_id: str, record_id: str) -> StudentAcademicRecord:
        item = await self.session.scalar(select(StudentAcademicRecord).where(
            StudentAcademicRecord.id == record_id,
            StudentAcademicRecord.student_profile_id == profile_id,
        ))
        if item is None:
            raise ResourceNotFoundError("Academic record not found")
        return item

    async def create_academic_record(self, profile_id: str, data: dict[str, Any]) -> StudentAcademicRecord:
        item = StudentAcademicRecord(id=str(uuid4()), student_profile_id=profile_id, **data)
        self.session.add(item)
        await self._commit()
        await self.session.refresh(item)
        return item

    async def update_academic_record(self, profile_id: str, record_id: str, data: dict[str, Any]) -> StudentAcademicRecord:
        item = await self.get_academic_record(profile_id, record_id)
        for key, value in data.items():
            setattr(item, key, value)
        await self._commit()
        await self.session.refresh(item)
        return item

    async def delete_academic_record(self, profile_id: str, record_id: str) -> None:
        item = await self.get_academic_record(profile_id, record_id)
        await self.session.delete(item)
        await self._commit()

    async def list_resumes(self, profile_id: str) -> list[StudentResume]:
        result = await self.session.scalars(select(StudentResume).where(
            StudentResume.student_profile_id == profile_id
        ).order_by(StudentResume.created_at.desc()))
        return list(result.all())

    async def get_resume(self, profile_id: str, resume_id: str) -> StudentResume:
        item = await self.session.scalar(select(StudentResume).where(
            StudentResume.id == resume_id, StudentResume.student_profile_id == profile_id
        ))
        if item is None:
            raise ResourceNotFoundError("Resume not found")
        return item

    async def create_resume(self, profile_id: str, account_id: str, data: dict[str, Any]) -> StudentResume:
        storage = await self.session.scalar(select(StorageFile).where(
            StorageFile.id == data["storage_file_id"], StorageFile.uploaded_by_account_id == account_id
        ))
        if storage is None:
            raise ResourceNotFoundError("Owned storage file not found")
        if data.get("is_primary"):
            current = list((await self.session.scalars(select(StudentResume).where(
                StudentResume.student_profile_id == profile_id, StudentResume.is_primary.is_(True)
            ))).all())
            for item in current:
                item.is_primary = False
        item = StudentResume(id=str(uuid4()), student_profile_id=profile_id, **data)
        self.session.add(item)
        await self._commit("Resume already references this file")
        await self.session.refresh(item)
        return item

    async def delete_resume(self, profile_id: str, resume_id: str) -> None:
        item = await self.get_resume(profile_id, resume_id)
        await self.session.delete(item)
        await self._commit()

    async def completeness(self, profile: StudentProfile, account: Account) -> dict[str, Any]:
        entries = list((await self.session.scalars(select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.student_profile_id == profile.id
        ))).all())
        academics = list((await self.session.scalars(select(StudentAcademicRecord).where(
            StudentAcademicRecord.student_profile_id == profile.id
        ))).all())
        checks = {
            "name": bool(account.full_name.strip()),
            "phone": bool(account.phone_number),
            "academic_context": bool(profile.cohort_id),
            "academics": bool(academics),
            "skills": any(entry.kind == "skill" for entry in entries),
            "projects": any(entry.kind == "project" for entry in entries),
            "experience": any(entry.kind == "experience" for entry in entries),
        }
        completed = sum(checks.values())
        return {"completed": completed, "total": len(checks),
                "percentage": round(100 * completed / len(checks)), "sections": checks}

    async def summary(self, profile: StudentProfile, account: Account) -> dict[str, Any]:
        entries = list((await self.session.scalars(select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.student_profile_id == profile.id
        ))).all())
        academics = list((await self.session.scalars(select(StudentAcademicRecord).where(
            StudentAcademicRecord.student_profile_id == profile.id
        ))).all())
        return {
            "student": {"id": profile.id, "full_name": account.full_name,
                        "enrollment_number": profile.enrollment_number,
                        "current_semester": profile.current_semester,
                        "cgpa": str(profile.cgpa) if profile.cgpa is not None else None},
            "counts": {"academic_records": len(academics),
                       **{name: sum(entry.kind == kind for entry in entries)
                          for name, kind in COLLECTION_KIND.items()}},
            "verified_academic_records": sum(record.is_verified for record in academics),
        }

    async def cv(self, profile: StudentProfile, account: Account) -> dict[str, Any]:
        entries = list((await self.session.scalars(select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.student_profile_id == profile.id
        ).order_by(StudentPortfolioEntry.start_date.desc()))).all())
        academics = list((await self.session.scalars(select(StudentAcademicRecord).where(
            StudentAcademicRecord.student_profile_id == profile.id
        ).order_by(StudentAcademicRecord.start_date.desc()))).all())
        sections = {
            name: [_row(entry, {"kind", "student_profile_id", "verified_by_account_id"})
                   for entry in entries if entry.kind == kind]
            for name, kind in COLLECTION_KIND.items()
        }
        return {
            "profile": {"full_name": account.full_name, "email": account.email,
                        "phone_number": account.phone_number},
            "academics": [_row(record, {"student_profile_id", "verified_by_account_id"})
                          for record in academics],
            **sections,
        }

    async def timeline(self, profile: StudentProfile, limit: int) -> dict[str, Any]:
        entries = list((await self.session.scalars(select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.student_profile_id == profile.id
        ))).all())
        academics = list((await self.session.scalars(select(StudentAcademicRecord).where(
            StudentAcademicRecord.student_profile_id == profile.id
        ))).all())
        placements = (await self.session.execute(
            select(InternshipPlacement, InternshipOpportunity.title, InternshipProvider.company_name)
            .join(InternshipApplication, InternshipApplication.id == InternshipPlacement.application_id)
            .join(InternshipOpportunity, InternshipOpportunity.id == InternshipApplication.opportunity_id)
            .join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id)
            .where(InternshipPlacement.student_id == profile.id)
        )).all()
        events = []
        for placement, title, company in placements:
            events.append({"id": placement.id, "kind": "internship", "title": title,
                           "organization": company, "date": placement.start_date,
                           "end_date": placement.end_date, "status": placement.status})
        for entry in entries:
            when = entry.start_date or entry.issued_date or entry.created_at.date()
            events.append({"id": entry.id, "kind": entry.kind, "title": entry.title,
                           "date": when, "end_date": entry.end_date})
        for record in academics:
            when = record.start_date or record.end_date or record.created_at.date()
            events.append({"id": record.id, "kind": "academic", "title": record.qualification,
                           "date": when, "end_date": record.end_date, "verified": record.is_verified})
        events.sort(key=lambda item: (item["date"], item["id"]), reverse=True)
        return {"items": events[:limit], "limit": limit}
