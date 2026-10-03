import pytest


@pytest.mark.asyncio
async def test_live_prescription_roundtrip(client):
    response = await client.post('/api/v1/prescriptions', json={
        'name': 'Đơn tái khám',
        'medications': [{'name': 'warfarin', 'dose': '5 mg'}, {'name': 'aspirin'}],
    })
    assert response.status_code == 201
    rx = response.json()
    assert rx['name'] == 'Đơn tái khám'
    assert rx['created_at'] and rx['last_checked'] is None
    assert len(rx['medications']) == 2
    listing = await client.get('/api/v1/prescriptions', params={'q': 'Đơn tái khám'})
    assert listing.json()['items'][0]['id'] == rx['id']
    assert len(listing.json()['items'][0]['medications']) == 2
    first = await client.post(f"/api/v1/prescriptions/{rx['id']}/checks")
    second = await client.post(f"/api/v1/prescriptions/{rx['id']}/checks")
    history = (await client.get(f"/api/v1/prescriptions/{rx['id']}/checks")).json()['items']
    assert history[0]['check_id'] == second.json()['check_id']
    assert history[1]['check_id'] == first.json()['check_id']
    assert history[0]['created_at']
    detail = (await client.get(f"/api/v1/checks/{history[0]['check_id']}")).json()
    assert len(detail['findings']) == 1
    assert detail['findings'][0]['citations']
    current = (await client.get(f"/api/v1/prescriptions/{rx['id']}")).json()
    assert current['highest_severity_vi'] == 'Nghiêm trọng'
    assert current['last_checked'] and current['checks_count'] == 2


@pytest.mark.asyncio
async def test_append_batch_is_atomic(client):
    rx = (await client.post('/api/v1/prescriptions')).json()['id']
    response = await client.post(f'/api/v1/prescriptions/{rx}/medications', json=[{'name': 'warfarin'}, {'name': ''}])
    assert response.status_code == 422
    assert (await client.get(f'/api/v1/prescriptions/{rx}')).json()['medications'] == []
    response = await client.post(f'/api/v1/prescriptions/{rx}/medications', json=[{'name': 'warfarin'}, {'name': 'aspirin'}])
    assert response.status_code == 201
    assert len(response.json()) == 2
    assert len((await client.get(f'/api/v1/prescriptions/{rx}')).json()['medications']) == 2


@pytest.mark.asyncio
async def test_unknown_drug_requires_review(client):
    rx = (await client.post('/api/v1/prescriptions', json={'medications': [{'name': 'thuoc khong ton tai xyz'}]})).json()['id']
    response = await client.post(f'/api/v1/prescriptions/{rx}/checks')
    assert response.status_code == 201
    current = (await client.get(f'/api/v1/prescriptions/{rx}')).json()
    assert current['status'] == 'Cần xem lại'
    detail = (await client.get(f"/api/v1/checks/{response.json()['check_id']}")).json()
    assert detail['unknown']
