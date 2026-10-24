"""Optional account identity-verification API."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.identity_verification.provider import IdentityProviderUnavailable
from app.modules.identity_verification.service import IdentityVerificationService

router = APIRouter(prefix="/identity-verification", tags=["identity verification"])


class InitiateVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent: bool
    consent_notice_version: str = Field(min_length=1, max_length=40)

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
    verified: bool
    available: bool
    provider: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None
    completed_at: datetime | None = None
    error_category: str | None = None
    message: str | None = None


class InitiateVerificationResponse(BaseModel):
    id: str
    status: Literal["pending"]
    redirect_url: str | None = None
    expires_at: datetime | None = None


@router.get("/status", response_model=VerificationStatusResponse)
async def verification_status(account: CurrentAccount, db: DbSession):
    # Account identity comes only from the authenticated bearer token.
    return await IdentityVerificationService(db).status(account.id)


@router.post(
    "/initiate",
    status_code=202,
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
