"""Fixtures: test DB SQLite rieng + seed toi thieu + override get_session."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from interface.backend.db.session import get_session
from interface.backend.main import app

TEST_DB = Path("data/test_be.db")


def _seed_sync():
    import sqlite3
    if TEST_DB.exists():
        TEST_DB.unlink()
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(TEST_DB)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE sources (source_id TEXT PRIMARY KEY, name TEXT NOT NULL,
            citation TEXT, url TEXT, license TEXT, last_updated DATE);
        CREATE TABLE drugs (drug_id TEXT PRIMARY KEY, name TEXT NOT NULL, name_vi TEXT,
            base_name TEXT NOT NULL, route_variant TEXT, drugbank_id TEXT, atc_code TEXT,
            drug_type TEXT, in_vn BOOLEAN, n_products_valid INTEGER, n_interactions INTEGER);
        CREATE TABLE aliases (alias TEXT NOT NULL, drug_id TEXT NOT NULL, alias_type TEXT,
            source_id TEXT NOT NULL DEFAULT 'dav', status TEXT DEFAULT 'ok', drug_name TEXT,
            PRIMARY KEY (alias, drug_id, source_id));
        CREATE TABLE interaction_mechanisms (mechanism_id TEXT PRIMARY KEY, severity TEXT,
            mechanism_type TEXT, description TEXT NOT NULL, management TEXT,
            "references" TEXT, n_pairs INTEGER, source_id TEXT, embedding JSON);
        CREATE TABLE drug_interactions (interaction_id BIGINT PRIMARY KEY, drug_a TEXT NOT NULL,
            drug_b TEXT NOT NULL, severity TEXT NOT NULL, mechanism_id TEXT,
            mechanism_type TEXT, both_in_vn BOOLEAN, source_id TEXT, source_url TEXT);
        CREATE TABLE food_interactions (id INTEGER PRIMARY KEY, drug_id TEXT, food TEXT NOT NULL,
            food_vi TEXT, severity TEXT, mechanism_type TEXT, description TEXT, management TEXT,
            "references" TEXT, source_id TEXT);
        CREATE TABLE disease_interactions (id INTEGER PRIMARY KEY, drug_id TEXT, disease TEXT,
            mesh_id TEXT, severity TEXT, description TEXT, "references" TEXT, source_id TEXT);
        CREATE TABLE duplication_classes (class_name TEXT NOT NULL, drug_id TEXT NOT NULL,
            drug_name TEXT, max_concurrent INTEGER, source_id TEXT,
            PRIMARY KEY (class_name, drug_id));
        CREATE TABLE ara_interactions (id INTEGER PRIMARY KEY, "table" TEXT, category TEXT,
            victim_drug_ids JSON, victim_form TEXT, victim_is_combination BOOLEAN,
            ara_class TEXT, ara_drug_ids JSON, mechanism TEXT, effect TEXT, severity TEXT,
            recommendation TEXT, route_scope TEXT, source_id TEXT);
        CREATE TABLE dosage_form_rules (rule_id TEXT PRIMARY KEY, drug_id TEXT, drug_route TEXT,
            drug_form TEXT, other_drug_id TEXT, other_route TEXT, severity TEXT, action TEXT,
            effect_vi TEXT, management_vi TEXT, evidence TEXT, source_url TEXT, source_id TEXT);
        CREATE TABLE pk_ddi (perpetrator_id TEXT NOT NULL, victim_id TEXT NOT NULL,
            auc_fold_change FLOAT, magnitude TEXT, source_id TEXT,
            PRIMARY KEY (perpetrator_id, victim_id));
        CREATE TABLE fda_labels (label_set_id TEXT PRIMARY KEY, effective_time TEXT, route TEXT,
            substances TEXT, drug_ids JSON, brand_names TEXT, boxed_warning TEXT,
            contraindications TEXT, drug_interactions TEXT, dosage_forms_and_strengths TEXT,
            source_id TEXT);
        CREATE TABLE products (product_id BIGINT PRIMARY KEY, registration_no TEXT, name TEXT NOT NULL,
            active_ingredients TEXT, strength TEXT, dosage_form TEXT, route TEXT, form_group TEXT,
            enteric_coated BOOLEAN, modified_release BOOLEAN, category TEXT, manufacturer TEXT,
            manufacturer_country TEXT, registrant TEXT, status TEXT, expiry_date DATE, source_id TEXT);
        CREATE TABLE product_ingredients (id INTEGER PRIMARY KEY, product_id BIGINT NOT NULL,
            position INTEGER NOT NULL, ingredient TEXT NOT NULL, strength TEXT, drug_id TEXT,
            base_drug_id TEXT, match_method TEXT, match_score INTEGER, status TEXT,
            route_match TEXT, needs_review BOOLEAN);
        CREATE TABLE prescriptions (id TEXT PRIMARY KEY, status TEXT, highest_severity_vi TEXT,
            checks_count INTEGER, last_checked DATETIME);
        CREATE TABLE medications (id INTEGER PRIMARY KEY, prescription_id TEXT, name TEXT NOT NULL,
            drug_id TEXT, ingredient TEXT, dose TEXT, frequency TEXT, type TEXT,
            verified BOOLEAN, norm_status TEXT, suggestions JSON);
        CREATE TABLE checks (id TEXT PRIMARY KEY, prescription_id TEXT, status TEXT,
            meds_snapshot JSON NOT NULL, summary JSON, max_severity TEXT,
            steps_done JSON, created_at DATETIME);
        CREATE TABLE reviews (id INTEGER PRIMARY KEY, prescription_id TEXT, check_id TEXT,
            message TEXT, status TEXT);
    """)
    cur.executemany("INSERT INTO sources VALUES (?,?,?,?,?,?)", [
        ("ddinter", "DDInter 2.0", "Tian 2025", "https://ddinter2.scbdd.com", "CC BY-NC-SA 4.0", "2026-09-30"),
        ("dav", "DAV", "DAV", "https://dichvucong.dav.gov.vn", "public", "2026-09-30"),
    ])
    cur.executemany("INSERT INTO drugs VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
        ("DDInter1", "Warfarin", "", "Warfarin", "", "DB00682", "B01AA03", "small molecule", 1, 5, 1),
        ("DDInter2", "Aspirin", "", "Aspirin", "", "DB00945", "B01AC06", "small molecule", 1, 5, 1),
    ])
    cur.executemany("INSERT INTO aliases VALUES (?,?,?,?,?,?)", [
        ("warfarin", "DDInter1", "inn_en", "ddinter", "ok", "Warfarin"),
        ("aspirin", "DDInter2", "inn_en", "ddinter", "ok", "Aspirin"),
        ("asca", "DDInter2", "brand_vi", "dav", "suggest", "Aspirin"),
    ])
    cur.execute("INSERT INTO interaction_mechanisms VALUES (?,?,?,?,?,?,?,?,?)",
                ("M1", "major", "synergy", "Tang nguy co chay mau khi dung chung.",
                 "Lien he bac si/duoc si.", "ref1", 1, "ddinter", None))
    cur.execute("INSERT INTO drug_interactions VALUES (?,?,?,?,?,?,?,?,?)",
                (1, "DDInter1", "DDInter2", "major", "M1", "synergy", 1, "ddinter",
                 "https://ddinter2.scbdd.com/server/interact/1/"))
    con.commit()
    con.close()


@pytest.fixture(scope="session", autouse=True)
def _test_db():
    _seed_sync()
    yield


@pytest_asyncio.fixture
async def client():
    url = f"sqlite+aiosqlite:///{TEST_DB}"
    eng = create_async_engine(url, connect_args={"check_same_thread": False})
    maker = async_sessionmaker(eng, expire_on_commit=False)

    async def _override():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await eng.dispose()


@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
