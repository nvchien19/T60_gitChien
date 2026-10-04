"""Prescriptions/checks/reviews/assistant — khop FE §13 (un-mock)."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.models.tables import Check, Medication, Prescription, Review
from interface.backend.db.session import get_session
from interface.backend.repositories import ddi_repo
from interface.backend.schemas.ddi import (
    AddMedicationRequest,
    CreatePrescriptionRequest,
    EditMedicationRequest,
    MedicationOut,
    ReviewOut,
    ReviewRequest,
    ReviewStatusUpdate,
)
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


def _rx_out(rx: Prescription, meds: list[Medication]) -> dict:
    return {"id": rx.id, "name": rx.name, "status": rx.status,
            "created_at": rx.created_at.isoformat() if rx.created_at else None,
            "last_checked": rx.last_checked.isoformat() if rx.last_checked else None,
            "highest_severity_vi": rx.highest_severity_vi,
            "checks_count": rx.checks_count or 0,
            "medications": [_med_out(m).model_dump() for m in meds]}


@router.get("/prescriptions")
async def list_rx(q: str = "", status: str = "", limit: int = 20, offset: int = 0,
                  db: AsyncSession = Depends(get_session)):
    stmt = select(Prescription).order_by(Prescription.created_at.desc(), Prescription.id)
    if q:
        stmt = stmt.where(Prescription.id.ilike(f"%{q}%") | Prescription.name.ilike(f"%{q}%"))
    if status and status != "Tất cả":
        stmt = stmt.where(Prescription.status == status)
    r = await db.execute(stmt.offset(max(0, offset)).limit(max(1, min(limit, 100))))
    rows = list(r.scalars().all())
    meds = []
    if rows:
        r = await db.execute(select(Medication).where(Medication.prescription_id.in_([x.id for x in rows])).order_by(Medication.id))
        meds = list(r.scalars().all())
    return {"items": [_rx_out(x, [m for m in meds if m.prescription_id == x.id]) for x in rows]}


async def _add_medications(db: AsyncSession, rx: Prescription, requests: list[AddMedicationRequest]):
    normed = await normalize_list(db, [req.name for req in requests]) if requests else []
    meds = []
    for req, n in zip(requests, normed):
        med = Medication(prescription_id=rx.id, name=req.name,
                         drug_id=n.drug_id or None, ingredient=n.canonical_name or "Chưa xác minh",
                         dose=req.dose, frequency=req.frequency, type=req.type,
                         verified=(n.status == "ok"), norm_status=n.status, suggestions=n.suggestions)
        db.add(med)
        meds.append(med)
    if requests:
        rx.status = "Cần xem lại" if any(n.status != "ok" for n in normed) else "Chưa kiểm tra"
        rx.highest_severity_vi = None
        rx.last_checked = None
    return meds


@router.post("/prescriptions", status_code=201)
async def create_rx(req: CreatePrescriptionRequest | None = None, db: AsyncSession = Depends(get_session)):
    req = req or CreatePrescriptionRequest()
    rx = Prescription(id=f"RX-{uuid.uuid4().hex[:6].upper()}", name=req.name, status="Chưa kiểm tra")
    db.add(rx)
    await db.flush()
    meds = await _add_medications(db, rx, req.medications)
    await db.commit()
    return _rx_out(rx, meds)


@router.get("/prescriptions/{rx_id}")
async def get_rx(rx_id: str, db: AsyncSession = Depends(get_session)):
    rx = await db.get(Prescription, rx_id)
    if not rx:
        raise HTTPException(404, "Không tìm thấy đơn")
    r = await db.execute(select(Medication).where(Medication.prescription_id == rx_id).order_by(Medication.id))
    return _rx_out(rx, list(r.scalars().all()))


@router.post("/prescriptions/{rx_id}/medications", response_model=MedicationOut | list[MedicationOut], status_code=201)
async def add_med(rx_id: str, req: AddMedicationRequest | list[AddMedicationRequest],
                  db: AsyncSession = Depends(get_session)):
    rx = await db.get(Prescription, rx_id)
    if not rx:
        raise HTTPException(404, "Không tìm thấy đơn")
    requests = req if isinstance(req, list) else [req]
    if not 1 <= len(requests) <= 50:
        raise HTTPException(422, "Thêm từ 1 đến 50 thuốc mỗi lần")
    meds = await _add_medications(db, rx, requests)
    await db.commit()
    for med in meds:
        await db.refresh(med)
    out = [_med_out(m) for m in meds]
    return out if isinstance(req, list) else out[0]


@router.put("/prescriptions/{rx_id}/medications", response_model=list[MedicationOut])
async def edit_medications(rx_id: str, requests: list[EditMedicationRequest],
                           db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Prescription).where(Prescription.id == rx_id).with_for_update())
    rx = result.scalar_one_or_none()
    if not rx:
        raise HTTPException(404, "Không tìm thấy đơn")
    if len(requests) > 50:
        raise HTTPException(422, "Đơn thuốc tối đa 50 thuốc")
    result = await db.execute(select(Medication).where(Medication.prescription_id == rx_id))
    existing = {med.id: med for med in result.scalars().all()}
    ids = [req.id for req in requests if req.id is not None]
    if len(set(ids)) != len(ids) or any(med_id not in existing for med_id in ids):
        raise HTTPException(422, "Thuốc không thuộc đơn hoặc bị lặp ID")
    if any(not req.name.strip() for req in requests):
        raise HTTPException(422, "Tên thuốc không được để trống")
    changed = set(ids) != set(existing)
    medications = []
    for req in requests:
        if req.id is None:
            medications.extend(await _add_medications(db, rx, [req]))
            changed = True
            continue
        med = existing[req.id]
        if med.name != req.name:
            normalized = (await normalize_list(db, [req.name]))[0]
            med.drug_id = normalized.drug_id or None
            med.ingredient = normalized.canonical_name or "Chưa xác minh"
            med.verified = normalized.status == "ok"
            med.norm_status = normalized.status
            med.suggestions = normalized.suggestions
        changed = changed or (med.name, med.dose, med.frequency, med.type) != (req.name, req.dose, req.frequency, req.type)
        med.name, med.dose, med.frequency, med.type = req.name, req.dose, req.frequency, req.type
        medications.append(med)
    for med_id, med in existing.items():
        if med_id not in ids:
            await db.delete(med)
    if changed:
        rx.status = "Cần xem lại" if any(not med.verified for med in medications) else "Chưa kiểm tra"
        rx.highest_severity_vi = None
        rx.last_checked = None
    await db.commit()
    for med in medications:
        await db.refresh(med)
    return [_med_out(med) for med in medications]


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
    # luu nguyen van ket qua + ngay cap nhat tung nguon: lan sau mo lai khong tra lai CSDL
    stored = result.model_dump(mode="json")
    stored["sources"] = {s.source_id: str(s.last_updated) if s.last_updated else ""
                         for s in await ddi_repo.list_sources(db)}
    db.add(Check(id=check_id, prescription_id=rx_id, status="done",
                 meds_snapshot=snapshot,
                 summary={"meds_count": len(meds), "findings_count": len(result.findings)},
                 result=stored,
                 max_severity=result.max_severity,
                 steps_done=["normalize", "ingredient", "duplicate", "drug_interaction",
                             "food", "rank", "evidence", "explain"]))
    rx.checks_count = (rx.checks_count or 0) + 1
    rx.last_checked = datetime.now(UTC)
    if result.findings:
        rx.status = "Có tương tác"
        rx.highest_severity_vi = result.max_severity_vi
    else:
        rx.status = "Cần xem lại" if result.unknown else "Đã kiểm tra"
        rx.highest_severity_vi = None
    await db.commit()
    return {"check_id": check_id, "status": "done",
            "max_severity": result.max_severity, "findings_count": len(result.findings)}


@router.get("/checks/{check_id}")
async def get_check(check_id: str, db: AsyncSession = Depends(get_session)):
    c = await db.get(Check, check_id)
    if not c:
        raise HTTPException(404, "Không tìm thấy check")
    # Lan kiem tra da luu ket qua: tra dung ban da luu. Ban ghi cu (truoc khi co cot `result`)
    # khong co ban luu nen phai tra lai tu CSDL hien tai; `from_snapshot` cho FE biet truong hop nay.
    data = c.result
    if not data:
        names = [m.get("name", "") for m in (c.meds_snapshot or [])]
        data = (await run_check(db, names)).model_dump(mode="json") if names else {}
    return {"check_id": c.id, "status": c.status, "summary": c.summary,
            "max_severity": c.max_severity, "steps_done": c.steps_done,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "from_snapshot": bool(c.result),
            "findings": data.get("findings", []),
            "food_findings": data.get("food_findings", []),
            "duplicate_findings": data.get("duplicate_findings", []),
            "disclaimer": data.get("disclaimer", ""),
            "unknown": data.get("unknown", []),
            "no_record_pairs": data.get("no_record_pairs", []),
            "sources": data.get("sources", {})}


@router.get("/prescriptions/{rx_id}/checks")
async def rx_checks(rx_id: str, db: AsyncSession = Depends(get_session)):
    r = await db.execute(select(Check).where(Check.prescription_id == rx_id).order_by(Check.created_at.desc(), Check.id.desc()))
    return {"items": [{"check_id": c.id, "status": c.status, "summary": c.summary,
                       "max_severity": c.max_severity,
                       "created_at": c.created_at.isoformat() if c.created_at else None} for c in r.scalars().all()]}


def _review_out(r: Review) -> ReviewOut:
    return ReviewOut(id=r.id, prescription_id=r.prescription_id, check_id=r.check_id,
                     patient=r.patient or "", med_count=r.med_count or 0,
                     message=r.message, status=r.status,
                     created_at=r.created_at.isoformat() if r.created_at else None)


@router.post("/reviews", status_code=201)
async def create_review(req: ReviewRequest, db: AsyncSession = Depends(get_session)):
    rx = await db.get(Prescription, req.prescription_id)
    if not rx:
        raise HTTPException(404, "Không tìm thấy đơn")
    med_count = req.med_count
    if not med_count:  # FE chua gui -> dem truc tiep tu DB de snapshot dung
        r = await db.execute(select(Medication).where(Medication.prescription_id == rx.id))
        med_count = len(list(r.scalars().all()))
    review = Review(prescription_id=req.prescription_id, check_id=req.check_id or None,
                    patient=req.patient, med_count=med_count,
                    message=req.message, status="Đang chờ")
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return {"review_id": review.id, "status": "Đang chờ dược sĩ xem xét"}


@router.get("/reviews")
async def list_reviews(prescription_id: str = "", status: str = "",
                       limit: int = 50, offset: int = 0,
                       db: AsyncSession = Depends(get_session)):
    stmt = select(Review).order_by(Review.created_at.desc(), Review.id.desc())
    if prescription_id:
        stmt = stmt.where(Review.prescription_id == prescription_id)
    if status and status != "Tất cả":
        stmt = stmt.where(Review.status == status)
    r = await db.execute(stmt.offset(offset).limit(limit))
    return {"items": [_review_out(x).model_dump() for x in r.scalars().all()]}


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def update_review(review_id: int, req: ReviewStatusUpdate,
                        db: AsyncSession = Depends(get_session)):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(404, "Không tìm thấy yêu cầu")
    review.status = req.status
    review.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(review)
    return _review_out(review)


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
