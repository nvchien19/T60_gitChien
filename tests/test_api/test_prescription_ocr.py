import base64
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from interface.backend.api.routers import prescription_ocr as route
from interface.backend.schemas.prescription_ocr import OcrImageRequest
from interface.backend.services import prescription_ocr as service
from interface.backend.services.auth_service import current_user

IMAGE = {'mime_type': 'image/png', 'image_base64': base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()}
EXTRACTED = {'name': 'Đơn thuốc', 'raw_text': '1. Thuốc A 500 mg', 'medications': [
    {'name': 'Thuốc A', 'dose': '500 mg', 'frequency': 'Uống sáng 1 viên', 'quantity': '10 viên', 'uncertain_fields': []},
    {'name': 'Thuốc B', 'dose': '', 'frequency': '', 'quantity': '', 'uncertain_fields': ['dose']},
], 'warnings': ['Thuốc 2: hàm lượng không rõ']}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    route._calls.clear()
    service._cooldowns.clear()
    monkeypatch.setattr(service, 'get_settings', lambda: SimpleNamespace(
        gemini_api_key='fake-key', google_api_key='', gemini_ocr_model='gemini-3.5-flash', gemini_ocr_timeout_s=65))


def mock_google(monkeypatch, status=200, payload=None, error=None):
    response = httpx.Response(status, json=payload or {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(EXTRACTED)}]}}]})
    post = AsyncMock(return_value=response, side_effect=error)
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    return post


@pytest.mark.asyncio
async def test_fields_and_provider_contract(monkeypatch):
    post = mock_google(monkeypatch)
    result = await service.recognize_prescription(OcrImageRequest(**IMAGE))
    assert result.medications[0].quantity == '10 viên'
    assert result.medications[1].dose == ''
    assert result.medications[1].uncertain_fields == ['dose']
    assert result.provider == 'gemini'
    request = post.call_args.kwargs
    assert request['headers'] == {'x-goog-api-key': 'fake-key'}
    assert request['json']['generationConfig']['responseMimeType'] == 'application/json'
    assert request['json']['contents'][0]['parts'][0]['inlineData']['data'] == IMAGE['image_base64']
    assert 'fake-key' not in result.model_dump_json()


@pytest.mark.asyncio
@pytest.mark.parametrize('status,expected', [(429,429), (401,503), (403,503), (404,503), (500,502), (503,503)])
async def test_provider_errors_do_not_leak(monkeypatch, status, expected):
    mock_google(monkeypatch, status, {'error': {'message': 'fake-key SECRET patient'}})
    with pytest.raises(service.HTTPException) as exc:
        await service.recognize_prescription(OcrImageRequest(**IMAGE))
    assert exc.value.status_code == expected
    assert 'SECRET' not in exc.value.detail


@pytest.mark.asyncio
async def test_timeout(monkeypatch):
    mock_google(monkeypatch, error=httpx.ReadTimeout('secret'))
    with pytest.raises(service.HTTPException) as exc:
        await service.recognize_prescription(OcrImageRequest(**IMAGE))
    assert exc.value.status_code == 504


@pytest.mark.asyncio
@pytest.mark.parametrize('candidate', [
    {'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': json.dumps(EXTRACTED)}]}},
    {'finishReason': 'STOP', 'content': {'parts': [{'text': '{"medications": []}'}]}},
    {'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({**EXTRACTED, 'medications': EXTRACTED['medications'] * 26})}]}},
])
async def test_incomplete_and_invalid_results_rejected(monkeypatch, candidate):
    mock_google(monkeypatch, payload={'candidates': [candidate]})
    with pytest.raises(service.HTTPException) as exc:
        await service.recognize_prescription(OcrImageRequest(**IMAGE))
    assert exc.value.status_code == 502


@pytest.mark.parametrize('image', [
    {**IMAGE, 'image_base64': '@@@'},
    {**IMAGE, 'mime_type': 'image/jpeg'},
])
def test_bad_images(image):
    with pytest.raises(service.HTTPException) as exc:
        service.validate_image(OcrImageRequest(**image))
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_no_key_does_not_call_google(monkeypatch):
    monkeypatch.setattr(service, 'get_settings', lambda: SimpleNamespace(gemini_api_key='', google_api_key=''))
    post = mock_google(monkeypatch)
    with pytest.raises(service.HTTPException) as exc:
        await service.recognize_prescription(OcrImageRequest(**IMAGE))
    assert exc.value.status_code == 503
    post.assert_not_called()


@pytest.mark.asyncio
async def test_route_auth_validation_rate_limit(monkeypatch):
    app = FastAPI()
    app.include_router(route.router)
    mocked = AsyncMock(return_value=service.OcrResponse(**EXTRACTED, model='gemini-3.5-flash'))
    monkeypatch.setattr(route, 'recognize_prescription', mocked)
    async def reject_auth():
        raise service.HTTPException(401, 'Đăng nhập')
    app.dependency_overrides[current_user] = reject_auth
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        assert (await client.post('/prescription-ocr', json=IMAGE)).status_code == 401
        mocked.assert_not_called()
        app.dependency_overrides[current_user] = lambda: SimpleNamespace(id=123)
        assert (await client.post('/prescription-ocr', json={**IMAGE, 'image_base64': 42})).status_code == 422
        assert (await client.post('/prescription-ocr', content='x' * 5700001, headers={'Content-Type': 'application/json'})).status_code == 413
        for _ in range(5):
            assert (await client.post('/prescription-ocr', json=IMAGE)).status_code == 200
        assert (await client.post('/prescription-ocr', json=IMAGE)).status_code == 429
        assert mocked.await_count == 5


