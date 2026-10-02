"""Prescriptions/checks/reviews/assistant — khop FE §13 (un-mock)."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.models.tables import Check, Medication, Prescription, Review
from interface.backend.db.session import get_session
from interface.backend.schemas.ddi import AddMedicationRequest, MedicationOut, ReviewRequest
from interface.backend.services.check_service import normalize_list, run_check
from src.core.guardrails import HANDOFF

router = APIRouter(tags=["prescriptions"])


def _med_out(m: Medication) -> MedicationOut:
    return MedicationOut(id=m.id, name=m.name, ingredient=m.ingredient or "",
                         dose=m.dose or "", frequency=m.frequency or "",
                         type=m.type or "OTC", verified=m.verified,
                         norm_status=m.norm_status or "unknown",
                         suggestions=m.suggestions or [])


@router.get("/prescriptions/summary")
async def summary(db: AsyncSession = Depends(get_session)):
    r = await db.execute(select(Prescription))
    rows = list(r.scalars().all())
    return {"total": len(rows),
            "checked": sum(1 for x in rows if (x.checks_count or 0) > 0),
            "with_interaction": sum(1 for x in rows if x.status == "Có tương tác"),
            "needs_review": sum(1 for x in rows if x.status == "Cần xem lại")}


@router.get("/prescriptions")
async def list_rx(q: str = "", status: str = "", limit: int = 20, offset: int = 0,
                  db: AsyncSession = Depends(get_session)):
    r = await db.execute(select(Prescription).offset(offset).limit(limit))
    rows = list(r.scalars().all())
    if q:
        rows = [x for x in rows if q.lower() in x.id.lower()]
    if status and status != "Tất cả":
        rows = [x for x in rows if x.status == status]
    return {"items": [{"id": x.id, "status": x.status,
                       "highest_severity_vi": x.highest_severity_vi,
                       "checks_count": x.checks_count} for x in rows]}


@router.post("/prescriptions", status_code=201)
async def create_rx(db: AsyncSession = Depends(get_session)):
    rx_id = f"RX-{uuid.uuid4().hex[:6].upper()}"
    db.add(Prescription(id=rx_id, status="Chưa kiểm tra"))
    await db.commit()
    return {"id": rx_id, "status": "Chưa kiểm tra"}


@router.get("/prescriptions/{rx_id}")
async def get_rx(rx_id: str, db: AsyncSession = Depends(get_session)):
    rx = await db.get(Prescription, rx_id)
    if not rx:
        raise HTTPException(404, "Không tìm thấy đơn")
    r = await db.execute(select(Medication).where(Medication.prescription_id == rx_id))
    meds = [_med_out(m).model_dump() for m in r.scalars().all()]
    return {"id": rx.id, "status": rx.status, "medications": meds,
            "checks_count": rx.checks_count}


@router.post("/prescriptions/{rx_id}/medications", response_model=MedicationOut, status_code=201)
async def add_med(rx_id: str, req: AddMedicationRequest,
                  db: AsyncSession = Depends(get_session)):
    rx = await db.get(Prescription, rx_id)
    if not rx:
        raise HTTPException(404, "Không tìm thấy đơn")
    normed = await normalize_list(db, [req.name])
    n = normed[0]
    med = Medication(prescription_id=rx_id, name=req.name,
                     drug_id=n.drug_id or None, ingredient=n.canonical_name or "Chưa xác minh",
                     dose=req.dose, frequency=req.frequency, type=req.type,
                     verified=(n.status == "ok"), norm_status=n.status,
                     suggestions=n.suggestions)
    db.add(med)
    if n.status != "ok":
        rx.status = "Cần xem lại"  # thuoc unverified -> nhac kiem tra lai (§13.5)
    await db.commit()
    await db.refresh(med)
    return _med_out(med)


@router.post("/prescriptions/{rx_id}/checks", status_code=201)
async def run_rx_check(rx_id: str, db: AsyncSession = Depends(get_session)):
    rx = await db.get(Prescription, rx_id)
    if not rx:
        raise HTTPException(404, "Không tìm thấy đơn")
    r = await db.execute(select(Medication).where(Medication.prescription_id == rx_id))
    meds = list(r.scalars().all())
    names = [m.drug_id and (m.ingredient or m.name) or m.name for m in meds]
    if not names:
        raise HTTPException(400, "Đơn chưa có thuốc")
    # chay check tren ten thuoc goc de normalize lai dong nhat
    result = await run_check(db, [m.name for m in meds])
    check_id = f"CHECK-{uuid.uuid4().hex[:6].upper()}"
    snapshot = [{"name": m.name, "drug_id": m.drug_id, "dose": m.dose} for m in meds]
    db.add(Check(id=check_id, prescription_id=rx_id, status="done",
                 meds_snapshot=snapshot,
                 summary={"meds_count": len(meds), "findings_count": len(result.findings)},
                 max_severity=result.max_severity,
                 steps_done=["normalize", "ingredient", "duplicate", "drug_interaction",
                             "food", "rank", "evidence", "explain"]))
    rx.checks_count = (rx.checks_count or 0) + 1
    rx.last_checked = datetime.now(UTC)
    if result.findings:
        rx.status = "Có tương tác"
        rx.highest_severity_vi = result.max_severity_vi
    else:
        rx.status = "Đã kiểm tra"
    await db.commit()
    return {"check_id": check_id, "status": "done",
            "max_severity": result.max_severity, "findings_count": len(result.findings)}


@router.get("/checks/{check_id}")
async def get_check(check_id: str, db: AsyncSession = Depends(get_session)):
    c = await db.get(Check, check_id)
    if not c:
        raise HTTPException(404, "Không tìm thấy check")
    # tai tao findings tu snapshot (deterministic) de tra chi tiet
    names = [m.get("name", "") for m in (c.meds_snapshot or [])]
    result = await run_check(db, names) if names else None
    return {"check_id": c.id, "status": c.status, "summary": c.summary,
            "max_severity": c.max_severity, "steps_done": c.steps_done,
            "findings": [f.model_dump() for f in result.findings] if result else [],
            "disclaimer": result.disclaimer if result else ""}


@router.get("/prescriptions/{rx_id}/checks")
async def rx_checks(rx_id: str, db: AsyncSession = Depends(get_session)):
    r = await db.execute(select(Check).where(Check.prescription_id == rx_id))
    return {"items": [{"check_id": c.id, "status": c.status, "summary": c.summary,
                       "max_severity": c.max_severity} for c in r.scalars().all()]}


@router.post("/reviews", status_code=201)
async def create_review(req: ReviewRequest, db: AsyncSession = Depends(get_session)):
    db.add(Review(prescription_id=req.prescription_id, check_id=req.check_id or None,
                  message=req.message, status="pending"))
    await db.commit()
    return {"status": "Đang chờ dược sĩ xem xét"}


@router.post("/assistant/chat")
async def assistant_chat(payload: dict, db: AsyncSession = Depends(get_session)):
    """P0 rule-based: chi doc findings cua check hien tai + handoff. Khong LLM."""
    check_id = payload.get("check_id", "")
    message = payload.get("message", "")
    if check_id:
        c = await db.get(Check, check_id)
        if c and c.summary:
            n = (c.summary.get("findings_count") or 0)
            return {"reply": f"Đơn có {n} phát hiện (mức cao nhất: {c.max_severity}). {HANDOFF}",
                    "mode": "rule-based"}
    _ = message
    return {"reply": f"Tôi chỉ tra cứu cảnh báo từ CSDL. {HANDOFF}", "mode": "rule-based"}
