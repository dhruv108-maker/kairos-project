from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
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

router = APIRouter(prefix="/auth", tags=["authentication"])


async def _account_public(db, account: Account) -> AccountPublic:
    return AccountPublic(
        id=account.id,
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
    try:
        async with db.begin():
            email_domain = payload.email.rsplit("@", 1)[1].strip().lower().rstrip(".")
            resolved_institution_id = await db.scalar(
                select(InstitutionDomain.institution_id)
                .join(Institution, Institution.id == InstitutionDomain.institution_id)
                .where(
                    InstitutionDomain.normalized_domain == email_domain,
                    InstitutionDomain.is_verified.is_(True),
                    Institution.status == "ACTIVE",
                )
            )
            if resolved_institution_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="Your email domain is not verified for an active institution. Contact your institution administrator.",
                )
            if payload.institution_id and payload.institution_id != resolved_institution_id:
                raise HTTPException(status_code=422, detail="The institution does not match your verified email domain")

            cohort = await db.scalar(
                select(Cohort)
                .join(Programme, Programme.id == Cohort.programme_id)
                .join(Department, Department.id == Programme.department_id)
                .join(School, School.id == Department.school_id)
                .join(AcademicYear, AcademicYear.id == Cohort.academic_year_id)
                .where(
                    Cohort.id == payload.cohort_id,
                    School.institution_id == resolved_institution_id,
                    School.is_active.is_(True),
                    Department.is_active.is_(True),
                    Programme.is_active.is_(True),
                    AcademicYear.is_current.is_(True),
                    AcademicYear.institution_id == resolved_institution_id,
                )
            )
            if cohort is None:
                raise HTTPException(
                    status_code=422,
                    detail="Choose an available cohort from your institution. The cohort may be inactive or belong to another institution.",
                )
            account = Account(
                id=str(uuid4()),
                email=payload.email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
                is_active=True,
                is_verified=False,
            )
            profile = StudentProfile(
                id=str(uuid4()),
                account_id=account.id,
                enrollment_number=payload.enrollment_number,
                cohort_id=payload.cohort_id,
            )
            role = await _ensure_role(db, "STUDENT")
            db.add_all([account, profile])
            await db.flush()
            db.add(AccountRole(account_id=account.id, role_id=role.id))
            token = await _new_verification_token(account)
            await db.flush()
    except HTTPException:
        raise
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Registration conflicts with an existing account or enrollment number",
        ) from None

    sent = await _send_verification(account, token)
    return RegistrationResponse(
        account_id=account.id,
        message=(
            "Account created. Check your email to verify it."
            if sent
            else "Account created but verification email could not be sent. Request a new link after email delivery is configured."
        ),
        verification_email_sent=sent,
    )


@router.post("/register/faculty", response_model=RegistrationResponse, status_code=201)
async def register_faculty(payload: FacultyRegistration, db: DbSession) -> RegistrationResponse:
    try:
        async with db.begin():
            department = await db.get(Department, payload.department_id)
            if department is None or not department.is_active:
                raise HTTPException(status_code=422, detail="Unknown or inactive department_id")
            if payload.institution_id:
                institution = await db.get(Institution, payload.institution_id)
                department_institution_id = await db.scalar(
                    select(School.institution_id)
                    .join(Department, Department.school_id == School.id)
                    .where(Department.id == payload.department_id)
                )
                if institution is None or institution.status != "ACTIVE":
                    raise HTTPException(status_code=422, detail="Unknown or inactive institution_id")
                if department_institution_id != institution.id:
                    raise HTTPException(status_code=422, detail="The selected department does not belong to the selected institution")
            account = Account(
                id=str(uuid4()),
                email=payload.email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
                is_active=False,
                is_verified=False,
            )
            profile = FacultyProfile(
                id=str(uuid4()),
                account_id=account.id,
                employee_code=payload.employee_code,
                department_id=payload.department_id,
                designation=payload.designation,
            )
            role = await _ensure_role(db, "FACULTY")
            db.add_all([account, profile])
            await db.flush()
            db.add(AccountRole(account_id=account.id, role_id=role.id))
            token = await _new_verification_token(account)
            await db.flush()
    except HTTPException:
        raise
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Registration conflicts with an existing account or employee code",
        ) from None

    sent = await _send_verification(account, token)
    return RegistrationResponse(
        account_id=account.id,
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
        account.id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), token_version=account.token_version
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
        await send_password_reset_email(account.email, token)
        return True
    except Exception:
        return False


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(payload: PasswordResetRequest, db: DbSession) -> MessageResponse:
    # Same response for unknown, disabled, unverified, and eligible accounts.
    account = await IdentityService(db).get_account_by_email(payload.email)
    now = datetime.now(UTC).replace(tzinfo=None)
    if account is not None and account.is_active and account.is_verified:
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

