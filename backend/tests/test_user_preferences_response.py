from datetime import datetime

from app.api.user_preferences import _serialize
from app.models.user_preferences import UserPreferences


def test_preferences_response_serializes_integer_account_ids():
    record = UserPreferences(
        account_id=73001,
        accent_color="teal",
        font_size="default",
        interface_density="comfortable",
        theme_mode="system",
        email_notifications_enabled=True,
        notification_preferences={},
        updated_at=datetime(2026, 10, 25),
    )

    response = _serialize(record)

    assert response.account_id == "73001"
    assert isinstance(response.account_id, str)
