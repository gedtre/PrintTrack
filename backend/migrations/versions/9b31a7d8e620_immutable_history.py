"""Protect the accounting ledger and audit history against UPDATE/DELETE."""

from alembic import op

revision = "9b31a7d8e620"
down_revision = "456bf0535f91"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE FUNCTION printtrack_immutable() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'PrintTrack history is immutable'; END;
    $$ LANGUAGE plpgsql""")
    for table in ("inventory_transactions", "audit_logs", "printer_assignment_history"):
        op.execute(
            f"CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION printtrack_immutable()"
        )


def downgrade():
    for table in ("inventory_transactions", "audit_logs", "printer_assignment_history"):
        op.execute(f"DROP TRIGGER immutable_history ON {table}")
    op.execute("DROP FUNCTION printtrack_immutable()")
