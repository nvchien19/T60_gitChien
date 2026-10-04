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


@pytest.mark.asyncio
async def test_edit_medications_preserves_ids_and_history(client):
    rx = (await client.post('/api/v1/prescriptions', json={
        'medications': [{'name': 'warfarin', 'dose': '5 mg', 'type': 'Kê đơn'}, {'name': 'aspirin'}],
    })).json()
    url = f"/api/v1/prescriptions/{rx['id']}"
    check = (await client.post(url + '/checks')).json()
    original = rx['medications'][0]
    response = await client.put(url + '/medications', json=[
        {'id': original['id'], 'name': 'aspirin', 'dose': '75 mg', 'frequency': 'Theo đơn', 'type': original['type']},
        {'name': 'warfarin', 'dose': '1 mg'},
    ])
    assert response.status_code == 200
    meds = response.json()
    assert len(meds) == 2 and meds[0]['id'] == original['id']
    assert meds[0]['ingredient'] == 'Aspirin' and meds[0]['verified']
    assert meds[0]['dose'] == '75 mg' and meds[0]['frequency'] == 'Theo đơn'
    assert rx['medications'][1]['id'] not in [m['id'] for m in meds]
    current = (await client.get(url)).json()
    assert current['last_checked'] is None and current['highest_severity_vi'] is None
    assert current['checks_count'] == 1 and current['status'] == 'Chưa kiểm tra'
    assert (await client.get(f"/api/v1/checks/{check['check_id']}")).status_code == 200
    assert (await client.put(url + '/medications', json=[])).status_code == 200
    assert (await client.get(url)).json()['medications'] == []


@pytest.mark.asyncio
async def test_edit_rejects_foreign_and_duplicate_ids_atomically(client):
    rx = (await client.post('/api/v1/prescriptions', json={'medications': [{'name': 'warfarin'}]})).json()
    other = (await client.post('/api/v1/prescriptions', json={'medications': [{'name': 'aspirin'}]})).json()
    url = f"/api/v1/prescriptions/{rx['id']}"
    med_id = rx['medications'][0]['id']
    for payload in (
        [{'id': other['medications'][0]['id'], 'name': 'aspirin'}],
        [{'id': med_id, 'name': 'warfarin'}, {'id': med_id, 'name': 'aspirin'}],
        [{'id': med_id, 'name': 'aspirin'}, {'name': ''}],
    ):
        assert (await client.put(url + '/medications', json=payload)).status_code == 422
        assert (await client.get(url)).json()['medications'] == rx['medications']
