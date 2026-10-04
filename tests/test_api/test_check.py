import pytest


@pytest.mark.asyncio
async def test_check_main_flow(client):
    r = await client.post("/api/v1/interactions/check",
                          json={"drugs": ["warfarin", "aspirin"]})
    assert r.status_code == 200
    d = r.json()
    assert d["max_severity"] == "major"
    assert len(d["findings"]) == 1
    assert d["findings"][0]["citations"]
    assert "bác sĩ" in d["disclaimer"] or "dược sĩ" in d["disclaimer"]


@pytest.mark.asyncio
async def test_check_unknown_not_safe(client):
    r = await client.post("/api/v1/interactions/check",
                          json={"drugs": ["warfarin", "thuoc khong ton tai xyz"]})
    assert r.status_code == 200
    d = r.json()
    assert d["unknown"]
    assert "an toàn" not in r.text


@pytest.mark.asyncio
async def test_pair_and_sources(client):
    r = await client.get("/api/v1/interactions/pair", params={"a": "warfarin", "b": "aspirin"})
    assert r.json()["match_type"] == "exact"
    r = await client.get("/api/v1/sources")
    assert r.status_code == 200 and len(r.json()["items"]) >= 2


@pytest.mark.asyncio
async def test_drugs_search_and_normalize(client):
    r = await client.get("/api/v1/drugs/search", params={"q": "warf"})
    assert r.status_code == 200
    r = await client.post("/api/v1/drugs/normalize", json={"drugs": ["asca"]})
    assert r.json()["items"][0]["status"] == "suggest"


@pytest.mark.asyncio
async def test_prescription_flow(client):
    r = await client.post("/api/v1/prescriptions")
    rx = r.json()["id"]
    await client.post(f"/api/v1/prescriptions/{rx}/medications", json={"name": "warfarin"})
    await client.post(f"/api/v1/prescriptions/{rx}/medications", json={"name": "aspirin"})
    r = await client.post(f"/api/v1/prescriptions/{rx}/checks")
    assert r.json()["status"] == "done"
    r = await client.get(f"/api/v1/checks/{r.json()['check_id']}")
    assert r.json()["status"] == "done" and r.json()["findings"]


@pytest.mark.asyncio
async def test_check_detail_is_stored_snapshot(client):
    """Mo lai lan kiem tra cu phai thay dung canh bao luc chay, ke ca khi CSDL da doi."""
    import sqlite3

    from tests.conftest import TEST_DB

    r = await client.post("/api/v1/prescriptions",
                          json={"medications": [{"name": "warfarin"}, {"name": "aspirin"}]})
    rx = r.json()["id"]
    check_id = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()["check_id"]
    before = (await client.get(f"/api/v1/checks/{check_id}")).json()
    assert before["from_snapshot"] and before["findings"]
    assert before["sources"]["ddinter"] == "2026-09-30"

    con = sqlite3.connect(TEST_DB)
    try:
        con.execute("UPDATE drug_interactions SET severity = 'minor' WHERE interaction_id = 1")
        con.commit()
        after = (await client.get(f"/api/v1/checks/{check_id}")).json()
    finally:
        con.execute("UPDATE drug_interactions SET severity = 'major' WHERE interaction_id = 1")
        con.commit()
        con.close()
    assert after["findings"] == before["findings"]
    assert after["findings"][0]["severity"] == "major"
