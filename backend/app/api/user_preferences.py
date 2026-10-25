from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.api.dependencies import CurrentAccount, DbSession
from app.models.user_preferences import UserPreferences

router = APIRouter(prefix="/users/me/preferences", tags=["user preferences"])

Accent = Literal["teal", "blue", "green", "amber", "rose", "neutral"]
FontSize = Literal["small", "default", "large", "xlarge"]
Density = Literal["compact", "comfortable", "spacious"]
ThemeMode = Literal["light", "dark", "system"]


class UserPreferencesPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accent_color: Accent | None = None
    font_size: FontSize | None = None
    interface_density: Density | None = None
    theme_mode: ThemeMode | None = None
    email_notifications_enabled: bool | None = None
    notification_preferences: dict[str, bool] | None = Field(default=None, max_length=32)

    @field_validator("notification_preferences")
    @classmethod
    def supported_notification_keys(cls, value: dict[str, bool] | None) -> dict[str, bool] | None:
        if value is None:
            return value
        allowed = {"internship_updates", "work_log_reviews", "report_updates", "recruitment_updates", "account_security"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError("Unsupported notification preference key")
        return value


class UserPreferencesResponse(BaseModel):
    account_id: str
    accent_color: Accent
    font_size: FontSize
    interface_density: Density
    theme_mode: ThemeMode
    email_notifications_enabled: bool
    notification_preferences: dict[str, bool]
    updated_at: datetime | None = None


def _serialize(record: UserPreferences) -> UserPreferencesResponse:
    return UserPreferencesResponse(
        account_id=record.account_id,
        accent_color=record.accent_color,
        font_size=record.font_size,
        interface_density=record.interface_density,
        theme_mode=record.theme_mode,
        email_notifications_enabled=record.email_notifications_enabled,
        notification_preferences=record.notification_preferences or {},
        updated_at=record.updated_at,
    )


async def _get_or_create(db, account_id: str) -> UserPreferences:
    record = await db.get(UserPreferences, account_id)
    if record is not None:
        return record
    # Race-safe creation via the current MySQL-compatible account-preferences key.
    statement = mysql_insert(UserPreferences).values(account_id=account_id, notification_preferences={}).on_duplicate_key_update(account_id=account_id)
    await db.execute(statement)
    await db.commit()
    record = await db.get(UserPreferences, account_id)
    if record is None:
        raise RuntimeError("Unable to initialize preferences")
    return record


@router.get("", response_model=UserPreferencesResponse)
async def get_my_preferences(account: CurrentAccount, db: DbSession) -> UserPreferencesResponse:
    record = await _get_or_create(db, str(account.id))
    return _serialize(record)


@router.patch("", response_model=UserPreferencesResponse)
async def patch_my_preferences(
    payload: UserPreferencesPatch,
    account: CurrentAccount,
    db: DbSession,
) -> UserPreferencesResponse:
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    record = await _get_or_create(db, str(account.id))

    if "notification_preferences" in changes:
        record.notification_preferences = {**(record.notification_preferences or {}), **changes["notification_preferences"]}

    for key, value in changes.items():
        if key != "notification_preferences":
            setattr(record, key, value)

    await db.commit()
    await db.refresh(record)
    return _serialize(record)
