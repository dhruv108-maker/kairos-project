from __future__ import annotations

import hmac
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, text
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


@router.post("/register/student", response_model=RegistrationResponse, status_code=201)
async def register_student(payload: StudentRegistration, db: DbSession) -> RegistrationResponse:
    """Register a student against the deployed MySQL schema.

    The production schema uses BIGINT AUTO_INCREMENT IDs and the tables
    accounts, students, student_enrollments, account_roles, and roles. It does
    not contain student_profiles or roles.description.
    """
    if len(payload.full_name) > 200:
        raise HTTPException(status_code=422, detail="Full name must be 200 characters or fewer")

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
            if payload.institution_id and int(payload.institution_id) != int(resolved_institution_id):
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
                          AND LOWER(c.status) = 'active'
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
        raise HTTPException(
            status_code=409,
            detail="Registration conflicts with an existing account or enrollment number",
        ) from None

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
        raise HTTPException(
            status_code=409,
            detail="Registration conflicts with an existing account or employee code",
        ) from None

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

