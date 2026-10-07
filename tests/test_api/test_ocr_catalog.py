import sqlite3

import pytest


@pytest.mark.asyncio
async def test_ocr_product_lookup_preserves_strength_and_literal_search(client):
    with sqlite3.connect('data/test_be.db') as db:
        db.execute("INSERT OR REPLACE INTO products (product_id,name,strength,active_ingredients,source_id,enteric_coated,modified_release) VALUES (?,?,?,?,?,?,?)",
                   (909001, 'Brand OCR 500mg', '500mg', 'Ingredient OCR', 'dav', False, False))
    response = await client.get('/api/v1/drugs/products/search', params={'q': 'Brand OCR'})
    assert response.status_code == 200
    rows = response.json()['items']
    assert len(rows) == 1
    assert rows[0]['product_id'] == 909001
    assert rows[0]['strength'] == '500mg'
    assert rows[0]['active_ingredients'] == 'Ingredient OCR'
    response = await client.get('/api/v1/drugs/products/search', params={'q': 'Brand%OCR'})
    assert response.json()['items'] == []


@pytest.mark.asyncio
async def test_ocr_product_lookup_validation_and_auth(client):
    for params in ({'q': 'x'}, {'q': 'Brand', 'limit': -1}, {'q': 'Brand', 'limit': 51}):
        assert (await client.get('/api/v1/drugs/products/search', params=params)).status_code == 422
    assert (await client.get('/api/v1/drugs/products/search', params={'q': '  '})).json()['items'] == []
    client.cookies.clear()
    assert (await client.get('/api/v1/drugs/products/search', params={'q': 'Brand'})).status_code == 401
