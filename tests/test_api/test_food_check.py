import sqlite3

import pytest

from tests.conftest import TEST_DB


@pytest.mark.asyncio
async def test_food_only_check_preserves_all_evidence_and_history(client):
    with sqlite3.connect(TEST_DB) as con:
        con.executemany(
            'INSERT INTO food_interactions (drug_id, food, food_vi, severity, description, management, "references", source_id) VALUES (?,?,?,?,?,?,?,?)',
            [('DDInter1', f'fixture-food-{i}', f'Thực phẩm thử {i}', 'moderate',
              'Evidence description', 'Keep intake consistent', 'Evidence reference', 'ddinter')
             for i in range(21)],
        )
    try:
        response = await client.post('/api/v1/interactions/check', json={'drugs': ['warfarin']})
        assert response.status_code == 200
        data = response.json()
        foods = data['food_findings']
        assert not data['findings']
        assert len(foods) == 21
        assert foods[0]['management'] == 'Keep intake consistent'
        assert foods[0]['citations'][0]['source_url'] == 'https://ddinter2.scbdd.com'
        assert foods[0]['citations'][0]['label'] == 'Evidence reference'
        assert 'management' in foods[0]['untranslated_fields']
        disabled = await client.post('/api/v1/interactions/check', json={'drugs': ['warfarin'], 'include_food': False})
        assert disabled.json()['food_findings'] == []
        rx = (await client.post('/api/v1/prescriptions', json={'medications': [{'name': 'warfarin'}]})).json()['id']
        check = (await client.post(f'/api/v1/prescriptions/{rx}/checks')).json()['check_id']
        with sqlite3.connect(TEST_DB) as con:
            con.execute("DELETE FROM food_interactions WHERE food LIKE 'fixture-food-%'")
        saved = (await client.get(f'/api/v1/checks/{check}')).json()
        assert saved['from_snapshot']
        assert saved['food_findings'] == foods
    finally:
        with sqlite3.connect(TEST_DB) as con:
            con.execute("DELETE FROM food_interactions WHERE food LIKE 'fixture-food-%'")
