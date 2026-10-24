"""Seed GSFCU's documented schools, departments, and programmes; persist student programme choice."""
from uuid import uuid5, NAMESPACE_URL
from alembic import op
import sqlalchemy as sa

revision = "20261024_23"
down_revision = "20261024_22"
branch_labels = None
depends_on = None
INSTITUTION_ID = "11"

SCHOOLS = [
    ("GSFC-SOS", "School of Science"),
    ("GSFC-SOT", "School of Technology"),
    ("GSFC-SOMLA", "School of Management & Liberal Arts"),
]
DEPARTMENTS = [
    ("GSFC-SOCIS", "School of Chemical & Industrial Sciences", "GSFC-SOS"),
    ("GSFC-SOLS", "School of Life Sciences", "GSFC-SOS"),
    ("GSFC-SOCIT", "School of Information & Communication Technology", "GSFC-SOT"),
    ("GSFC-SOCFS", "School of Chemical Engineering & Fire Safety", "GSFC-SOT"),
    ("GSFC-SOME", "School of Management & Entrepreneurship", "GSFC-SOMLA"),
]
# Names and levels follow the user-provided GSFCU_School_Wise_Programmes.md.
PROGRAMMES = [
 ("SOCIS-BSC-HONS-CHEM","B.Sc. (Hons.) Chemistry","Undergraduate","GSFC-SOCIS"),
 ("SOCIS-BSC-DS","B.Sc. Data Science","Undergraduate","GSFC-SOCIS"),
 ("SOCIS-IBSC-HMSC-DS","Integrated B.Sc. (Hons.)–M.Sc. Data Science","Integrated UG–PG","GSFC-SOCIS"),
 ("SOCIS-IBSC-MSC-CHEM","Integrated B.Sc.–M.Sc. Chemistry","Integrated UG–PG","GSFC-SOCIS"),
 ("SOCIS-MSC-CHEM","M.Sc. Chemistry (Organic / Analytical Chemistry)","Postgraduate","GSFC-SOCIS"),
 ("SOCIS-MSC-DS","M.Sc. Data Science","Postgraduate","GSFC-SOCIS"),
 ("SOCIS-PHD-CHEM","Ph.D. Chemistry","Doctoral","GSFC-SOCIS"),
 ("SOCIS-PHD-MATH","Ph.D. Mathematics","Doctoral","GSFC-SOCIS"),
 ("SOLS-BSC-HONS-BIOTECH","B.Sc. (Hons.) Biotechnology","Undergraduate","GSFC-SOLS"),
 ("SOLS-BSC-HONS-MICRO","B.Sc. (Hons.) Microbiology","Undergraduate","GSFC-SOLS"),
 ("SOLS-IBS-MS-PHARM","Integrated BS (Hons.)–MS Pharmaceutical Science","Integrated UG–PG","GSFC-SOLS"),
 ("SOLS-MSC-BIOTECH","M.Sc. Biotechnology","Postgraduate","GSFC-SOLS"),
 ("SOLS-MSC-MICRO","M.Sc. Microbiology","Postgraduate","GSFC-SOLS"),
 ("SOLS-PHD-BIOTECH","Ph.D. Biotechnology","Doctoral","GSFC-SOLS"),
 ("SOLS-PHD-MICRO","Ph.D. Microbiology","Doctoral","GSFC-SOLS"),
 ("SOCIT-BTECH-CSE","B.Tech. Computer Science & Engineering","Undergraduate","GSFC-SOCIT"),
 ("SOCIT-BTECH-ECE","B.Tech. Electronics & Communication Engineering","Undergraduate","GSFC-SOCIT"),
 ("SOCIT-BCA","BCA — Bachelor of Computer Applications","Undergraduate","GSFC-SOCIT"),
 ("SOCIT-MTECH-CSE","M.Tech. Computer Science & Engineering","Postgraduate","GSFC-SOCIT"),
 ("SOCIT-PHD-CSE","Ph.D. Computer Science & Engineering","Doctoral","GSFC-SOCIT"),
 ("SOCFS-BTECH-CHE","B.Tech. Chemical Engineering","Undergraduate","GSFC-SOCFS"),
 ("SOCFS-BTECH-FEHS","B.Tech. Fire & Environment, Health & Safety (F&EHS)","Undergraduate","GSFC-SOCFS"),
 ("SOCFS-MTECH-SAFETY","M.Tech. Industrial Safety & Engineering","Postgraduate","GSFC-SOCFS"),
 ("SOCFS-PGD-SAFETY","PG Diploma in Industrial Safety","Diploma","GSFC-SOCFS"),
 ("SOME-BBA","BBA — General","Undergraduate","GSFC-SOME"),
 ("SOME-BBA-BA","BBA — Business Analytics","Undergraduate","GSFC-SOME"),
 ("SOME-BCOM","B.Com. / B.Com. (Hons.)","Undergraduate","GSFC-SOME"),
 ("SOME-IBBA-MBA-AI","Integrated BBA–MBA (with AI in Business)","Integrated UG–PG","GSFC-SOME"),
 ("SOME-MBA-BA","MBA — Business Analytics","Postgraduate","GSFC-SOME"),
 ("SOME-MBA-MKT","MBA — Marketing","Postgraduate","GSFC-SOME"),
 ("SOME-MBA-HRM","MBA — Human Resource Management","Postgraduate","GSFC-SOME"),
 ("SOME-MBA-FIN","MBA — Finance","Postgraduate","GSFC-SOME"),
 ("SOME-PHD-MGMT","Ph.D. Management","Doctoral","GSFC-SOME"),
 ("SOCIT-CSE-SPEC-DS","CSE specialisation — Data Science","Specialisation","GSFC-SOCIT"),
 ("SOCIT-CSE-SPEC-AIML","CSE specialisation — Artificial Intelligence & Machine Learning","Specialisation","GSFC-SOCIT"),
 ("SOCIT-CSE-SPEC-IOT","CSE specialisation — IoT & Automation","Specialisation","GSFC-SOCIT"),
 ("SOCIT-CSE-SPEC-CYBER","CSE specialisation — Cyber Security","Specialisation","GSFC-SOCIT"),
 ("SOME-BBA-SPEC-HRM","BBA specialisation — Human Resource Management","Specialisation","GSFC-SOME"),
 ("SOME-BBA-SPEC-MKT","BBA specialisation — Marketing","Specialisation","GSFC-SOME"),
 ("SOME-BBA-SPEC-AF","BBA specialisation — Accounting & Finance","Specialisation","GSFC-SOME"),
 ("SOME-BBA-SPEC-ITM","BBA specialisation — Information Technology Management","Specialisation","GSFC-SOME"),
]