def success_response():
    return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(EXTRACTED)}]}}]})


@pytest.mark.asyncio
async def test_auto_stops_at_cheapest_success(monkeypatch):
    post = mock_google(monkeypatch)
    result = await service.recognize_prescription(OcrImageRequest(**IMAGE, model='auto'))
    assert result.model == 'gemini-3.1-flash-lite'
    assert result.attempted_models == ['gemini-3.1-flash-lite']
    assert post.await_count == 1


@pytest.mark.asyncio
async def test_auto_fallback_skips_unhealthy_and_returns_to_cheaper_model(monkeypatch):
    post = AsyncMock(side_effect=[httpx.Response(429), success_response(), success_response(), success_response()])
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    request = OcrImageRequest(**IMAGE, model='auto')
    first = await service.recognize_prescription(request)
    assert first.attempted_models == ['gemini-3.1-flash-lite', 'gemini-3.5-flash-lite']
    assert first.model == 'gemini-3.5-flash-lite'
    second = await service.recognize_prescription(request)
    assert second.attempted_models == ['gemini-3.5-flash-lite']
    for item in service._cooldowns:
        service._cooldowns[item] = 0
    third = await service.recognize_prescription(request)
    assert third.model == 'gemini-3.1-flash-lite'
    assert post.await_count == 4


@pytest.mark.asyncio
async def test_auto_limits_calls_and_rotates_next_request(monkeypatch):
    post = AsyncMock(side_effect=[httpx.Response(503), httpx.Response(404), success_response()])
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    request = OcrImageRequest(**IMAGE, model='auto')
    with pytest.raises(service.HTTPException):
        await service.recognize_prescription(request)
    assert post.await_count == 2
    result = await service.recognize_prescription(request)
    assert result.model == 'gemini-3.8-flash'
    assert result.attempted_models == ['gemini-3.8-flash']


@pytest.mark.asyncio
async def test_auto_auth_error_does_not_retry(monkeypatch):
    post = mock_google(monkeypatch, status=403)
    with pytest.raises(service.HTTPException):
        await service.recognize_prescription(OcrImageRequest(**IMAGE, model='auto'))
    assert post.await_count == 1
    assert not service._cooldowns


@pytest.mark.asyncio
async def test_auto_blocked_content_does_not_retry(monkeypatch):
    post = mock_google(monkeypatch, payload={'candidates': [{'finishReason': 'SAFETY'}]})
    with pytest.raises(service.HTTPException):
        await service.recognize_prescription(OcrImageRequest(**IMAGE, model='auto'))
    assert post.await_count == 1


@pytest.mark.asyncio
async def test_manual_model_is_not_silently_changed(monkeypatch):
    post = mock_google(monkeypatch, status=503)
    with pytest.raises(service.HTTPException):
        await service.recognize_prescription(OcrImageRequest(**IMAGE, model='gemini-3.7-flash'))
    assert post.await_count == 1
    assert 'gemini-3.7-flash:generateContent' in post.call_args.args[0]


@pytest.mark.asyncio
async def test_auto_all_unavailable_does_not_call_google(monkeypatch):
    import time
    from hashlib import sha256
    fingerprint = sha256(b'fake-key').hexdigest()
    for model in service.AUTO_MODELS:
        service._cooldowns[(fingerprint, model)] = time.monotonic() + 60
    post = mock_google(monkeypatch)
    with pytest.raises(service.HTTPException):
        await service.recognize_prescription(OcrImageRequest(**IMAGE, model='auto'))
    post.assert_not_called()


def test_unapproved_model_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        OcrImageRequest(**IMAGE, model='gemini-3-pro')


@pytest.mark.asyncio
async def test_auto_budget_is_bounded(monkeypatch):
    import asyncio
    monkeypatch.setattr(service, 'get_settings', lambda: SimpleNamespace(
        gemini_api_key='fake-key', google_api_key='', gemini_ocr_model='auto', gemini_ocr_timeout_s=.02))
    async def slow_model(*args):
        await asyncio.sleep(.1)
    recognize = AsyncMock(side_effect=slow_model)
    monkeypatch.setattr(service, '_recognize_model', recognize)
    with pytest.raises(service.HTTPException) as error:
        await service.recognize_prescription(OcrImageRequest(**IMAGE, model='auto'))
    assert error.value.status_code == 504
    assert 1 <= recognize.await_count <= 2


def test_provider_schema_is_inline_but_retains_required_fields_and_enums():
    schema = service.provider_extraction_schema()
    encoded = json.dumps(schema)
    assert '$ref' not in encoded and '$defs' not in encoded
    assert 'maxLength' not in encoded and 'additionalProperties' not in encoded
    assert set(schema['required']) == {'name', 'raw_text', 'medications', 'warnings'}
    medication = schema['properties']['medications']['items']
    assert set(medication['required']) == {'name', 'dose', 'frequency', 'quantity', 'uncertain_fields'}
    assert medication['properties']['uncertain_fields']['items']['enum'] == ['name', 'dose', 'frequency', 'quantity']
