import sqlite3
from types import SimpleNamespace

import httpx
import pytest

from interface.backend.repositories.translations import source_hash
from scripts.translate_evidence import translate


@pytest.mark.asyncio
async def test_check_uses_vi_and_rejects_stale_translation(client):
    url = '/api/v1/interactions/check'
    payload = {'drugs': ['warfarin', 'aspirin']}
    before = (await client.post(url, json=payload)).json()['findings'][0]
    assert before['untranslated_fields'] == ['description', 'management']
    connection = sqlite3.connect('data/test_be.db')
    originals = connection.execute('SELECT description,management FROM interaction_mechanisms WHERE mechanism_id=?', ('M1',)).fetchone()
    for field, original, vietnamese in zip(('description', 'management'), originals,
                                         ('Có nguy cơ tương tác giữa hai thuốc.', 'Trao đổi với bác sĩ hoặc dược sĩ.')):
        connection.execute('INSERT INTO content_translations VALUES (?,?,?,?,?,?,?,?,?)',
                           ('interaction_mechanisms', 'M1', field, 'vi', source_hash(original), vietnamese,
                            'google', False, '2026-10-04T00:00:00+00:00'))
    connection.commit()
    try:
        result = (await client.post(url, json=payload)).json()['findings'][0]
        assert result['summary'] == 'Có nguy cơ tương tác giữa hai thuốc.'
        assert result['management'] == 'Trao đổi với bác sĩ hoặc dược sĩ.'
        assert result['machine_translation'] and not result['untranslated_fields']
        assert result['severity'] == before['severity'] and result['citations'] == before['citations']
        assert result['original_mechanism'] == originals[0]
        connection.execute("UPDATE content_translations SET source_hash='outdated',reviewed=1 WHERE field='description'")
        connection.commit()
        stale = (await client.post(url, json=payload)).json()['findings'][0]
        assert stale['summary'] == originals[0]
        assert stale['untranslated_fields'] == ['description']
        assert stale['management'] == result['management']
    finally:
        connection.execute('DELETE FROM content_translations')
        connection.commit()
        connection.close()


@pytest.mark.asyncio
async def test_google_translation_batch_and_key_not_in_url():
    def handle(request):
        assert 'key=' not in str(request.url)
        assert request.headers['x-goog-api-key'] == 'fake-key'
        return httpx.Response(200, json={'data': {'translations': [
            {'translatedText': 'Thuốc A &amp; B'}, {'translatedText': 'Theo dõi'}]}})
    settings = SimpleNamespace(google_translation_project='', google_translation_api_key='fake-key', google_translation_glossary='')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await translate(client, ['Drug A & B', 'Monitor'], 'google', settings) == ['Thuốc A & B', 'Theo dõi']


@pytest.mark.asyncio
async def test_provider_failure_does_not_expose_key():
    settings = SimpleNamespace(google_translation_project='', google_translation_api_key='secret-key', google_translation_glossary='')
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(403))) as client:
        with pytest.raises(RuntimeError, match='HTTP 403') as error:
            await translate(client, ['Drug A'], 'google', settings)
        assert 'secret-key' not in str(error.value)


@pytest.mark.asyncio
async def test_gemini_translation_and_incomplete_output():
    import json
    settings = SimpleNamespace(gemini_api_key='secret-gemini', google_api_key='', gemini_model='gemini-3.8-flash')
    def handle(request):
        assert 'secret-gemini' not in str(request.url)
        assert request.headers['x-goog-api-key'] == 'secret-gemini'
        body = json.loads(request.content)
        assert body['generationConfig']['responseJsonSchema']['properties']['translations']['minItems'] == 2
        return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
            {'text': json.dumps({'translations': ['Bằng chứng', 'Theo dõi']})}]}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await translate(client, ['Evidence', 'Monitor'], 'gemini', settings) == ['Bằng chứng', 'Theo dõi']
    for result in (
        {'candidates': []},
        {'candidates': [{'finishReason': 'MAX_TOKENS'}]},
        {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{"translations":["Thiếu"]}'}]}}]},
    ):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=result))) as client:
            with pytest.raises(RuntimeError):
                await translate(client, ['Evidence', 'Monitor'], 'gemini', settings)


@pytest.mark.asyncio
async def test_gemini_removes_nul_control_characters_before_database_write():
    import json
    settings = SimpleNamespace(gemini_api_key='fake', google_api_key='', gemini_model='gemini-3.5-flash')
    result = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
        {'text': json.dumps({'translations': ['Theo\x00 dõi']})}]}}]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=result))) as client:
        assert await translate(client, ['Monitor'], 'gemini', settings) == ['Theo dõi']


@pytest.mark.asyncio
async def test_gemini_daily_quota_is_actionable():
    from scripts.translate_evidence import DailyQuotaExceeded
    settings = SimpleNamespace(gemini_api_key='secret', google_api_key='', gemini_model='gemini-3.5-flash')
    payload = {'error': {'details': [{'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]}]}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(429, json=payload))) as client:
        with pytest.raises(DailyQuotaExceeded, match='daily quota exhausted'):
            await translate(client, ['Evidence'], 'gemini', settings)
