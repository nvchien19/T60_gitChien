import re

import pytest

from interface.backend.config import get_settings
from interface.backend.schemas.assistant import AssistantRequest
from interface.backend.schemas.ddi import Citation
from interface.backend.services import assistant_external, assistant_llm, assistant_service


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(get_settings(), 'deepseek_api_key', '')


@pytest.mark.asyncio
async def test_brief_and_expanded_preserve_source(client, monkeypatch):
    async def label_reply(names, message, unsafe, detail):
        assert names == ['Keytruda']
        return ('Câu thứ nhất. Câu thứ hai. Câu thứ ba. Câu thứ tư.',
                [Citation(source_id='openfda', source_name='FDA', source_url='https://www.fda.gov')], True)
    monkeypatch.setattr(assistant_service, 'label_reply', label_reply)
    body = {'message': 'Tra cứu thuốc Keytruda'}
    brief = (await client.post('/api/v1/assistant/chat', json=body)).json()
    expanded = (await client.post('/api/v1/assistant/chat', json=dict(body, detail='expanded'))).json()
    assert len(re.split(r'(?<=[.!?])\s+', brief['reply'])) == 3
    assert 'Câu thứ tư' not in brief['reply'] and 'Câu thứ tư' in expanded['reply']
    assert brief['citations'] == expanded['citations']
    assert brief['status'] == expanded['status'] == 'answered'


@pytest.mark.asyncio
async def test_explicit_lookup_with_catalog_hit_calls_labels(client, monkeypatch):
    async def label_reply(names, message, unsafe, detail):
        assert names == ['Aspirin']
        return 'Thông tin nhãn có nguồn.', [Citation(source_id='openfda')], True
    monkeypatch.setattr(assistant_service, 'label_reply', label_reply)
    response = await client.post('/api/v1/assistant/chat', json={'message': 'Tra cứu thuốc Aspirin'})
    assert response.status_code == 200
    assert response.json()['status'] == 'answered'


@pytest.mark.asyncio
async def test_extraction_filters_hallucinated_names_and_redacts(monkeypatch):
    monkeypatch.setattr(get_settings(), 'deepseek_api_key', 'test-key')
    payloads = []
    async def provider(system, payload):
        payloads.append(payload)
        return {'names': ['Keytruda', 'invented-drug', 'Aspirin']}
    monkeypatch.setattr(assistant_llm, 'provider_json', provider)
    names = await assistant_external.extract_drug_names(
        'Cho tôi biết về Keytruda và Aspirin; email: private@example.com', lambda text: False)
    assert names == ['Keytruda', 'Aspirin']
    assert 'private@example.com' not in str(payloads)


@pytest.mark.asyncio
async def test_extraction_fail_closed(monkeypatch):
    monkeypatch.setattr(get_settings(), 'deepseek_api_key', 'test-key')
    async def provider(*args):
        raise RuntimeError('provider unavailable')
    monkeypatch.setattr(assistant_llm, 'provider_json', provider)
    assert await assistant_external.extract_drug_names('Cho biết về Keytruda', lambda text: False) == []


def test_detail_contract():
    assert AssistantRequest(message='test').detail == 'brief'
    with pytest.raises(ValueError):
        AssistantRequest(message='test', detail='unlimited')


@pytest.mark.asyncio
async def test_selected_prescription_without_check_can_lookup(client, monkeypatch):
    async def label_reply(names, message, unsafe, detail):
        return 'Thông tin có nguồn.', [Citation(source_id='openfda')], True
    monkeypatch.setattr(assistant_service, 'label_reply', label_reply)
    rx = (await client.post('/api/v1/prescriptions', json={
        'medications': [{'name': 'Aspirin'}]})).json()['id']
    response = await client.post('/api/v1/assistant/chat', json={
        'prescription_id': rx, 'message': 'Tra cứu thuốc Keytruda'})
    assert response.status_code == 200 and response.json()['status'] == 'answered'
