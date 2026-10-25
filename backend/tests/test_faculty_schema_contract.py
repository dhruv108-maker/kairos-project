from sqlalchemy.dialects.mysql import BIGINT

from app.models.academic import FacultyProfile


def test_faculty_model_matches_deployed_table_and_key_types():
    table = FacultyProfile.__table__

    assert table.name == "faculty"
    assert isinstance(table.c.id.type, BIGINT)
    assert table.c.id.type.unsigned is True
    assert table.c.id.autoincrement is True
    assert isinstance(table.c.account_id.type, BIGINT)
    assert table.c.account_id.type.unsigned is True
    assert table.c.display_name.type.length == 200
    assert table.c.employee_number.type.length == 80
    assert table.c.designation.type.length == 150
    assert "updated_at" not in table.c
