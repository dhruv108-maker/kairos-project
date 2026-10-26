from __future__ import annotations

import hmac
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession, account_roles
from app.api.schemas import (
    AccountPublic,
    AuthResponse,
    FacultyRegistration,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    StudentRegistration,
    VerifyEmailRequest,
)
from app.core.config import settings
from app.core.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.academic import (
    Account,
    AccountRole,
    AcademicYear,
    Cohort,
    Department,
    FacultyProfile,
    Programme,
    School,
    Role,
    StudentProfile,
    Student,
    StudentEnrollment,
)
from app.services.email import send_verification_email, send_password_reset_email
from app.modules.identity.service import IdentityService
from app.models.institutions import Institution
from app.models.institution_domains import InstitutionDomain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


async def _account_public(db, account: Account) -> AccountPublic:
    return AccountPublic(
        id=str(account.id),
        email=account.email,
        full_name=account.full_name,
        phone_number=account.phone_number,
        is_active=account.is_active,
        is_verified=account.is_verified,
        email_verified=account.is_verified,
        identity_verified=bool(account.identity_verified),
        last_login_at=account.last_login_at,
        roles=await account_roles(db, account.id),
    )


async def _ensure_role(db, name: str) -> Role:
    return await IdentityService(db).ensure_role(name)


async def _new_verification_token(account: Account) -> str:
    token = create_token(account.id, "email_verification", timedelta(minutes=30))
    account.verification_token = hash_token(token)
    return token


async def _send_verification(account: Account, token: str) -> bool:
    try:
        await send_verification_email(account.email, token)
        return True
    except Exception:
        # Delivery failures are intentionally not returned with provider internals or secrets.
        return False


async def _student_registration_identity_exists(db, payload: StudentRegistration) -> bool:
    """Return whether this registration collides with a canonical student identity.

    Used after a failed transaction as well as before writes, so unrelated FK,
    schema, and NOT NULL failures are not mislabeled as duplicate-registration 409s.
    """
    return bool(await db.scalar(
        text("""
            SELECT
                EXISTS (SELECT 1 FROM accounts WHERE LOWER(email) = :email)
                OR EXISTS (SELECT 1 FROM students WHERE student_number = :enrollment_number)
                OR EXISTS (SELECT 1 FROM student_profiles WHERE enrollment_number = :enrollment_number)
        """),
        {
            "email": payload.email.strip().lower(),
            "enrollment_number": payload.enrollment_number,
        },
    ))


async def _faculty_registration_identity_exists(db, payload: FacultyRegistration) -> bool:
    """Return whether email or employee identity is already assigned."""
    return bool(await db.scalar(
        text("""
            SELECT
                EXISTS (SELECT 1 FROM accounts WHERE LOWER(email) = :email)
                OR EXISTS (
                    SELECT 1 FROM faculty
                    WHERE employee_number = :employee_code
                       OR employee_code = :employee_code
                )
        """),
        {
            "email": payload.email.strip().lower(),
            "employee_code": payload.employee_code,
        },
    ))


