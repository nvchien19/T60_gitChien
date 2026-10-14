"""Bối cảnh bệnh nhân của một đơn: bệnh nền (mã MeSH) và kiểu gen, cùng các cảnh báo tra được từ đó.

Chỉ tra khớp chính xác trong CSDL, không LLM, không suy luận:
  - thuốc với bệnh nền: `disease_interactions` (DDInter 2.0 và MED-RT), khớp đúng mã MeSH người dùng chọn.
    Không lan theo cây MeSH: chọn "Suy thận mạn" sẽ không ra bản ghi của "Bệnh thận".
  - thuốc với gen: `gene_interactions` (CPIC), khớp đúng kết quả từng gen. Khuyến cáo là nguyên văn CPIC viết
    cho người kê đơn; ở đây chỉ dẫn lại kèm nguồn, không phải lời khuyên của hệ thống.
Bản thử nghiệm để thăm dò nhu cầu, chưa có dược sĩ thẩm định.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.models.tables import DiseaseInteraction, GeneInteraction
from interface.backend.repositories import ddi_repo
from interface.backend.repositories.translations import localize
from interface.backend.schemas.ddi import Citation, FindingOut
from src.tools.context_terms import DISEASE_TERMS
from src.tools.ranker import SEVERITY_VI

NO_RESULT = "No Result"
MAX_CONDITIONS = 30

RESULT_VI = {
    "Poor Metabolizer": "Chuyển hóa kém",
    "Likely Poor Metabolizer": "Nhiều khả năng chuyển hóa kém",
    "Intermediate Metabolizer": "Chuyển hóa trung gian",
    "Likely Intermediate Metabolizer": "Nhiều khả năng chuyển hóa trung gian",
    "Possible Intermediate Metabolizer": "Có thể chuyển hóa trung gian",
    "Normal Metabolizer": "Chuyển hóa bình thường",
    "Rapid Metabolizer": "Chuyển hóa nhanh",
    "Ultrarapid Metabolizer": "Chuyển hóa siêu nhanh",
    "Indeterminate": "Không xác định được",
    "Poor Function": "Chức năng kém",
    "Decreased Function": "Chức năng giảm",
    "Possible Decreased Function": "Có thể giảm chức năng",
    "Normal Function": "Chức năng bình thường",
    "Increased Function": "Chức năng tăng",
    "Normal": "Bình thường",
    "Deficient": "Thiếu hụt",
    "Deficient with CNSHA": "Thiếu hụt kèm thiếu máu tán huyết mạn không do hồng cầu hình cầu (CNSHA)",
    "Variable": "Biến thiên",
    "Malignant Hyperthermia Susceptibility": "Nhạy cảm với tăng thân nhiệt ác tính",
    "Uncertain Susceptibility": "Chưa rõ mức nhạy cảm",
    "increased risk of aminoglycoside-induced hearing loss": "Tăng nguy cơ mất thính lực do aminoglycosid",
    "normal risk of aminoglycoside-induced hearing loss": "Nguy cơ mất thính lực do aminoglycosid ở mức bình thường",
    "uncertain risk of aminoglycoside-induced hearing loss": "Chưa rõ nguy cơ mất thính lực do aminoglycosid",
    "ivacaftor responsive in CF patients": "Đáp ứng với ivacaftor (bệnh nhân xơ nang)",
    "ivacaftor non-responsive in CF patients": "Không đáp ứng với ivacaftor (bệnh nhân xơ nang)",
}
CLASSIFICATION_VI = {"Strong": "Khuyến cáo mạnh", "Moderate": "Khuyến cáo trung bình",
                     "Optional": "Khuyến cáo tùy chọn", "No Recommendation": "Không có khuyến cáo"}
CLASSIFICATION_ORDER = ["Strong", "Moderate", "Optional", "No Recommendation", ""]
POPULATION_VI = {"general": "", "pediatrics": "Trẻ em", "adults": "Người lớn"}
MEDRT_ONLY = ("MED-RT ghi nhận quan hệ chống chỉ định giữa {drug} và bệnh này. Nguồn không kèm mô tả, "
              "mức độ hay tài liệu tham khảo; cần đối chiếu tờ hướng dẫn sử dụng của thuốc.")
MEDRT_ALSO = "MED-RT cũng ghi nhận quan hệ chống chỉ định cho cặp này."


def result_label(value: str) -> str:
    if value.endswith(" positive"):
        return f"{value[:-9]} dương tính"
    if value.endswith(" negative"):
        return f"{value[:-9]} âm tính"
    return RESULT_VI.get(value, value)


def empty_context() -> dict:
    return {"conditions": [], "genes": {}}


async def context_options(db: AsyncSession) -> dict:
    """Danh sách bệnh nền và kết quả gen mà CSDL có bản ghi; chỉ các lựa chọn này mới tra được."""
    rows = (await db.execute(
        select(DiseaseInteraction.mesh_id, DiseaseInteraction.disease, DiseaseInteraction.source_id,
               func.min(DiseaseInteraction.id), func.count(func.distinct(DiseaseInteraction.drug_id)))
        .where(DiseaseInteraction.mesh_id.is_not(None), DiseaseInteraction.mesh_id != "")
        .group_by(DiseaseInteraction.mesh_id, DiseaseInteraction.disease, DiseaseInteraction.source_id))).all()
    conditions: dict[str, dict] = {}
    for mesh_id, disease, source_id, row_id, n_drugs in rows:
        item = conditions.setdefault(mesh_id, {"mesh_id": mesh_id, "name": disease or mesh_id, "row_id": row_id,
                                               "n_drugs": 0, "sources": []})
        item["n_drugs"] = max(item["n_drugs"], n_drugs)
        item["sources"].append(source_id)
    names = await localize(db, "disease_interactions", [
        {"id": item["row_id"], "fields": {"disease": item["name"]}} for item in conditions.values()])
    for item, vi in zip(conditions.values(), names):
        translated = "disease" not in vi["untranslated_fields"]
        item["name_vi"] = vi["disease"] if translated else ""
        item["machine_translation"] = translated and vi["machine_translation"]
        item["keywords"] = DISEASE_TERMS.get(item["mesh_id"], [])
        item["sources"] = sorted(set(item.pop("sources")))
        del item["row_id"]

    gene_rows = (await db.execute(
        select(GeneInteraction.genes, GeneInteraction.lookupkey, GeneInteraction.drug_name))).all()
    genes: dict[str, dict] = {}
    for raw_genes, lookupkey, drug_name in gene_rows:
        # CPIC rows use genes={gene: phenotype}; the earlier imported data stores
        # genes=[gene, ...] and the corresponding phenotype in lookupkey.
        values = raw_genes if isinstance(raw_genes, dict) else {}
        if isinstance(raw_genes, list):
            lookup_values = lookupkey if isinstance(lookupkey, dict) else {}
            values = {gene: lookup_values.get(gene, NO_RESULT) for gene in raw_genes}
        for gene, value in values.items():
            item = genes.setdefault(gene, {"gene": gene, "results": set(), "drugs": set()})
            if drug_name:
                item["drugs"].add(drug_name)
            if value and value != NO_RESULT:
                item["results"].add(value)
    return {
        "conditions": sorted(conditions.values(), key=lambda c: (-c["n_drugs"], c["name"])),
        "genes": [{"gene": g["gene"], "drugs": sorted(g["drugs"]),
                   "results": [{"value": v, "label": result_label(v)} for v in sorted(g["results"])]}
                  for g in sorted(genes.values(), key=lambda g: g["gene"])],
    }


async def validate_context(db: AsyncSession, conditions: list[str], genes: dict[str, str]) -> dict:
    options = await context_options(db)
    known = {c["mesh_id"] for c in options["conditions"]}
    results = {g["gene"]: {r["value"] for r in g["results"]} for g in options["genes"]}
    conditions = list(dict.fromkeys(conditions))
    if len(conditions) > MAX_CONDITIONS:
        raise ValueError(f"Chọn tối đa {MAX_CONDITIONS} bệnh nền")
    if any(c not in known for c in conditions):
        raise ValueError("Có bệnh nền không nằm trong danh mục của CSDL")
    if any(value not in results.get(gene, ()) for gene, value in genes.items()):
        raise ValueError("Có kết quả gen không nằm trong danh mục của CPIC")
    return {"conditions": conditions, "genes": dict(sorted(genes.items()))}


async def disease_findings(db: AsyncSession, drug_ids: list[str], name_by_id: dict[str, str],
                           conditions: list[str]) -> list[FindingOut]:
    rows = await ddi_repo.get_disease_for_drugs(db, drug_ids, conditions)
    if not rows:
        return []
    sources = {s.source_id: s for s in await ddi_repo.list_sources(db)}
    translated = await localize(db, "disease_interactions", [
        {"id": row.id, "fields": {"disease": row.disease, "description": row.description}} for row in rows])
    grouped: dict[tuple[str, str], list] = {}
    for row, vi in zip(rows, translated):
        grouped.setdefault((row.drug_id, row.mesh_id), []).append((row, vi))

    def citation(row) -> Citation:
        source = sources.get(row.source_id)
        return Citation(source_id=row.source_id, source_name=source.name if source else row.source_id,
                        label=row.refs or "", source_url=(source.url or "") if source else "")

    findings = []
    for (drug_id, mesh_id), items in grouped.items():
        medrt = [item for item in items if item[0].source_id == "medrt"]
        described = [item for item in items if item[0].source_id != "medrt"]
        drug = name_by_id.get(drug_id, drug_id)
        for row, vi in described or medrt[:1]:
            only_medrt = row.source_id == "medrt"
            name_vi = vi["disease"] if "disease" not in vi["untranslated_fields"] else ""
            severity = row.severity or "moderate"
            summary = MEDRT_ONLY.format(drug=drug) if only_medrt else vi["description"]
            if medrt and not only_medrt:
                summary = f"{summary}\n\n{MEDRT_ALSO}"
            findings.append(FindingOut(
                pair=[drug, name_vi or row.disease or mesh_id], severity=severity,
                severity_vi=SEVERITY_VI.get(severity, severity), summary=summary,
                original_mechanism="" if only_medrt else (row.description or ""),
                untranslated_fields=[] if only_medrt else [f for f in vi["untranslated_fields"] if f == "description"],
                machine_translation=vi["machine_translation"],
                citations=[citation(row), *(citation(m[0]) for m in medrt if not only_medrt)],
                details={"mesh_id": mesh_id, "disease_en": row.disease or "",
                         "sources": sorted({i[0].source_id for i in items})}))
    order = ["contraindicated", "major", "moderate", "minor"]
    findings.sort(key=lambda f: (order.index(f.severity) if f.severity in order else len(order), f.pair))
    return findings


def is_normal(value: str) -> bool:
    return (value in {"Normal Metabolizer", "Normal Function", "Normal"} or value.endswith(" negative")
            or value.startswith("normal risk"))


def matches(rec_genes: dict[str, str], patient: dict[str, str]) -> bool:
    """Khớp khi mọi gen của khuyến cáo trùng kết quả của bệnh nhân; gen chưa xét nghiệm tính là "No Result"."""
    return (any(gene in patient for gene in rec_genes)
            and all(patient.get(gene, NO_RESULT) == value for gene, value in rec_genes.items()))


def reference_text(rec: GeneInteraction, same_drug: list[GeneInteraction], patient: dict[str, str]) -> str | None:
    """Khuyến cáo của cùng thuốc, cùng nhóm bệnh nhân khi các gen đã xét nghiệm đều ở kết quả bình thường."""
    for other in same_drug:
        if other.population != rec.population or set(other.genes) != set(rec.genes):
            continue
        if all((is_normal(value) and (not value.endswith(" negative") or value[:-9] == rec.genes[gene][:-9]))
               if gene in patient else value == NO_RESULT for gene, value in other.genes.items()):
            return other.recommendation or ""
    return None


async def gene_findings(db: AsyncSession, drug_ids: list[str], name_by_id: dict[str, str],
                        genes: dict[str, str]) -> list[FindingOut]:
    if not drug_ids or not genes:
        return []
    rows = list((await db.execute(
        select(GeneInteraction).where(GeneInteraction.drug_id.in_(drug_ids))
        .order_by(GeneInteraction.id))).scalars().all())
    matched = [row for row in rows if matches(row.genes, genes)]
    if not matched:
        return []
    source = next((s for s in await ddi_repo.list_sources(db) if s.source_id == "cpic"), None)
    translated = await localize(db, "gene_interactions", [
        {"id": row.id, "fields": {"implication_text": row.implication_text, "recommendation": row.recommendation,
                                  "comments": row.comments}} for row in matched])
    merged: dict[tuple, dict] = {}
    for row, vi in zip(matched, translated):
        same_drug = [other for other in rows if other.drug_id == row.drug_id]
        reference = reference_text(row, same_drug, genes)
        key = (row.drug_id, row.recommendation, row.implication_text, row.classification,
               tuple(sorted(row.genes.items())))
        item = merged.setdefault(key, {"row": row, "vi": vi, "populations": [], "comments": [],
                                       "standard": None if reference is None else reference == row.recommendation})
        population = POPULATION_VI.get(row.population or "general", (row.population or "").strip())
        if population and population not in item["populations"]:
            item["populations"].append(population)
        if vi["comments"] and vi["comments"] not in item["comments"]:
            item["comments"].append(vi["comments"])
    findings = []
    for item in merged.values():
        row, vi = item["row"], item["vi"]
        tested = {gene: value for gene, value in row.genes.items() if gene in genes}
        findings.append(FindingOut(
            pair=[name_by_id.get(row.drug_id, row.drug_name),
                  "; ".join(f"{gene}: {result_label(value)}" for gene, value in tested.items())],
            severity="pgx", severity_vi=CLASSIFICATION_VI.get(row.classification or "", row.classification or ""),
            symbol="G", summary=vi["implication_text"], management=vi["recommendation"],
            original_mechanism=row.implication_text or "", original_management=row.recommendation or "",
            untranslated_fields=[f for f in vi["untranslated_fields"] if f != "comments"],
            machine_translation=vi["machine_translation"],
            citations=[Citation(source_id="cpic", source_name=source.name if source else "CPIC",
                                label=row.guideline_name or "", source_url=row.guideline_url or "")],
            details={"genes": tested, "untested_genes": sorted(set(row.genes) - set(genes)),
                     "classification": row.classification or "", "populations": item["populations"],
                     "comments": item["comments"], "same_as_normal": item["standard"]}))

    def rank(finding: FindingOut):
        strength = finding.details["classification"]
        return (finding.details["same_as_normal"] is True,
                CLASSIFICATION_ORDER.index(strength) if strength in CLASSIFICATION_ORDER else len(CLASSIFICATION_ORDER),
                finding.pair)
    findings.sort(key=rank)
    return findings
