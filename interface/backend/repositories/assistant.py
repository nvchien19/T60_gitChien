"""Read-only, bound database access available to the assistant."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.models.tables import Check, Medication, Prescription


async def assistant_context(db: AsyncSession, prescription_id: str, check_id: str):
    prescription = await db.get(Prescription, prescription_id)
    if prescription is None:
        return None, None, []
    if check_id:
        check = await db.get(Check, check_id)
    else:
        result = await db.execute(
            select(Check).where(Check.prescription_id == prescription_id)
            .order_by(Check.created_at.desc(), Check.id.desc()).limit(1)
        )
        check = result.scalar_one_or_none()
    result = await db.execute(
        select(Medication).where(Medication.prescription_id == prescription_id)
        .order_by(Medication.id)
    )
    return prescription, check, list(result.scalars().all())
