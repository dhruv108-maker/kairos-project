"""Institution onboarding and institution-scoped academic administration."""
from __future__ import annotations

from uuid import uuid4
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account, AcademicYear, Cohort, Department, FacultyProfile, Programme, School, StudentProfile
from app.models.organizations import Team
from app.models.institutions import Institution, InstitutionMembership
from app.modules.audit.service import AuditService


class InstitutionAccessError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class InstitutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def platform_admin(self, account_id: str) -> bool:
        from app.models.academic import AccountRole, Role
        result = await self.db.execute(
            select(Role.name).join(AccountRole, AccountRole.role_id == Role.id)
            .where(AccountRole.account_id == account_id)
        )
        return "PLATFORM_ADMIN" in set(result.scalars().all())

    async def require_platform_admin(self, account_id: str) -> None:
        if not await self.platform_admin(account_id):
            raise InstitutionAccessError(403, "Platform administrator permission required")

    async def membership(self, institution_id: str, account_id: str) -> InstitutionMembership:
        result = await self.db.execute(select(InstitutionMembership).where(
            InstitutionMembership.institution_id == institution_id,
            InstitutionMembership.account_id == account_id,
            InstitutionMembership.status == "ACTIVE",
        ))
        member = result.scalar_one_or_none()
        if member is None:
            raise InstitutionAccessError(403, "Active institution membership required")
        institution = await self.db.get(Institution, institution_id)
        if institution is None:
            raise InstitutionAccessError(404, "Institution not found")
        if institution.status != "ACTIVE":
            raise InstitutionAccessError(403, "Institution is not active")
        return member

    async def require_admin(self, institution_id: str, account_id: str) -> InstitutionMembership:
        member = await self.membership(institution_id, account_id)
        if member.role != "INSTITUTION_ADMIN":
            raise InstitutionAccessError(403, "Institution administrator permission required")
        return member

    async def create_institution(self, actor_id: str, payload: dict) -> Institution:
        await self.require_platform_admin(actor_id)
        item = Institution(
            id=str(uuid4()), name=payload["name"].strip(), slug=payload["slug"].strip().lower(),
            status="PENDING", contact_email=payload.get("contact_email"),
            website_url=payload.get("website_url"), created_by_account_id=actor_id,
        )
        self.db.add(item)
        AuditService(self.db).record(actor_id, item.id, "institution.created", "institution", item.id, {"slug": item.slug})
        await self.db.commit()
        await self.db.refresh(item)
        return item


    async def register_institution(self, actor_id: str, payload: dict) -> Institution:
        account = await self.db.get(Account, actor_id)
        if account is None or not account.is_active or not account.is_verified:
            raise InstitutionAccessError(403, "An active, verified Kairos account is required")
        slug = payload["slug"].strip().lower()
        conditions = [Institution.slug == slug]
        if payload.get("registration_number"):
            conditions.append(Institution.registration_number == payload["registration_number"].strip())
        existing = await self.db.scalar(select(Institution).where(or_(*conditions)))
        if existing is not None:
            raise InstitutionAccessError(409, "Institution slug or registration number is already registered")
        item = Institution(
            id=str(uuid4()), name=payload["name"].strip(), slug=slug, status="PENDING_APPROVAL",
            contact_email=(payload.get("contact_email") or account.email).strip().lower(),
            website_url=str(payload["website_url"]) if payload.get("website_url") else None,
            institution_type=payload.get("institution_type", "COLLEGE"),
            registration_number=payload.get("registration_number"), description=payload.get("description"),
            address=payload.get("address"), country=payload.get("country"), state=payload.get("state"),
            city=payload.get("city"), postal_code=payload.get("postal_code"),
            created_by_account_id=actor_id,
        )
        self.db.add(item)
        self.db.add(InstitutionMembership(
            institution_id=item.id, account_id=actor_id, role="INSTITUTION_ADMIN",
            status="PENDING", invited_by_account_id=actor_id,
        ))
        AuditService(self.db).record(actor_id, item.id, "institution.registration_submitted",
            "institution", item.id, {"slug": item.slug, "institution_type": item.institution_type})
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(item)
        return item

    async def registration_status(self, institution_id: str, actor_id: str) -> dict:
        item = await self.db.get(Institution, institution_id)
        if item is None:
            raise InstitutionAccessError(404, "Institution not found")
        if item.created_by_account_id != actor_id and not await self.platform_admin(actor_id):
            raise InstitutionAccessError(403, "Only the registering account or a platform administrator can view registration status")
        return {"institution_id": item.id, "status": item.status, "created_at": item.created_at,
                "updated_at": item.updated_at, "reviewed": item.status in {"ACTIVE", "REJECTED", "SUSPENDED"}}

    async def list_institutions(self, actor_id: str) -> list[Institution]:
        await self.require_platform_admin(actor_id)
        result = await self.db.execute(select(Institution).order_by(Institution.created_at.desc()))
        return list(result.scalars().all())

    async def get_institution(self, institution_id: str, actor_id: str) -> Institution:
        if not await self.platform_admin(actor_id):
            await self.membership(institution_id, actor_id)
        item = await self.db.get(Institution, institution_id)
        if item is None:
            raise InstitutionAccessError(404, "Institution not found")
        return item

    async def set_status(self, institution_id: str, actor_id: str, status: str) -> Institution:
        await self.require_platform_admin(actor_id)
        item = await self.db.get(Institution, institution_id)
        if item is None:
            raise InstitutionAccessError(404, "Institution not found")
        old_status = item.status
        item.status = status
        if status == "ACTIVE":
            pending_membership = await self.db.get(InstitutionMembership, (institution_id, item.created_by_account_id))
            if pending_membership is not None and pending_membership.status == "PENDING":
                pending_membership.status = "ACTIVE"
        AuditService(self.db).record(actor_id, institution_id, "institution.status_changed", "institution", item.id, {"from": old_status, "to": status})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def assign_member(self, institution_id: str, actor_id: str, account_id: str, role: str) -> InstitutionMembership:
        await self.require_platform_admin(actor_id)
        institution = await self.db.get(Institution, institution_id)
        account = await self.db.get(Account, account_id)
        if institution is None or account is None:
            raise InstitutionAccessError(404, "Institution or account not found")
        if role not in {"INSTITUTION_ADMIN", "FACULTY", "MEMBER"}:
            raise InstitutionAccessError(422, "Unsupported institution membership role")
        item = await self.db.get(InstitutionMembership, (institution_id, account_id))
        if item is None:
            item = InstitutionMembership(institution_id=institution_id, account_id=account_id, role=role, status="ACTIVE", invited_by_account_id=actor_id)
            self.db.add(item)
        else:
            item.role, item.status, item.invited_by_account_id = role, "ACTIVE", actor_id
        AuditService(self.db).record(actor_id, institution_id, "institution.member_upserted", "institution_membership", account_id, {"role": role, "status": item.status})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_members(self, institution_id: str, actor_id: str) -> list[InstitutionMembership]:
        await self.membership(institution_id, actor_id)
        result = await self.db.execute(select(InstitutionMembership).where(
            InstitutionMembership.institution_id == institution_id
        ).order_by(InstitutionMembership.created_at))
        return list(result.scalars().all())

    async def revoke_member(self, institution_id: str, actor_id: str, target_account_id: str) -> None:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.get(InstitutionMembership, (institution_id, target_account_id))
        if item is None:
            raise InstitutionAccessError(404, "Institution membership not found")
        if item.role == "INSTITUTION_ADMIN" and target_account_id == actor_id:
            raise InstitutionAccessError(409, "Administrators cannot revoke their own membership")
        item.status = "REVOKED"
        AuditService(self.db).record(actor_id, institution_id, "institution.member_revoked", "institution_membership", target_account_id, {"role": item.role})
        await self.db.commit()

    async def create_school(self, institution_id: str, actor_id: str, code: str, name: str) -> School:
        await self.require_admin(institution_id, actor_id)
        item = School(id=str(uuid4()), code=code.strip().upper(), name=name.strip(), institution_id=institution_id, is_active=True)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "academic.school_created", "school", item.id, {"code": item.code})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_schools(self, institution_id: str, actor_id: str) -> list[School]:
        await self.membership(institution_id, actor_id)
        result = await self.db.execute(select(School).where(School.institution_id == institution_id).order_by(School.name))
        return list(result.scalars().all())

    async def create_department(self, institution_id: str, actor_id: str, school_id: str, code: str, name: str) -> Department:
        await self.require_admin(institution_id, actor_id)
        school = await self.db.get(School, school_id)
        if school is None or school.institution_id != institution_id:
            raise InstitutionAccessError(404, "School not found in this institution")
        item = Department(id=str(uuid4()), school_id=school_id, code=code.strip().upper(), name=name.strip(), is_active=True)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "academic.department_created", "department", item.id, {"school_id": school_id, "code": item.code})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_departments(self, institution_id: str, actor_id: str, school_id: str | None = None) -> list[Department]:
        await self.membership(institution_id, actor_id)
        query = select(Department).join(School, School.id == Department.school_id).where(School.institution_id == institution_id)
        if school_id:
            query = query.where(Department.school_id == school_id)
        result = await self.db.execute(query.order_by(Department.name))
        return list(result.scalars().all())

    async def create_programme(self, institution_id: str, actor_id: str, department_id: str, code: str, name: str, degree_level: str, duration_years: int) -> Programme:
        await self.require_admin(institution_id, actor_id)
        department = await self.db.get(Department, department_id)
        school = await self.db.get(School, department.school_id) if department else None
        if school is None or school.institution_id != institution_id:
            raise InstitutionAccessError(404, "Department not found in this institution")
        item = Programme(id=str(uuid4()), department_id=department_id, code=code.strip().upper(), name=name.strip(), degree_level=degree_level.strip(), duration_years=duration_years, is_active=True)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "academic.programme_created", "programme", item.id, {"department_id": department_id, "code": item.code})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_programmes(self, institution_id: str, actor_id: str, department_id: str | None = None) -> list[Programme]:
        await self.membership(institution_id, actor_id)
        query = select(Programme).join(Department, Department.id == Programme.department_id).join(School, School.id == Department.school_id).where(School.institution_id == institution_id)
        if department_id:
            query = query.where(Programme.department_id == department_id)
        result = await self.db.execute(query.order_by(Programme.name))
        return list(result.scalars().all())

    async def create_academic_year(self, institution_id: str, actor_id: str, year_label: str, start_date, end_date, is_current: bool) -> AcademicYear:
        await self.require_admin(institution_id, actor_id)
        if end_date <= start_date:
            raise InstitutionAccessError(422, "Academic year end_date must be after start_date")
        item = AcademicYear(id=str(uuid4()), year_label=year_label.strip(), start_date=start_date, end_date=end_date, is_current=is_current, institution_id=institution_id)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "academic.year_created", "academic_year", item.id, {"year_label": item.year_label})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_academic_years(self, institution_id: str, actor_id: str) -> list[AcademicYear]:
        await self.membership(institution_id, actor_id)
        result = await self.db.execute(select(AcademicYear).where(AcademicYear.institution_id == institution_id).order_by(AcademicYear.start_date.desc()))
        return list(result.scalars().all())

    async def create_cohort(self, institution_id: str, actor_id: str, programme_id: str, academic_year_id: str, name: str, graduation_year: int) -> Cohort:
        await self.require_admin(institution_id, actor_id)
        programme = await self.db.get(Programme, programme_id)
        department = await self.db.get(Department, programme.department_id) if programme else None
        school = await self.db.get(School, department.school_id) if department else None
        year = await self.db.get(AcademicYear, academic_year_id)
        if school is None or school.institution_id != institution_id or year is None or year.institution_id != institution_id:
            raise InstitutionAccessError(422, "Programme and academic year must belong to this institution")
        item = Cohort(id=str(uuid4()), programme_id=programme_id, academic_year_id=academic_year_id, name=name.strip(), graduation_year=graduation_year)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "academic.cohort_created", "cohort", item.id, {"programme_id": programme_id, "academic_year_id": academic_year_id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_cohorts(self, institution_id: str, actor_id: str, programme_id: str | None = None) -> list[Cohort]:
        await self.membership(institution_id, actor_id)
        query = select(Cohort).join(Programme, Programme.id == Cohort.programme_id).join(Department, Department.id == Programme.department_id).join(School, School.id == Department.school_id).where(School.institution_id == institution_id)
        if programme_id:
            query = query.where(Cohort.programme_id == programme_id)
        result = await self.db.execute(query.order_by(Cohort.graduation_year.desc(), Cohort.name))
        return list(result.scalars().all())


    async def update_school(self, institution_id: str, actor_id: str, school_id: str, code: str | None, name: str | None, is_active: bool | None) -> School:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.get(School, school_id)
        if item is None or item.institution_id != institution_id:
            raise InstitutionAccessError(404, "School not found in this institution")
        if code is not None:
            item.code = code.strip().upper()
        if name is not None:
            item.name = name.strip()
        if is_active is not None:
            item.is_active = is_active
        AuditService(self.db).record(actor_id, institution_id, "academic.school_updated", "school", item.id, {"code": item.code, "is_active": item.is_active})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_school(self, institution_id: str, actor_id: str, school_id: str) -> None:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.get(School, school_id)
        if item is None or item.institution_id != institution_id:
            raise InstitutionAccessError(404, "School not found in this institution")
        used = await self.db.scalar(select(func.count(Department.id)).where(Department.school_id == school_id))
        if used:
            raise InstitutionAccessError(409, "School cannot be deleted while departments exist")
        AuditService(self.db).record(actor_id, institution_id, "academic.school_deleted", "school", item.id, {"code": item.code})
        await self.db.delete(item)
        await self.db.commit()

    async def update_department(self, institution_id: str, actor_id: str, department_id: str, code: str | None, name: str | None, is_active: bool | None) -> Department:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.scalar(select(Department).join(School, School.id == Department.school_id).where(
            Department.id == department_id, School.institution_id == institution_id))
        if item is None:
            raise InstitutionAccessError(404, "Department not found in this institution")
        if code is not None:
            item.code = code.strip().upper()
        if name is not None:
            item.name = name.strip()
        if is_active is not None:
            item.is_active = is_active
        AuditService(self.db).record(actor_id, institution_id, "academic.department_updated", "department", item.id, {"code": item.code, "is_active": item.is_active})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_department(self, institution_id: str, actor_id: str, department_id: str) -> None:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.scalar(select(Department).join(School, School.id == Department.school_id).where(
            Department.id == department_id, School.institution_id == institution_id))
        if item is None:
            raise InstitutionAccessError(404, "Department not found in this institution")
        programme_count = await self.db.scalar(select(func.count(Programme.id)).where(Programme.department_id == department_id))
        faculty_count = await self.db.scalar(select(func.count(FacultyProfile.id)).where(FacultyProfile.department_id == department_id))
        team_count = await self.db.scalar(select(func.count(Team.id)).where(Team.department_id == department_id))
        if programme_count or faculty_count or team_count:
            raise InstitutionAccessError(409, "Department cannot be deleted while programmes, faculty, or teams reference it")
        AuditService(self.db).record(actor_id, institution_id, "academic.department_deleted", "department", item.id, {"code": item.code})
        await self.db.delete(item)
        await self.db.commit()

    async def update_programme(self, institution_id: str, actor_id: str, programme_id: str, code: str | None, name: str | None, degree_level: str | None, duration_years: int | None, is_active: bool | None) -> Programme:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.scalar(select(Programme).join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id).where(Programme.id == programme_id, School.institution_id == institution_id))
        if item is None:
            raise InstitutionAccessError(404, "Programme not found in this institution")
        if code is not None:
            item.code = code.strip().upper()
        if name is not None:
            item.name = name.strip()
        if degree_level is not None:
            item.degree_level = degree_level.strip()
        if duration_years is not None:
            item.duration_years = duration_years
        if is_active is not None:
            item.is_active = is_active
        AuditService(self.db).record(actor_id, institution_id, "academic.programme_updated", "programme", item.id, {"code": item.code, "is_active": item.is_active})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_programme(self, institution_id: str, actor_id: str, programme_id: str) -> None:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.scalar(select(Programme).join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id).where(Programme.id == programme_id, School.institution_id == institution_id))
        if item is None:
            raise InstitutionAccessError(404, "Programme not found in this institution")
        if await self.db.scalar(select(func.count(Cohort.id)).where(Cohort.programme_id == programme_id)):
            raise InstitutionAccessError(409, "Programme cannot be deleted while cohorts exist")
        AuditService(self.db).record(actor_id, institution_id, "academic.programme_deleted", "programme", item.id, {"code": item.code})
        await self.db.delete(item)
        await self.db.commit()

    async def update_academic_year(self, institution_id: str, actor_id: str, year_id: str, year_label: str | None, start_date, end_date, is_current: bool | None) -> AcademicYear:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.get(AcademicYear, year_id)
        if item is None or item.institution_id != institution_id:
            raise InstitutionAccessError(404, "Academic year not found in this institution")
        next_start = start_date if start_date is not None else item.start_date
        next_end = end_date if end_date is not None else item.end_date
        if next_end <= next_start:
            raise InstitutionAccessError(422, "Academic year end_date must be after start_date")
        if year_label is not None:
            item.year_label = year_label.strip()
        item.start_date, item.end_date = next_start, next_end
        if is_current is True:
            others = await self.db.execute(select(AcademicYear).where(
                AcademicYear.institution_id == institution_id, AcademicYear.id != year_id))
            for other in others.scalars().all():
                other.is_current = False
        if is_current is not None:
            item.is_current = is_current
        AuditService(self.db).record(actor_id, institution_id, "academic.year_updated", "academic_year", item.id, {"year_label": item.year_label, "is_current": item.is_current})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_academic_year(self, institution_id: str, actor_id: str, year_id: str) -> None:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.get(AcademicYear, year_id)
        if item is None or item.institution_id != institution_id:
            raise InstitutionAccessError(404, "Academic year not found in this institution")
        if await self.db.scalar(select(func.count(Cohort.id)).where(Cohort.academic_year_id == year_id)):
            raise InstitutionAccessError(409, "Academic year cannot be deleted while cohorts reference it")
        AuditService(self.db).record(actor_id, institution_id, "academic.year_deleted", "academic_year", item.id, {"year_label": item.year_label})
        await self.db.delete(item)
        await self.db.commit()

    async def update_cohort(self, institution_id: str, actor_id: str, cohort_id: str, name: str | None, graduation_year: int | None, programme_id: str | None, academic_year_id: str | None, is_active: bool | None = None) -> Cohort:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.scalar(select(Cohort).join(Programme, Programme.id == Cohort.programme_id)
            .join(Department, Department.id == Programme.department_id).join(School, School.id == Department.school_id)
            .where(Cohort.id == cohort_id, School.institution_id == institution_id))
        if item is None:
            raise InstitutionAccessError(404, "Cohort not found in this institution")
        next_programme_id = programme_id or item.programme_id
        next_year_id = academic_year_id or item.academic_year_id
        programme = await self.db.get(Programme, next_programme_id)
        department = await self.db.get(Department, programme.department_id) if programme else None
        school = await self.db.get(School, department.school_id) if department else None
        year = await self.db.get(AcademicYear, next_year_id)
        if school is None or school.institution_id != institution_id or year is None or year.institution_id != institution_id:
            raise InstitutionAccessError(422, "Programme and academic year must belong to this institution")
        if name is not None:
            item.name = name.strip()
        if graduation_year is not None:
            item.graduation_year = graduation_year
        item.programme_id, item.academic_year_id = next_programme_id, next_year_id
        if is_active is not None:
            item.is_active = is_active
        AuditService(self.db).record(actor_id, institution_id, "academic.cohort_updated", "cohort", item.id, {"programme_id": item.programme_id, "academic_year_id": item.academic_year_id, "is_active": item.is_active})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_cohort(self, institution_id: str, actor_id: str, cohort_id: str) -> None:
        await self.require_admin(institution_id, actor_id)
        item = await self.db.scalar(select(Cohort).join(Programme, Programme.id == Cohort.programme_id)
            .join(Department, Department.id == Programme.department_id).join(School, School.id == Department.school_id)
            .where(Cohort.id == cohort_id, School.institution_id == institution_id))
        if item is None:
            raise InstitutionAccessError(404, "Cohort not found in this institution")
        if await self.db.scalar(select(func.count(StudentProfile.id)).where(StudentProfile.cohort_id == cohort_id)):
            raise InstitutionAccessError(409, "Cohort cannot be deleted while students are enrolled")
        AuditService(self.db).record(actor_id, institution_id, "academic.cohort_deleted", "cohort", item.id, {"name": item.name})
        await self.db.delete(item)
        await self.db.commit()
