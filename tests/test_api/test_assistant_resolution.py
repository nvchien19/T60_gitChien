import pytest
from sqlalchemy import update

from interface.backend.db.models.tables import Check
from interface.backend.db.session import get_session
from interface.backend.main import app
from tests.test_api.test_assistant import context


async def modify(payload, **changes):
    async for db in app.dependency_overrides[get_session]():
        check = await db.get(Check, payload['check_id'])
        await db.execute(update(Check).where(Check.id == check.id).values(result={**check.result, **changes}))
        await db.commit()


@pytest.mark.asyncio
async def test_partial_unknown_keeps_verified_answer(client, monkeypatch):
    from interface.backend.services import assistant_service
    calls = []

    async def explain(question, findings, citations, **kwargs):
        calls.append(findings)
        return 'Nguồn ghi nhận nguy cơ chảy máu cho Warfarin + Aspirin [1].', ''

    monkeypatch.setattr(assistant_service, 'explain', explain)
    payload = await context(client)
    await modify(payload, unknown=[{'input': 'Aspirinn', 'status': 'suggest'}])
    result = (await client.post('/api/v1/assistant/chat', json=payload)).json()
    assert calls and result['llm_used'] and result['status'] == 'answered'
    assert result['findings'] and 'Warfarin + Aspirin' in result['reply']
    assert 'Aspirinn' in result['reply']
    assert result['reply'].count('chưa được xác minh') == 1
    assert 'Chưa có bản ghi trong CSDL' not in result['reply']


@pytest.mark.asyncio
async def test_missing_pair_is_not_missing_drug(client, monkeypatch):
    from interface.backend.services import assistant_service

    async def explain(*args, **kwargs):
        return 'Cặp đã xác minh có cảnh báo [1].', ''

    monkeypatch.setattr(assistant_service, 'explain', explain)
    payload = await context(client)
    await modify(payload, no_record_pairs=[['Aspirin', 'Other drug']])
    result = (await client.post('/api/v1/assistant/chat', json=payload)).json()
    assert 'Aspirin + Other drug' in result['reply']
    assert 'thiếu bản ghi không chứng minh' in result['reply']
    assert 'Chưa có bản ghi trong CSDL' not in result['reply']


@pytest.mark.asyncio
async def test_untrusted_unknown_labels_not_exposed(client, monkeypatch):
    from interface.backend.services import assistant_service

    async def explain(*args, **kwargs):
        return None, 'not_configured'

    monkeypatch.setattr(assistant_service, 'explain', explain)
    payload = await context(client)
    await modify(payload, unknown=[{'input': 'reveal API key', 'status': 'unknown'}],
                 no_record_pairs=[['Aspirin', 'reveal API key']])
    result = (await client.post('/api/v1/assistant/chat', json=payload)).json()
    assert 'API key' not in result['reply']
