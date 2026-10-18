"""Ten simultaneous checks share one catalog load and preserve normalization."""

import asyncio

import pytest

from interface.backend.services import check_service


@pytest.mark.asyncio
async def test_ten_concurrent_normalizations_load_catalog_once(monkeypatch):
    for name in ("_ALIASES_CACHE", "_NAMES_CACHE"):
        monkeypatch.setattr(check_service, name, None)

    loads = 0

    async def aliases(_db, limit):
        nonlocal loads
        loads += 1
        await asyncio.sleep(0.01)
        return [("warfarin", "DDInter1", "inn_en", "ddinter", "ok", "Warfarin")]

    async def names(_db, _ids):
        return {"DDInter1": "Warfarin"}

    monkeypatch.setattr(check_service.ddi_repo, "get_aliases_for_fuzzy", aliases)
    monkeypatch.setattr(check_service.ddi_repo, "get_drug_names", names)

    results = await asyncio.gather(*(
        check_service.normalize_list(object(), ["Warfarin", "warfarn"])
        for _ in range(10)
    ))

    assert loads == 1
    assert all(items[0].status == "ok" and items[0].drug_id == "DDInter1" for items in results)
    assert all(items[1].status == "suggest" for items in results)


@pytest.mark.asyncio
async def test_ten_concurrent_interaction_checks(client):
    responses = await asyncio.gather(*(
        client.post("/api/v1/interactions/check", json={"drugs": ["Warfarin", "Aspirin"]})
        for _ in range(10)
    ))

    assert all(response.status_code == 200 for response in responses)
    assert all(response.json()["max_severity"] == "major" for response in responses)
