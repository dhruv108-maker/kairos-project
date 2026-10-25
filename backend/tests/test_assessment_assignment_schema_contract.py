from sqlalchemy.dialects.mysql import BIGINT

from app.models.organizations import AssessmentCampaign, FacultyAssessmentAssignment


def test_assessment_assignment_model_matches_deployed_table():
    table = FacultyAssessmentAssignment.__table__

    assert table.name == "assessment_assignments"
    assert isinstance(table.c.id.type, BIGINT)
    assert table.c.id.type.unsigned is True
    assert table.c.id.autoincrement is True
    assert isinstance(table.c.campaign_id.type, BIGINT)
    assert table.c.campaign_id.type.unsigned is True
    assert isinstance(table.c.faculty_id.type, BIGINT)
    assert table.c.faculty_id.type.unsigned is True
    assert set(table.c.keys()) == {
        "id", "campaign_id", "faculty_id", "assigned_at", "assignment_status", "selection_key"
    }
    assert table.c.assignment_status.default is None
    assert table.c.assignment_status.server_default.arg.text.strip("'") == "assigned"
    assert table.c.selection_key.type.length == 200
    assert any(constraint.name == "uq_campaign_faculty" for constraint in table.constraints)
    foreign_keys = {fk.target_fullname for fk in table.foreign_keys}
    assert foreign_keys == {"assessment_campaigns.id", "faculty.id"}


def test_assessment_campaign_uses_unsigned_auto_increment_key():
    column = AssessmentCampaign.__table__.c.id
    assert isinstance(column.type, BIGINT)
    assert column.type.unsigned is True
    assert column.autoincrement is True
