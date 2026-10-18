"""Regression for development databases partially created by create_all."""
import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


@pytest.mark.parametrize("already_created", [False, True])
def test_patient_context_migration_preserves_precreated_gene_data(already_created):
    path = Path(__file__).resolve().parents[2] / "alembic/versions/b2d5e7f91a38_patient_context_gene_interactions.py"
    spec = importlib.util.spec_from_file_location("patient_context_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE prescriptions (id VARCHAR PRIMARY KEY)"))
        connection.execute(sa.text("CREATE TABLE drugs (drug_id VARCHAR PRIMARY KEY)"))
        connection.execute(sa.text("CREATE TABLE sources (source_id VARCHAR PRIMARY KEY)"))
        with Operations.context(MigrationContext.configure(connection)):
            if already_created:
                migration._create_gene_table()
                connection.execute(sa.text("INSERT INTO gene_interactions (id, drug_name, genes) VALUES (1, 'fixture', '{}')"))
            migration.upgrade()
            # Re-running against an existing schema must not duplicate objects or remove rows.
            migration.upgrade()
        inspector = sa.inspect(connection)
        assert "patient_context" in {column["name"] for column in inspector.get_columns("prescriptions")}
        assert inspector.has_table("gene_interactions")
        assert "ix_gene_interactions_drug_id" in {index["name"] for index in inspector.get_indexes("gene_interactions")}
        count = connection.scalar(sa.text("SELECT count(*) FROM gene_interactions"))
        assert count == (1 if already_created else 0)
    engine.dispose()