async def _register_student_sqlite(payload: StudentRegistration, db) -> RegistrationResponse:
    """Exercise the mounted registration workflow with its canonical ORM schema.

    Production keeps the MySQL-native SQL path below; this SQLite-only adapter is
    for deterministic route integration tests and validates the same ownership and
    institution/cohort invariants before persisting any account rows.
    """
    today = date.today()
    account: Account
    token: str
    try:
        async with db.begin():
            domain = payload.email.rsplit("@", 1)[1].strip().lower().rstrip(".")
            institution = await db.scalar(
                select(Institution)
                .join(InstitutionDomain, InstitutionDomain.institution_id == Institution.id)
                .where(
                    InstitutionDomain.normalized_domain == domain,
                    InstitutionDomain.is_verified.is_(True),
                    func.upper(Institution.status) == "ACTIVE",
                )
                .limit(1)
            )
            if institution is None:
                raise HTTPException(
                    status_code=422,
                    detail="Your email domain is not verified for an active institution. Contact your institution administrator.",
                )
            if payload.institution_id and str(payload.institution_id) != str(institution.id):
                raise HTTPException(status_code=422, detail="The institution does not match your verified email domain")
            if not payload.school_id or not payload.department_id:
                raise HTTPException(status_code=422, detail="Choose a school and department")

            department = await db.scalar(
                select(Department)
                .join(School, School.id == Department.school_id)
                .where(
                    Department.id == payload.department_id,
                    Department.school_id == payload.school_id,
                    Department.is_active.is_(True),
                    func.upper(Department.status) == "ACTIVE",
                    School.id == payload.school_id,
                    School.institution_id == institution.id,
                    School.is_active.is_(True),
                    func.upper(School.status) == "ACTIVE",
                )
            )
            if department is None:
                raise HTTPException(status_code=422, detail="Choose an active school and department from your verified institution.")

            programme_id = None
            if payload.programme_id:
                programme = await db.scalar(
                    select(Programme)
                    .join(Department, Department.id == Programme.department_id)
                    .join(School, School.id == Department.school_id)
                    .where(
                        Programme.id == payload.programme_id,
                        Programme.department_id == department.id,
                        Programme.is_active.is_(True),
                        func.upper(Programme.status) == "ACTIVE",
                        Department.is_active.is_(True),
                        School.id == payload.school_id,
                        School.institution_id == institution.id,
                        School.is_active.is_(True),
                    )
                )
                if programme is None:
                    raise HTTPException(status_code=422, detail="Choose an active programme within your selected department.")
                programme_id = programme.id

            cohort = None
            academic_year = None
            if payload.cohort_id:
                cohort = await db.scalar(
                    select(Cohort)
                    .join(Programme, Programme.id == Cohort.programme_id)
                    .join(Department, Department.id == Programme.department_id)
                    .join(School, School.id == Department.school_id)
                    .where(
                        Cohort.id == payload.cohort_id,
                        Cohort.is_active.is_(True),
                        Programme.is_active.is_(True),
                        func.upper(Programme.status) == "ACTIVE",
                        Department.id == department.id,
                        Department.is_active.is_(True),
                        School.id == payload.school_id,
                        School.institution_id == institution.id,
                        School.is_active.is_(True),
                    )
                )
                if cohort is None or (programme_id is not None and cohort.programme_id != programme_id):
                    raise HTTPException(status_code=422, detail="The selected cohort must be active and belong to the selected department and institution.")
                programme_id = cohort.programme_id
                academic_year = await db.scalar(
                    select(AcademicYear).where(
                        AcademicYear.institution_id == institution.id,
                        AcademicYear.start_date <= today,
                        AcademicYear.end_date >= today,
                    ).order_by(AcademicYear.start_date.desc()).limit(1)
                )
                if academic_year is None:
                    raise HTTPException(
                        status_code=422,
                        detail="No current academic year is configured for this institution, so the student cannot be enrolled in the selected cohort yet.",
                    )

            if await db.scalar(select(Account.id).where(func.lower(Account.email) == payload.email)) is not None:
                raise HTTPException(status_code=409, detail="Registration conflicts with an existing account or enrollment number")
            if await db.scalar(select(StudentProfile.id).where(StudentProfile.enrollment_number == payload.enrollment_number)) is not None:
                raise HTTPException(status_code=409, detail="Registration conflicts with an existing account or enrollment number")

            account = Account(
                id=str(uuid4()), email=payload.email, password_hash=hash_password(payload.password),
                full_name=payload.full_name, display_name=payload.full_name,
                account_status="pending", is_active=True, is_verified=False,
            )
            token = await _new_verification_token(account)
            db.add(account)
            await db.flush()

            student = Student(
                account_id=account.id,
                student_number=payload.enrollment_number,
                legal_name=payload.full_name,
            )
            db.add(student)
            await db.flush()
            db.add(StudentProfile(
                student_id=student.id,
                account_id=account.id,
                enrollment_number=payload.enrollment_number,
                department_id=department.id,
                programme_id=programme_id,
                cohort_id=cohort.id if cohort else None,
                current_semester=1,
            ))
            if cohort is not None and academic_year is not None:
                db.add(StudentEnrollment(
                    student_id=student.id, cohort_id=cohort.id,
                    academic_year_id=academic_year.id, starts_on=today,
                    enrollment_status="active",
                ))

            role = await db.scalar(select(Role).where(Role.name == "STUDENT"))
            if role is None:
                role = Role(id=str(uuid4()), name="STUDENT", code="STUDENT")
                db.add(role)
                await db.flush()
            db.add(AccountRole(account_id=account.id, role_id=role.id, institution_id=institution.id))
    except HTTPException:
        raise
    except IntegrityError:
        if await _student_registration_identity_exists(db, payload):
            raise HTTPException(
                status_code=409,
                detail="Registration conflicts with an existing account or enrollment number",
            ) from None
        raise

    sent = await _send_verification(account, token)
    return RegistrationResponse(
        account_id=str(account.id),
        message=(
            "Account created. Check your email to verify it."
            if sent
            else "Account created but verification email could not be sent. Request a new link after email delivery is configured."
        ),
        verification_email_sent=sent,
    )


