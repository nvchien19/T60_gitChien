"""Fixtures: test DB SQLite rieng + seed toi thieu + override get_session."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from interface.backend.db.base import Base
from interface.backend.db.models import tables  # noqa: F401  (nap model vao metadata)
from interface.backend.db.session import get_session
from interface.backend.main import app

TEST_DB = Path("data/test_be.db")


def _seed_sync():
    import sqlite3

    if TEST_DB.exists():
        TEST_DB.unlink()
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)

    # Tao schema tu chinh model thay vi hardcode DDL: tranh lech cot khi model doi.
    engine = create_engine(f"sqlite:///{TEST_DB}")
    Base.metadata.create_all(engine)
    engine.dispose()

    con = sqlite3.connect(TEST_DB)
    cur = con.cursor()
    cur.executemany(
        "INSERT INTO sources (source_id, name, citation, url, license, last_updated)"
        " VALUES (?,?,?,?,?,?)",
        [
            ("ddinter", "DDInter 2.0", "Tian 2025", "https://ddinter2.scbdd.com",
             "CC BY-NC-SA 4.0", "2026-09-30"),
            ("dav", "DAV", "DAV", "https://dichvucong.dav.gov.vn", "public", "2026-09-30"),
        ],
    )
    cur.executemany(
        "INSERT INTO drugs (drug_id, name, name_vi, base_name, route_variant, drugbank_id,"
        " atc_code, drug_type, in_vn, n_products, n_products_valid, n_interactions)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("DDInter1", "Warfarin", "", "Warfarin", "", "DB00682", "B01AA03",
             "small molecule", 1, 3, 5, 1),
            ("DDInter2", "Aspirin", "", "Aspirin", "", "DB00945", "B01AC06",
             "small molecule", 1, 4, 5, 1),
        ],
    )
    cur.executemany(
        "INSERT INTO aliases (alias, drug_id, alias_type, source_id, status, drug_name)"
        " VALUES (?,?,?,?,?,?)",
        [
            ("warfarin", "DDInter1", "inn_en", "ddinter", "ok", "Warfarin"),
            ("aspirin", "DDInter2", "inn_en", "ddinter", "ok", "Aspirin"),
            ("asca", "DDInter2", "brand_vi", "dav", "suggest", "Aspirin"),
        ],
    )
    cur.execute(
        "INSERT INTO interaction_mechanisms (mechanism_id, severity, mechanism_type,"
        " description, management, \"references\", n_pairs, source_id, embedding)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        ("M1", "major", "synergy", "Tang nguy co chay mau khi dung chung.",
         "Lien he bac si/duoc si.", "ref1", 1, "ddinter", None),
    )
    cur.execute(
        "INSERT INTO drug_interactions (interaction_id, drug_a, drug_b, severity,"
        " mechanism_id, mechanism_type, both_in_vn, source_id, source_url)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (1, "DDInter1", "DDInter2", "major", "M1", "synergy", 1, "ddinter",
         "https://ddinter2.scbdd.com/server/interact/1/"),
    )
    from interface.backend.services.auth_service import hash_password

    for email, name, role in [
        ("pharmacist@test.vn", "Dược sĩ Test", "pharmacist"),
        ("other@test.vn", "Dược sĩ Khác", "pharmacist"),
        ("doctor@test.vn", "Bác sĩ Test", "doctor"),
    ]:
        cur.execute("INSERT INTO users (email, name, role, password_hash, active) VALUES (?,?,?,?,?)",
                    (email, name, role, hash_password("Test-password-123"), True))
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
    from interface.backend.api.routers.auth import _attempts
    _attempts.clear()
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        result = await ac.post("/api/v1/auth/login", json={
            "email": "pharmacist@test.vn", "password": "Test-password-123",
        })
        assert result.status_code == 200
        yield ac
    app.dependency_overrides.clear()
    await eng.dispose()


@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
