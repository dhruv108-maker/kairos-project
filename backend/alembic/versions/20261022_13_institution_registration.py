# """Add institution registration profile fields and self-service onboarding.

# Revision ID: 20261022_13
# Revises: 20261022_12
# """
# from alembic import op
# import sqlalchemy as sa

# revision = "20261022_13"
# down_revision = "20261022_12"
# branch_labels = None
# depends_on = None


# def upgrade() -> None:
#     if not sa.inspect(op.get_bind()).has_table("institutions"):
#         return
#     columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("institutions")}
#     additions = [
#         sa.Column("institution_type", sa.String(40), nullable=True),
#         sa.Column("registration_number", sa.String(120), nullable=True),
#         sa.Column("description", sa.Text(), nullable=True),
#         sa.Column("address", sa.String(500), nullable=True),
#         sa.Column("country", sa.String(100), nullable=True),
#         sa.Column("state", sa.String(100), nullable=True),
#         sa.Column("city", sa.String(100), nullable=True),
#         sa.Column("postal_code", sa.String(30), nullable=True),
#         sa.Column("logo_storage_key", sa.String(500), nullable=True),
#     ]
#     missing = [column for column in additions if column.name not in columns]
#     if missing:
#         with op.batch_alter_table("institutions") as batch:
#             for column in missing:
#                 batch.add_column(column)
#             if "registration_number" not in columns:
#                 batch.create_unique_constraint("uq_institutions_registration_number", ["registration_number"])


# def downgrade() -> None:
#     if not sa.inspect(op.get_bind()).has_table("institutions"):
#         return
#     columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("institutions")}
#     with op.batch_alter_table("institutions") as batch:
#         if "registration_number" in columns:
#             uniques = {u["name"] for u in sa.inspect(op.get_bind()).get_unique_constraints("institutions")}
#             if "uq_institutions_registration_number" in uniques:
#                 batch.drop_constraint("uq_institutions_registration_number", type_="unique")
#         for name in ["logo_storage_key", "postal_code", "city", "state", "country", "address", "description", "registration_number", "institution_type"]:
#             if name in columns:
#                 batch.drop_column(name)