async def _register_faculty_sqlite(payload: FacultyRegistration, db) -> RegistrationResponse:
    """SQLite-only route adapter preserving the same faculty approval contract."""
    if not payload.school_id or not payload.department_id:
        raise HTTPException(status_code=422, detail="Choose an active department within the selected school")

    account: Account
    token: str
    try:
        async with db.begin():
            department = await db.scalar(
                select(Department)
                .join(School, School.id == Department.school_id)
                .join(Institution, Institution.id == School.institution_id)
                .where(
                    Department.id == payload.department_id,
                    Department.school_id == payload.school_id,
                    Department.is_active.is_(True),
                    func.upper(Department.status) == "ACTIVE",
                    School.is_active.is_(True),
                    func.upper(School.status) == "ACTIVE",
                    func.upper(Institution.status) == "ACTIVE",
                )
            )
            if department is None:
                raise HTTPException(status_code=422, detail="Choose an active department within the selected school")
            school = await db.get(School, payload.school_id)
            if school is None or school.institution_id is None:
                raise HTTPException(status_code=422, detail="The selected school is not linked to an institution")
            institution = await db.get(Institution, school.institution_id)
            if institution is None or (institution.status or "").upper() != "ACTIVE":
                raise HTTPException(status_code=422, detail="The selected institution is inactive")
            if payload.institution_id and str(payload.institution_id) != str(institution.id):
                raise HTTPException(status_code=422, detail="The selected school and department do not belong to the selected institution")

            if await db.scalar(select(Account.id).where(func.lower(Account.email) == payload.email)) is not None:
                raise HTTPException(status_code=409, detail="Registration conflicts with an existing account or employee code")
            if await db.scalar(select(FacultyProfile.id).where(or_(
                FacultyProfile.employee_number == payload.employee_code,
                FacultyProfile.employee_code == payload.employee_code,
            ))) is not None:
                raise HTTPException(status_code=409, detail="Registration conflicts with an existing account or employee code")

            account = Account(
                id=str(uuid4()), email=payload.email, password_hash=hash_password(payload.password),
                full_name=payload.full_name, display_name=payload.full_name,
                account_status="pending", is_active=False, is_verified=False,
            )
            token = await _new_verification_token(account)
            db.add(account)
            await db.flush()
            db.add(FacultyProfile(
                account_id=account.id,
                employee_number=payload.employee_code,
                employee_code=payload.employee_code,
                display_name=payload.full_name,
                employment_status="active",
                department_id=department.id,
                designation=payload.designation,
            ))
            role = await db.scalar(select(Role).where(Role.name == "FACULTY"))
            if role is None:
                role = Role(id=str(uuid4()), name="FACULTY", code="FACULTY")
                db.add(role)
                await db.flush()
            db.add(AccountRole(account_id=account.id, role_id=role.id, institution_id=institution.id))
    except HTTPException:
        raise
    except IntegrityError:
        if await _faculty_registration_identity_exists(db, payload):
            raise HTTPException(
                status_code=409,
                detail="Registration conflicts with an existing account or employee code",
            ) from None
        raise

    sent = await _send_verification(account, token)
    return RegistrationResponse(
        account_id=str(account.id),
        message=(
            "Faculty account created. Verify the email; institutional approval is still required."
            if sent
            else "Faculty account created pending email verification and institutional approval. Verification email delivery is not available."
        ),
        verification_email_sent=sent,
        activation_pending=True,
    )


