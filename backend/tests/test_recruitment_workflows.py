from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.modules.employers.schemas import InterviewCreate, OfferCreate, JobPatch
from app.main import app


def test_video_interview_requires_timezone_and_meeting_url():
    future = datetime.now(timezone.utc) + timedelta(days=2)
    with pytest.raises(ValidationError):
        InterviewCreate(scheduled_at=future.replace(tzinfo=None), interview_type="VIDEO", meeting_url="https://meet.example.test/room")
    with pytest.raises(ValidationError):
        InterviewCreate(scheduled_at=future, interview_type="VIDEO")
    item = InterviewCreate(scheduled_at=future, interview_type="VIDEO", meeting_url="https://meet.example.test/room")
    assert item.duration_minutes == 30
    assert item.interview_type == "VIDEO"


def test_onsite_interview_requires_location():
    future = datetime.now(timezone.utc) + timedelta(days=2)
    with pytest.raises(ValidationError):
        InterviewCreate(scheduled_at=future, interview_type="ONSITE")
    item = InterviewCreate(scheduled_at=future, interview_type="ONSITE", location="Kairos HQ, Ahmedabad")
    assert item.location == "Kairos HQ, Ahmedabad"


def test_offer_currency_and_expiry_validation():
    with pytest.raises(ValidationError):
        OfferCreate(compensation_amount=50000, compensation_currency="IN")
    with pytest.raises(ValidationError):
        OfferCreate(expires_at=datetime.now())
    item = OfferCreate(compensation_amount=50000, compensation_currency="inr")
    assert item.compensation_currency == "INR"


def test_job_patch_only_contains_fields_supplied_by_client():
    patch = JobPatch(title="Backend Engineer")
    assert patch.model_dump(exclude_unset=True) == {"title": "Backend Engineer"}


def test_interview_offer_and_student_response_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/employers/organizations/{organization_id}/applications/{application_id}/interviews" in paths
    assert "/api/v1/employers/organizations/{organization_id}/applications/{application_id}/offers" in paths
    assert "/api/v1/students/applications/{application_id}/offers/{offer_id}/respond" in paths
