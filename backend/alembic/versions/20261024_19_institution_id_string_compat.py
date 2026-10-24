"""Normalize legacy numeric institution keys to the repository's string key contract.

The application/migration history defines institutions.id as VARCHAR(36), and all
institution foreign keys as the same string type. Some manually provisioned legacy
databases used BIGINT UNSIGNED instead. This forward migration converts the existing
numeric values to their exact decimal string representation (for example, 11 -> "11")
and converts every database-discovered FK that references institutions.id in the same
operation. It does not generate replacement IDs or rewrite unrelated IDs.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_19"
down_revision = "20261024_18"
branch_labels = None
depends_on = None


def _quoted(name: str) -> str:
    return op.get_bind().dialect.identifier_preparer.quote(name)


def _institution_fk_constraints(inspector):
    found = []
    for table_name in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table_name):
            if fk.get("referred_table") != "institutions":
                continue
            referred = fk.get("referred_columns") or []
            if "id" not in referred:
                continue
            name = fk.get("name")
            if not name:
                raise RuntimeError(
                    f"Cannot safely normalize institutions.id: unnamed foreign key on {table_name}"
                )
            found.append((table_name, fk))
    return found


def _mysql_normalize_to_string() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("institutions"):
        return

    institution_columns = {c["name"]: c for c in inspector.get_columns("institutions")}
    if "id" not in institution_columns:
        raise RuntimeError("Cannot normalize institution IDs: institutions.id is missing")
    id_type = institution_columns["id"]["type"]
    if isinstance(id_type, sa.String):
        return
    if bind.dialect.name != "mysql":
        raise RuntimeError(
            "Numeric legacy institution IDs require the MySQL/MariaDB migration path; "
            "no schema changes were applied."
        )

    fk_constraints = _institution_fk_constraints(inspector)
    # Include legacy institution_id columns even if a hand-created legacy schema omitted
    # its FK constraint. The repository model defines these as institution references.
    columns_to_convert = {}
    for table_name in inspector.get_table_names():
        for column in inspector.get_columns(table_name):
            if column["name"] == "institution_id":
                columns_to_convert[(table_name, column["name"])] = column
    for table_name, fk in fk_constraints:
        for local_column, remote_column in zip(
            fk.get("constrained_columns") or [], fk.get("referred_columns") or []
        ):
            if remote_column == "id":
                column = next(
                    item for item in inspector.get_columns(table_name)
                    if item["name"] == local_column
                )
                columns_to_convert[(table_name, local_column)] = column

    # Preflight all candidate references before any DDL. Fail before mutation on
    # orphaned values or identifiers that cannot fit the repository's VARCHAR(36).
    for (table_name, local_column), column in columns_to_convert.items():
        table_q, local_q = _quoted(table_name), _quoted(local_column)
        too_long = bind.exec_driver_sql(
            f"SELECT COUNT(*) FROM {table_q} WHERE {local_q} IS NOT NULL "
            f"AND CHAR_LENGTH(CAST({local_q} AS CHAR)) > 36"
        ).scalar_one()
        if too_long:
            raise RuntimeError(
                f"Cannot normalize institutions.id: {table_name}.{local_column} "
                f"contains {too_long} value(s) longer than 36 characters"
            )
        orphan_count = bind.exec_driver_sql(
            f"SELECT COUNT(*) FROM {table_q} child "
            f"LEFT JOIN institutions parent ON CAST(child.{local_q} AS CHAR) = CAST(parent.id AS CHAR) "
            f"WHERE child.{local_q} IS NOT NULL AND parent.id IS NULL"
        ).scalar_one()
        if orphan_count:
            raise RuntimeError(
                f"Cannot normalize institutions.id: {table_name}.{local_column} "
                f"contains {orphan_count} orphaned reference(s)"
            )

    # Drop all constraints that depend on the PK before changing either side's type.
    for table_name, fk in fk_constraints:
        op.drop_constraint(fk["name"], table_name, type_="foreignkey")

    for (table_name, local_column), column in columns_to_convert.items():
        bind.exec_driver_sql(
            f"ALTER TABLE {_quoted(table_name)} MODIFY COLUMN {_quoted(local_column)} "
            f"VARCHAR(36) {'NULL' if column['nullable'] else 'NOT NULL'}"
        )

    bind.exec_driver_sql(
        f"ALTER TABLE institutions MODIFY COLUMN {_quoted('id')} VARCHAR(36) NOT NULL"
    )

    # Restore the same FK columns, names, and referential actions after type alignment.
    for table_name, fk in fk_constraints:
        options = fk.get("options") or {}
        op.create_foreign_key(
            fk["name"],
            table_name,
            "institutions",
            fk.get("constrained_columns") or [],
            fk.get("referred_columns") or [],
            ondelete=options.get("ondelete"),
            onupdate=options.get("onupdate"),
        )


def upgrade() -> None:
    _mysql_normalize_to_string()


def downgrade() -> None:
    # Keep the normalized string key contract on downgrade as well. Converting back
    # to numeric IDs is unsafe once any UUID institution has been created, so this
    # forward-only compatibility migration deliberately never rewrites identities.
    return