@router.post("/register/student", response_model=RegistrationResponse, status_code=201)
async def register_student(payload: StudentRegistration, db: DbSession) -> RegistrationResponse:
    """Register a student against the deployed MySQL schema.

    The production schema uses BIGINT AUTO_INCREMENT IDs and the tables
    accounts, students, student_enrollments, account_roles, and roles. It does
    not contain student_profiles or roles.description.
    """
    if len(payload.full_name) > 200:
        raise HTTPException(status_code=422, detail="Full name must be 200 characters or fewer")
    if db.get_bind().dialect.name == "sqlite":
        return await _register_student_sqlite(payload, db)

    try:
        async with db.begin():
            email_domain = payload.email.rsplit("@", 1)[1].strip().lower().rstrip(".")
            resolved_institution_id = await db.scalar(
                text("""
                    SELECT i.id
                    FROM institutions AS i
                    JOIN institution_domains AS d ON d.institution_id = i.id
                    WHERE d.normalized_domain = :domain
                      AND d.is_verified = 1
                      AND UPPER(i.status) = 'ACTIVE'
                    LIMIT 1
                """),
                {"domain": email_domain},
            )
            if resolved_institution_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="Your email domain is not verified for an active institution. Contact your institution administrator.",
                )
            if payload.institution_id and str(payload.institution_id) != str(resolved_institution_id):
                raise HTTPException(status_code=422, detail="The institution does not match your verified email domain")
            if not payload.school_id or not payload.department_id:
                raise HTTPException(status_code=422, detail="Choose a school and department")

            department = await db.scalar(
                text("""
                    SELECT d.id
                    FROM departments AS d
                    JOIN schools AS s ON s.id = d.school_id
                    WHERE d.id = :department_id
                      AND s.id = :school_id
                      AND s.institution_id = :institution_id
                      AND s.is_active = 1
                      AND d.is_active = 1
                    LIMIT 1
                """),
                {
                    "department_id": payload.department_id,
                    "school_id": payload.school_id,
                    "institution_id": resolved_institution_id,
                },
            )
            if department is None:
                raise HTTPException(status_code=422, detail="Choose an active school and department from your verified institution.")

            valid_programme_id = None
            if payload.programme_id:
                valid_programme_id = await db.scalar(
                    text("""
                        SELECT p.id
                        FROM programmes AS p
                        JOIN departments AS d ON d.id = p.department_id
                        JOIN schools AS s ON s.id = d.school_id
                        WHERE p.id = :programme_id
                          AND p.department_id = :department_id
                          AND LOWER(p.status) = 'active'
                          AND s.id = :school_id
                          AND s.institution_id = :institution_id
                          AND s.is_active = 1
                          AND d.is_active = 1
                        LIMIT 1
                    """),
                    {
                        "programme_id": payload.programme_id,
                        "department_id": payload.department_id,
                        "school_id": payload.school_id,
                        "institution_id": resolved_institution_id,
                    },
                )
                if valid_programme_id is None:
                    raise HTTPException(status_code=422, detail="Choose an active programme within your selected department.")

            cohort_id = None
            if payload.cohort_id:
                cohort = await db.execute(
                    text("""
                        SELECT c.id, c.programme_id
                        FROM cohorts AS c
                        JOIN programmes AS p ON p.id = c.programme_id
                        JOIN departments AS d ON d.id = p.department_id
                        JOIN schools AS s ON s.id = d.school_id
                        WHERE c.id = :cohort_id
                          AND c.is_active = 1
                          AND d.id = :department_id
                          AND (:programme_id IS NULL OR p.id = :programme_id)
                          AND s.id = :school_id
                          AND s.institution_id = :institution_id
                          AND s.is_active = 1
                          AND d.is_active = 1
                          AND LOWER(p.status) = 'active'
                        LIMIT 1
                    """),
                    {
                        "cohort_id": payload.cohort_id,
                        "department_id": payload.department_id,
                        "programme_id": valid_programme_id,
                        "school_id": payload.school_id,
                        "institution_id": resolved_institution_id,
                    },
                )
                cohort = cohort.mappings().first()
                if cohort is None:
                    raise HTTPException(status_code=422, detail="The selected cohort must be active and belong to the selected department and institution.")
                cohort_id = cohort["id"]
                if valid_programme_id is None:
                    valid_programme_id = cohort["programme_id"]

            if await _student_registration_identity_exists(db, payload):
                raise HTTPException(
                    status_code=409,
                    detail="Registration conflicts with an existing account or enrollment number",
                )

            account_result = await db.execute(
                text("""
                    INSERT INTO accounts (
                        email, password_hash, display_name, account_status, full_name,
                        is_active, is_verified
                    ) VALUES (
                        :email, :password_hash, :display_name, 'pending', :full_name,
                        1, 0
                    )
                """),
                {
                    "email": payload.email,
                    "password_hash": hash_password(payload.password),
                    "display_name": payload.full_name,
                    "full_name": payload.full_name,
                },
            )
            account_id = account_result.lastrowid
            if not account_id:
                raise RuntimeError("The database did not return the new account ID")

            await db.execute(
                text("""
                    INSERT INTO students (account_id, student_number, legal_name)
                    VALUES (:account_id, :student_number, :legal_name)
                """),
                {
                    "account_id": account_id,
                    "student_number": payload.enrollment_number,
                    "legal_name": payload.full_name,
                },
            )

            if cohort_id is not None:
                academic_year_id = await db.scalar(
                    text("""
                        SELECT id
                        FROM academic_years
                        WHERE institution_id = :institution_id
                          AND starts_on <= CURRENT_DATE()
                          AND ends_on >= CURRENT_DATE()
                        ORDER BY starts_on DESC
                        LIMIT 1
                    """),
                    {"institution_id": resolved_institution_id},
                )
                if academic_year_id is None:
                    raise HTTPException(
                        status_code=422,
                        detail="No current academic year is configured for this institution, so the student cannot be enrolled in the selected cohort yet.",
                    )
                await db.execute(
                    text("""
                        INSERT INTO student_enrollments (
                            student_id, cohort_id, academic_year_id, starts_on, enrollment_status
                        )
                        SELECT s.id, :cohort_id, :academic_year_id, CURRENT_DATE(), 'active'
                        FROM students AS s
                        WHERE s.account_id = :account_id
                    """),
                    {
                        "cohort_id": cohort_id,
                        "academic_year_id": academic_year_id,
                        "account_id": account_id,
                    },
                )

            # Keep the student-facing profile synchronized with the canonical student
            # identity and enrollment selected during registration.
            await db.execute(
                text("""
                    INSERT INTO student_profiles (
                        student_id, account_id, enrollment_number,
                        department_id, programme_id, cohort_id
                    )
                    SELECT s.id, s.account_id, s.student_number,
                           :department_id, :programme_id, :cohort_id
                    FROM students AS s
                    WHERE s.account_id = :account_id
                    ON DUPLICATE KEY UPDATE
                        account_id = VALUES(account_id),
                        enrollment_number = VALUES(enrollment_number),
                        department_id = VALUES(department_id),
                        programme_id = VALUES(programme_id),
                        cohort_id = VALUES(cohort_id)
                """),
                {
                    "department_id": payload.department_id,
                    "programme_id": valid_programme_id,
                    "cohort_id": cohort_id,
                    "account_id": account_id,
                },
            )

            role_id = await db.scalar(
                text("SELECT id FROM roles WHERE code = 'STUDENT' OR name = 'STUDENT' LIMIT 1")
            )
            if role_id is None:
                role_result = await db.execute(
                    text("INSERT INTO roles (code, name) VALUES ('STUDENT', 'STUDENT')")
                )
                role_id = role_result.lastrowid
            await db.execute(
                text("""
                    INSERT INTO account_roles (account_id, role_id, institution_id)
                    VALUES (:account_id, :role_id, :institution_id)
                """),
                {
                    "account_id": account_id,
                    "role_id": role_id,
                    "institution_id": resolved_institution_id,
                },
            )

            token = create_token(str(account_id), "email_verification", timedelta(minutes=30))
            await db.execute(
                text("UPDATE accounts SET verification_token = :token_hash WHERE id = :account_id"),
                {"token_hash": hash_token(token), "account_id": account_id},
            )
    except HTTPException:
        raise
    except IntegrityError:
        if await _student_registration_identity_exists(db, payload):
            raise HTTPException(
                status_code=409,
                detail="Registration conflicts with an existing account or enrollment number",
            ) from None
        raise

    try:
        await send_verification_email(payload.email, token)
        sent = True
    except Exception:
        # Do not expose provider internals or secrets to the registration caller.
        sent = False
    return RegistrationResponse(
        account_id=str(account_id),
        message=(
            "Account created. Check your email to verify it."
            if sent
            else "Account created but verification email could not be sent. Request a new link after email delivery is configured."
        ),
        verification_email_sent=sent,
    )


