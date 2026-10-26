"""Optional account identity-verification API."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.identity_verification.provider import IdentityProviderUnavailable
from app.modules.identity_verification.service import IdentityVerificationService

router = APIRouter(prefix="/identity-verification", tags=["identity verification"])


class SaveIdentityDetailsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    declared_name: str | None = Field(default=None, max_length=200)
    consent: bool
    consent_notice_version: str = Field(min_length=1, max_length=40)

    @field_validator("consent_notice_version")
    @classmethod
    def normalize_notice_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Consent notice version cannot be blank")
        return normalized

    @field_validator("declared_name")
    @classmethod
    def normalize_declared_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized and any(ord(char) < 32 for char in normalized):
            raise ValueError("Declared name contains invalid control characters")
        return normalized or None


class SaveIdentityDetailsResponse(BaseModel):
    declared_name: str | None = None
    consented_at: datetime
    updated_at: datetime | None = None


class InitiateVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aadhaar_number: SecretStr = Field(repr=False)
    consent: bool
    consent_notice_version: str = Field(min_length=1, max_length=40)

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar_number(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw) != 12 or not raw.isascii() or not raw.isdigit():
            raise ValueError("Enter a valid 12-digit Aadhaar number.")
        return value

    @field_validator("consent_notice_version")
    @classmethod
    def normalize_notice_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Consent notice version cannot be blank")
        return normalized


class VerificationStatusResponse(BaseModel):
    id: str | None = None
    status: Literal[
        "not_started", "pending", "verified", "failed", "expired", "cancelled", "review_required"
    ]
    # Backward-compatible alias for identity_verified; never email verification.
    verified: bool
    email_verified: bool
    identity_verified: bool
    identity_verification_status: Literal["not_started", "pending", "verified", "failed", "expired", "cancelled", "review_required"]
    available: bool
    provider: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None
    completed_at: datetime | None = None
    error_category: str | None = None
    message: str | None = None
    declared_name: str | None = None


class InitiateVerificationResponse(BaseModel):
    id: str
    status: Literal["verified", "failed"]
    verified: bool
    identity_verified: bool
    email_verified: bool
    provider: str
    message: str | None = None
    completed_at: datetime | None = None


@router.get("/status", response_model=VerificationStatusResponse)
async def verification_status(account: CurrentAccount, db: DbSession):
    # Account identity comes only from the authenticated bearer token.
    return await IdentityVerificationService(db).status(account.id)


@router.put("/details", response_model=SaveIdentityDetailsResponse)
async def save_identity_details(
    payload: SaveIdentityDetailsRequest, account: CurrentAccount, db: DbSession
):
    try:
        return await IdentityVerificationService(db).save_details(
            account_id=account.id,
            declared_name=payload.declared_name,
            consent=payload.consent,
            notice_version=payload.consent_notice_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post(
    "/initiate",
    response_model=InitiateVerificationResponse,
)
async def initiate_verification(
    payload: InitiateVerificationRequest, account: CurrentAccount, db: DbSession
):
    service = IdentityVerificationService(db)
    try:
        return await service.initiate(
            account_id=account.id,
            consent=payload.consent,
            notice_version=payload.consent_notice_version,
            aadhaar_number=payload.aadhaar_number.get_secret_value(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except IdentityProviderUnavailable:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "identity_verification_unavailable",
                "message": "Aadhaar identity verification is not currently supported by the configured provider.",
            },
            headers={"Retry-After": "3600"},
        ) from None
