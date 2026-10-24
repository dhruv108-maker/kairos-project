"""Make student cohort assignment optional and seed GSFC University's hierarchy."""
from uuid import uuid5, NAMESPACE_URL
from alembic import op
import sqlalchemy as sa
revision = "20261024_22"
down_revision = "20261024_21"
branch_labels = None
depends_on = None
GSFC_INSTITUTION_ID = "11"
SCHOOLS = (("GSFC-SOT", "School of Technology"), ("GSFC-SOS", "School of Science"), ("GSFC-SOM", "School of Management"))
DEPARTMENTS = (
 ("GSFC-CSE","Computer Science and Engineering","GSFC-SOT"),
 ("GSFC-MECH","Mechanical Engineering","GSFC-SOT"),
 ("GSFC-CHE","Chemical Engineering","GSFC-SOT"),
 ("GSFC-FEHS","Fire & Environment, Health & Safety Engineering","GSFC-SOT"),
 ("GSFC-CHEM","Chemistry","GSFC-SOS"),
 ("GSFC-BIOTECH","Biotechnology","GSFC-SOS"),
 ("GSFC-MICRO","Microbiology","GSFC-SOS"),
 ("GSFC-INDCHEM","Industrial Chemistry","GSFC-SOS"),
 ("GSFC-BBA","Business Administration","GSFC-SOM"),
)
def _stable_id(kind, code):
    return str(uuid5(NAMESPACE_URL, f"kairos:gsfc:{kind}:{code}"))
def _insert_if_missing(bind, name, code, values):
    if not sa.inspect(bind).has_table(name): return None
    table=sa.Table(name,sa.MetaData(),autoload_with=bind)
    if "code" not in table.c: return None
    existing=bind.execute(sa.select(table).where(table.c.code==code)).mappings().first()
    if existing is not None: return existing.get("id")
    payload={k:v for k,v in values.items() if k in table.c}
    if "id" in table.c and table.c.id.primary_key:
        if isinstance(table.c.id.type,(sa.String,sa.Unicode,sa.CHAR,sa.Text)) or not table.c.id.autoincrement:
            payload["id"]=_stable_id(name,code)
    result=bind.execute(table.insert().values(**payload))
    return (payload.get("id") or result.inserted_primary_key[0]) if "id" in table.c else None
def upgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    if inspector.has_table("student_profiles"):
        cols={c["name"]:c for c in inspector.get_columns("student_profiles")}
        if "cohort_id" in cols and not cols["cohort_id"]["nullable"]:
            with op.batch_alter_table("student_profiles") as b:
                b.alter_column("cohort_id",existing_type=cols["cohort_id"]["type"],nullable=True)
        if "department_id" not in cols and inspector.has_table("departments"):
            dc={c["name"]:c for c in inspector.get_columns("departments")}
            op.add_column("student_profiles",sa.Column("department_id",dc["id"]["type"],nullable=True))
            with op.batch_alter_table("student_profiles") as b:
                b.create_foreign_key("fk_student_profiles_department_id","departments",["department_id"],["id"],ondelete="RESTRICT")
        cols={c["name"] for c in sa.inspect(bind).get_columns("student_profiles")}
        if {"department_id","cohort_id"}<=cols and all(sa.inspect(bind).has_table(t) for t in ("cohorts","programmes","departments")):
            bind.execute(sa.text("""
                UPDATE student_profiles SET department_id = (
                  SELECT programmes.department_id FROM cohorts
                  JOIN programmes ON programmes.id=cohorts.programme_id
                  WHERE cohorts.id=student_profiles.cohort_id
                ) WHERE department_id IS NULL AND cohort_id IS NOT NULL
            """))
    inspector=sa.inspect(bind)
    if not all(inspector.has_table(t) for t in ("institutions","schools","departments")): return
    if bind.execute(sa.text("SELECT id FROM institutions WHERE id=:id"),{"id":GSFC_INSTITUTION_ID}).first() is None: return
    school_ids={}
    for code,name in SCHOOLS:
        _insert_if_missing(bind,"schools",code,{"institution_id":GSFC_INSTITUTION_ID,"code":code,"name":name,"status":"active","is_active":True})
        table=sa.Table("schools",sa.MetaData(),autoload_with=bind)
        school_ids[code]=bind.execute(sa.select(table.c.id).where(table.c.code==code)).scalar_one()
    for code,name,school_code in DEPARTMENTS:
        _insert_if_missing(bind,"departments",code,{"school_id":school_ids[school_code],"code":code,"name":name,"status":"active","is_active":True})
def downgrade():
    # Preserve seeded hierarchy and student affiliations; deleting them could break live accounts.
    return