@router.post("/register/faculty", response_model=RegistrationResponse, status_code=201)
async def register_faculty(payload: FacultyRegistration, db: DbSession) -> RegistrationResponse:
    """Register faculty using the deployed MySQL identity schema.

    The live schema uses accounts.id BIGINT UNSIGNED AUTO_INCREMENT and the
    canonical faculty table (not faculty_profiles). Keep this flow on SQL
    statements so UUID-based legacy ORM mappings cannot create incompatible rows.
    """
    if len(payload.full_name) > 200:
        raise HTTPException(status_code=422, detail="Full name must be 200 characters or fewer")
    if len(payload.employee_code) > 80:
        raise HTTPException(status_code=422, detail="Employee code must be 80 characters or fewer")
    if len(payload.designation) > 150:
        raise HTTPException(status_code=422, detail="Designation must be 150 characters or fewer")
    if db.get_bind().dialect.name == "sqlite":
        return await _register_faculty_sqlite(payload, db)

    token: str
    account_id: int
    try:
        async with db.begin():
            department = await db.execute(
                text("""
                    SELECT d.id, s.institution_id
                    FROM departments AS d
                    JOIN schools AS s ON s.id = d.school_id
                    WHERE d.id = :department_id
                      AND s.id = :school_id
                      AND d.is_active = 1
                      AND s.is_active = 1
                    LIMIT 1
                """),
                {"department_id": payload.department_id, "school_id": payload.school_id},
            )
            department_row = department.mappings().first()
            if department_row is None:
                raise HTTPException(
                    status_code=422,
                    detail="Choose an active department within the selected school",
                )

            institution_id = department_row["institution_id"]
            if institution_id is None:
                raise HTTPException(status_code=422, detail="The selected school is not linked to an institution")
            if payload.institution_id and str(payload.institution_id) != str(institution_id):
                raise HTTPException(
                    status_code=422,
                    detail="The selected school and department do not belong to the selected institution",
                )
            active_institution = await db.scalar(
                text("SELECT id FROM institutions WHERE id = :institution_id AND UPPER(status) = 'ACTIVE' LIMIT 1"),
                {"institution_id": institution_id},
            )
            if active_institution is None:
                raise HTTPException(status_code=422, detail="The selected institution is inactive")

            if await _faculty_registration_identity_exists(db, payload):
                raise HTTPException(
                    status_code=409,
                    detail="Registration conflicts with an existing account or employee code",
                )

            account_result = await db.execute(
                text("""
                    INSERT INTO accounts (
                        email, password_hash, display_name, account_status, full_name,
                        is_active, is_verified
                    ) VALUES (
                        :email, :password_hash, :display_name, 'pending', :full_name,
                        0, 0
                    )
                """),
                {
                    "email": payload.email,
                    "password_hash": hash_password(payload.password),
                    "display_name": payload.full_name,
                    "full_name": payload.full_name,
                },
            )
            account_id = account_result.lastrowid
            if not account_id:
                raise RuntimeError("The database did not return the new account ID")

            await db.execute(
                text("""
                    INSERT INTO faculty (
                        account_id, employee_number, employee_code, display_name,
                        employment_status, department_id, designation
                    ) VALUES (
                        :account_id, :employee_number, :employee_code, :display_name,
                        'active', :department_id, :designation
                    )
                """),
                {
                    "account_id": account_id,
                    "employee_number": payload.employee_code,
                    "employee_code": payload.employee_code,
                    "display_name": payload.full_name,
                    "department_id": department_row["id"],
                    "designation": payload.designation,
                },
            )

            role_id = await db.scalar(
                text("SELECT id FROM roles WHERE code = 'FACULTY' OR name = 'FACULTY' LIMIT 1")
            )
            if role_id is None:
                role_result = await db.execute(
                    text("INSERT INTO roles (code, name) VALUES ('FACULTY', 'FACULTY')")
                )
                role_id = role_result.lastrowid
            await db.execute(
                text("""
                    INSERT INTO account_roles (account_id, role_id, institution_id)
                    VALUES (:account_id, :role_id, :institution_id)
                """),
                {
                    "account_id": account_id,
                    "role_id": role_id,
                    "institution_id": institution_id,
                },
            )

            token = create_token(str(account_id), "email_verification", timedelta(minutes=30))
            await db.execute(
                text("UPDATE accounts SET verification_token = :token_hash WHERE id = :account_id"),
                {"token_hash": hash_token(token), "account_id": account_id},
            )
    except HTTPException:
        raise
    except IntegrityError:
        if await _faculty_registration_identity_exists(db, payload):
            raise HTTPException(
                status_code=409,
                detail="Registration conflicts with an existing account or employee code",
            ) from None
        raise

    try:
        await send_verification_email(payload.email, token)
        sent = True
    except Exception:
        sent = False
    return RegistrationResponse(
        account_id=str(account_id),
        message=(
            "Faculty account created. Verify the email; institutional approval is still required."
            if sent
            else "Faculty account created pending email verification and institutional approval. Verification email delivery is not available."
        ),
        verification_email_sent=sent,
        activation_pending=True,
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest, db: DbSession) -> MessageResponse:
    try:
        claims = decode_token(payload.token, "email_verification")
    except TokenError:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link") from None

    account = await IdentityService(db).get_account(claims["sub"])
    if (
        account is None
        or account.is_verified
        or not account.verification_token
        or not hmac.compare_digest(account.verification_token, hash_token(payload.token))
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    account.is_verified = True
    account.verification_token = None
    await db.commit()
    return MessageResponse(
        message=(
            "Email verified. You can now log in."
            if account.is_active
            else "Email verified. Your faculty account remains pending institutional approval."
        )
    )


@router.post("/verification/resend", response_model=MessageResponse)
async def resend_verification(payload: ResendVerificationRequest, db: DbSession) -> MessageResponse:
    # The response is deliberately the same for unknown, verified, and pending accounts.
    account = await IdentityService(db).get_account_by_email(payload.email)
    if account is not None and not account.is_verified:
        token = create_token(account.id, "email_verification", timedelta(minutes=30))
        account.verification_token = hash_token(token)
        await db.commit()
        await _send_verification(account, token)
    return MessageResponse(
        message="If the account requires verification, a link will be sent when email delivery is available."
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    account = await IdentityService(db).get_account_by_email(payload.email)
    # Same response for missing account, wrong password, pending, or disabled account.
    if (
        account is None
        or not verify_password(payload.password, account.password_hash)
        or not account.is_active
        or not account.is_verified
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    account.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    token = create_token(
        str(account.id), "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), token_version=account.token_version
    )
    return AuthResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        account=await _account_public(db, account),
    )


@router.get("/me", response_model=AccountPublic)
async def current_user(account: CurrentAccount, db: DbSession) -> AccountPublic:
    return await _account_public(db, account)




async def _send_password_reset(account: Account, token: str) -> bool:
    try:
        message_id = await send_password_reset_email(account.email, token)
        logger.warning("PASSWORD_RESET_DIAGNOSTIC outcome=provider_accepted provider_message_id=%s", message_id)
        return True
    except Exception as exc:
        # Keep the public response generic to prevent account enumeration, but make
        # delivery failures diagnosable in backend logs without exposing PII/tokens.
        logger.error(
            "PASSWORD_RESET_DIAGNOSTIC outcome=delivery_failed error_type=%s error=%s",
            type(exc).__name__,
            str(exc)[:300],
        )
        return False


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(payload: PasswordResetRequest, db: DbSession) -> MessageResponse:
    # Same response for unknown, disabled, unverified, and eligible accounts.
    logger.warning("PASSWORD_RESET_DIAGNOSTIC outcome=request_received")
    account = await IdentityService(db).get_account_by_email(payload.email)
    now = datetime.now(UTC).replace(tzinfo=None)
    if account is None:
        logger.warning("PASSWORD_RESET_DIAGNOSTIC outcome=account_not_found")
    elif not account.is_active or not account.is_verified:
        logger.warning(
            "PASSWORD_RESET_DIAGNOSTIC outcome=account_ineligible active=%s verified=%s",
            account.is_active,
            account.is_verified,
        )
    else:
        # An unexpired token acts as an account-level cooldown to reduce email flooding.
        can_issue = account.reset_token_expires_at is None or account.reset_token_expires_at <= now
        if can_issue:
            token = create_token(account.id, "password_reset", timedelta(minutes=30))
            account.reset_token = hash_token(token)
            account.reset_token_expires_at = now + timedelta(minutes=30)
            await db.commit()
            if not await _send_password_reset(account, token):
                account.reset_token = None
                account.reset_token_expires_at = None
                await db.commit()
        else:
            logger.warning("PASSWORD_RESET_DIAGNOSTIC outcome=throttled_existing_token")
    return MessageResponse(
        message="If an eligible account exists, password reset instructions will be sent when email delivery is available."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(payload: PasswordResetConfirm, db: DbSession) -> MessageResponse:
    try:
        claims = decode_token(payload.token, "password_reset")
    except TokenError:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token") from None
    account = await IdentityService(db).get_account(claims["sub"])
    now = datetime.now(UTC).replace(tzinfo=None)
    if (
        account is None
        or not account.is_active
        or not account.is_verified
        or not account.reset_token
        or account.reset_token_expires_at is None
        or account.reset_token_expires_at <= now
        or not hmac.compare_digest(account.reset_token, hash_token(payload.token))
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
    account.password_hash = hash_password(payload.new_password)
    account.reset_token = None
    account.reset_token_expires_at = None
    account.token_version += 1
    await db.commit()
    return MessageResponse(message="Password reset successful. Please log in with your new password.")


@router.post("/logout", response_model=MessageResponse)
async def logout(account: CurrentAccount, db: DbSession) -> MessageResponse:
    # The current JWT design uses an account token-version counter to revoke all issued access tokens.
    account.token_version += 1
    await db.commit()
    return MessageResponse(message="Logged out. Existing access tokens for this account have been revoked.")

