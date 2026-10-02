"""Pydantic I/O theo BE_DEVELOPMENT.md muc 7 + 13.4."""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_id: str
    source_name: str = ""
    label: str = ""
    source_url: str = ""


class NormalizedItem(BaseModel):
    input: str
    canonical_name: str = ""
    drug_id: str = ""
    status: str = "unknown"
    suggestions: list[dict] = []
    note: str = ""


class NormalizeRequest(BaseModel):
    drugs: list[str] = Field(min_length=1, max_length=50)


class CheckRequest(BaseModel):
    drugs: list[str] = Field(min_length=1, max_length=50)
    include_food: bool = True
    foods: list[str] = []


class FindingOut(BaseModel):
    pair: list[str]
    severity: str
    severity_vi: str = ""
    symbol: str = "!"
    summary: str = ""
    mechanism: str = ""
    management: str = ""
    citations: list[Citation] = []
    match_type: str = "exact"


class CheckResponse(BaseModel):
    normalized: list[NormalizedItem] = []
    unknown: list[NormalizedItem] = []
    max_severity: str = "unknown"
    max_severity_vi: str = "Chưa có bản ghi"
    findings: list[FindingOut] = []
    no_record_pairs: list[list[str]] = []
    food_findings: list[FindingOut] = []
    duplicate_findings: list[FindingOut] = []
    disclaimer: str
    data_coverage: str = ""


class AddMedicationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dose: str = ""
    frequency: str = ""
    type: str = "OTC"


class MedicationOut(BaseModel):
    id: int
    name: str
    ingredient: str = ""
    dose: str = ""
    frequency: str = ""
    type: str = "OTC"
    verified: bool = False
    norm_status: str = "unknown"
    suggestions: list = []


class PrescriptionOut(BaseModel):
    id: str
    status: str
    highest_severity_vi: str | None = None
    checks_count: int = 0
    medications: list[MedicationOut] = []


class ReviewRequest(BaseModel):
    prescription_id: str
    check_id: str = ""
    message: str = Field(min_length=1, max_length=2000)
