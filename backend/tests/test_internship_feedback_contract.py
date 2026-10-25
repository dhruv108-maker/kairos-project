from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.api.internship_feedback import WeeklyFeedbackInput, DailyLogFeedbackInput

def test_weekly_feedback_accepts_rating_boundaries():
    value = WeeklyFeedbackInput(overall_rating=Decimal("0"), attendance_rating=1, technical_rating=5, communication_rating=3)
    assert value.overall_rating == Decimal("0")
    assert value.attendance_rating == 1

@pytest.mark.parametrize("payload", [
    {"overall_rating": -0.1}, {"overall_rating": 5.1},
    {"attendance_rating": 0}, {"technical_rating": 6}, {"communication_rating": 0},
])
def test_weekly_feedback_rejects_invalid_ratings(payload):
    with pytest.raises(ValidationError):
        WeeklyFeedbackInput(**payload)

def test_optional_text_is_trimmed_and_blank_becomes_null():
    value = WeeklyFeedbackInput(strengths="  shipped feature  ", feedback_text="  ")
    assert value.strengths == "shipped feature"
    assert value.feedback_text is None

def test_daily_log_feedback_requires_nonblank_text():
    with pytest.raises(ValidationError):
        DailyLogFeedbackInput(decision="acknowledged", feedback_text="   ")
