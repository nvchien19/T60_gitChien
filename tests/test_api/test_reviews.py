"""Reviews HITL flow: POST -> GET list -> PATCH status (khop FE ReviewView)."""

import pytest


@pytest.mark.asyncio
async def test_review_flow(client):
    # tao don + thuoc de co med_count that
    r = await client.post("/api/v1/prescriptions")
    assert r.status_code == 201
    rx_id = r.json()["id"]
    m = await client.post(f"/api/v1/prescriptions/{rx_id}/medications",
                          json={"name": "Warfarin", "dose": "5 mg"})
    assert m.status_code == 201

    # POST review khong gui med_count -> BE tu dem (1)
    r = await client.post("/api/v1/reviews",
                          json={"prescription_id": rx_id, "message": "Xin tu van"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "Đang chờ dược sĩ xem xét"
    review_id = body["review_id"]

    # GET list: co ban ghi moi nhat, med_count snapshot = 1
    r = await client.get("/api/v1/reviews", params={"prescription_id": rx_id})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert items[0]["id"] == review_id
    assert items[0]["status"] == "Đang chờ"
    assert items[0]["med_count"] == 1

    # PATCH sang Da phan hoi
    r = await client.patch(f"/api/v1/reviews/{review_id}",
                           json={"status": "Đã phản hồi"})
    assert r.status_code == 200
    assert r.json()["status"] == "Đã phản hồi"

    # status la -> 422
    r = await client.patch(f"/api/v1/reviews/{review_id}", json={"status": "pending"})
    assert r.status_code == 422

    # don khong ton tai -> 404
    r = await client.post("/api/v1/reviews",
                          json={"prescription_id": "RX-KHONG-CO", "message": "x"})
    assert r.status_code == 404