def _id(kind, code):
    return str(uuid5(NAMESPACE_URL, f"kairos:gsfcu:{kind}:{code}"))

def _upsert(bind, table_name, code, values):
    table = sa.Table(table_name, sa.MetaData(), autoload_with=bind)
    existing = bind.execute(sa.select(table).where(table.c.code == code)).mappings().first()
    if existing:
        update_values = {k: v for k, v in values.items() if k in table.c and k not in {"code", "id"}}
        if update_values:
            bind.execute(table.update().where(table.c.code == code).values(**update_values))
        return existing["id"]
    payload = {k: v for k, v in values.items() if k in table.c}
    payload["id"] = _id(table_name, code)
    bind.execute(table.insert().values(**payload))
    return payload["id"]

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("student_profiles"):
        columns = {c["name"]: c for c in inspector.get_columns("student_profiles")}
        if "programme_id" not in columns and inspector.has_table("programmes"):
            programme_type = {c["name"]: c for c in inspector.get_columns("programmes")}["id"]["type"]
            op.add_column("student_profiles", sa.Column("programme_id", programme_type, nullable=True))
            with op.batch_alter_table("student_profiles") as batch:
                batch.create_foreign_key("fk_student_profiles_programme_id", "programmes", ["programme_id"], ["id"], ondelete="RESTRICT")
        if {"programme_id", "cohort_id"} <= {c["name"] for c in sa.inspect(bind).get_columns("student_profiles")}:
            bind.execute(sa.text("""
                UPDATE student_profiles
                SET programme_id = (SELECT cohorts.programme_id FROM cohorts WHERE cohorts.id = student_profiles.cohort_id)
                WHERE programme_id IS NULL AND cohort_id IS NOT NULL
            """))

    inspector = sa.inspect(bind)
    if not all(inspector.has_table(t) for t in ("institutions", "schools", "departments", "programmes")):
        return
    if bind.execute(sa.text("SELECT id FROM institutions WHERE id=:id"), {"id": INSTITUTION_ID}).first() is None:
        return

    school_ids = {}
    for code, name in SCHOOLS:
        school_ids[code] = _upsert(bind, "schools", code, {
            "institution_id": INSTITUTION_ID, "code": code, "name": name, "is_active": True,
        })

    department_ids = {}
    for code, name, school_code in DEPARTMENTS:
        department_ids[code] = _upsert(bind, "departments", code, {
            "school_id": school_ids[school_code], "code": code, "name": name, "is_active": True,
        })

    for code, name, level, department_code in PROGRAMMES:
        _upsert(bind, "programmes", code, {
            "department_id": department_ids[department_code], "code": code,
            "name": name, "degree_level": level, "is_active": True,
        })

    # Retire rows from the earlier coarse seed; never delete rows referenced by existing accounts.
    old_codes = ["GSFC-CSE", "GSFC-MECH", "GSFC-CHE", "GSFC-FEHS", "GSFC-CHEM", "GSFC-BIOTECH", "GSFC-MICRO", "GSFC-INDCHEM", "GSFC-BBA"]
    bind.execute(sa.text("UPDATE departments SET is_active=0 WHERE code IN :codes").bindparams(
        sa.bindparam("codes", expanding=True)), {"codes": old_codes})

def downgrade():
    # Keep catalogue rows and programme affiliations to avoid invalidating live accounts.
    return
