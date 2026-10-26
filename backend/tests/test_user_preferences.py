import pytest
from pydantic import ValidationError
from sqlalchemy import String
from sqlalchemy.dialects import mysql, sqlite

from app.api.user_preferences import UserPreferencesPatch
from app.models import Base
from app.models.user_preferences import UserPreferences


def test_user_preferences_model_is_keyed_by_account_and_cascades():
    table = UserPreferences.__table__
    assert list(table.primary_key.columns.keys()) == ["account_id"]
    account_fk = next(iter(table.c.account_id.foreign_keys))
    assert account_fk.target_fullname == "accounts.id"
    assert account_fk.ondelete == "CASCADE"
    # The canonical model contract is MySQL BIGINT UNSIGNED; SQLite uses a
    # UUID-like string variant for isolated fixtures.
    assert isinstance(table.c.account_id.type.dialect_impl(mysql.dialect()), mysql.BIGINT)
    assert table.c.account_id.type.dialect_impl(mysql.dialect()).unsigned is True
    assert isinstance(table.c.account_id.type.dialect_impl(sqlite.dialect()), String)
    assert table.c.account_id.type.dialect_impl(sqlite.dialect()).length == 36
    assert table.c.accent_color.server_default is not None
    assert table.c.notification_preferences.nullable is False
    assert "user_preferences" in Base.metadata.tables


def test_patch_accepts_only_supported_appearance_values():
    patch = UserPreferencesPatch(
        accent_color="teal",
        font_size="large",
        interface_density="comfortable",
        theme_mode="system",
    )
    assert patch.model_dump(exclude_unset=True) == {
        "accent_color": "teal",
        "font_size": "large",
        "interface_density": "comfortable",
        "theme_mode": "system",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"accent_color": "purple"},
        {"font_size": "giant"},
        {"interface_density": "zoom"},
        {"theme_mode": "auto"},
        {"notification_preferences": {"made_up_category": True}},
        {"unexpected_admin_setting": True},
    ],
)
def test_patch_rejects_unknown_preference_values_or_fields(payload):
    with pytest.raises(ValidationError):
        UserPreferencesPatch.model_validate(payload)


def test_patch_supports_partial_category_updates_without_replacing_the_whole_map():
    patch = UserPreferencesPatch(notification_preferences={"report_updates": False})
    assert patch.notification_preferences == {"report_updates": False}


def test_master_email_preference_is_a_boolean():
    assert UserPreferencesPatch(email_notifications_enabled=False).email_notifications_enabled is False
    with pytest.raises(ValidationError):
        UserPreferencesPatch(email_notifications_enabled="not a boolean")
