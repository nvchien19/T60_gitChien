"""Kiểm tra tương tác thuốc - thuốc: normalize -> lookup -> rank -> explain -> guardrail.

Mọi kết luận lấy từ CSDL (src/services/ddi_repository.py). LLM chỉ diễn giải bằng chứng đã tra được.
"""

from itertools import combinations

from langchain_core.language_models import BaseChatModel

from src.models.schemas import (
    Citation,
    DrugSuggestion,
    DuplicateNote,
    Finding,
    FormNote,
    InteractionCheckResponse,
    Mechanism,
    PairResult,
    ResolvedDrug,
)
from src.services.ddi_repository import DDIRepository
from src.services.explainer import SEVERITY_RANK, SEVERITY_VI, explain_pairs

DISCLAIMER = (
    "Kết quả này là cảnh báo tham khảo dựa trên cơ sở dữ liệu tương tác có trích dẫn, không phải chẩn đoán "
    "hay chỉ định điều trị. Việc dùng tiếp, ngưng hay điều chỉnh thuốc do bác sĩ hoặc dược sĩ quyết định. "
    "Nếu có dấu hiệu bất thường nghiêm trọng, hãy gọi 115 hoặc đến cơ sở y tế gần nhất."
)
NO_RECORD = (
    "Chưa có bản ghi tương tác giữa {a} và {b} trong CSDL hiện có (DDInter 2.0 và quy tắc dạng bào chế). "
    "Chưa có bản ghi không có nghĩa là dùng chung an toàn."
)


def _dedupe_inputs(drugs: list[str]) -> list[str]:
    seen, out = set(), []
    for d in drugs:
        d = " ".join(d.split())
        if d and d.lower() not in seen:
            seen.add(d.lower())
            out.append(d)
    return out


async def _normalize(name: str, repo: DDIRepository) -> tuple[ResolvedDrug, str | None]:
    """Trả về (kết quả chuẩn hóa, ghi chú cho người dùng nếu có)."""
    matches = await repo.find_drug(name)
    exact = [m for m in matches if m.score >= 1.0]
    if exact:
        ok = [m for m in exact if m.status == "ok"]
        chosen = ok or exact
        drug = ResolvedDrug(
            input=name,
            status="ok" if ok else "suggest",
            drug_ids=[m.drug_id for m in chosen],
            drug_names=[m.drug_name for m in chosen],
        )
        note = None
        if not ok:
            note = (
                f"'{name}' được ghép với {', '.join(drug.drug_names)} theo so khớp gần đúng của dữ liệu biệt dược; "
                "hãy đối chiếu tên hoạt chất trên vỏ hộp."
            )
        return drug, note
    if matches:
        sugg = [
            DrugSuggestion(drug_id=m.drug_id, drug_name=m.drug_name, alias=m.alias, score=round(m.score, 3))
            for m in matches
        ]
        names = ", ".join(dict.fromkeys(f"{s.alias} ({s.drug_name})" for s in sugg))
        return (
            ResolvedDrug(input=name, status="suggest", suggestions=sugg),
            f"Không tìm thấy chính xác '{name}'. Có thể bạn muốn nhập: {names}. "
            "Thuốc này CHƯA được đưa vào kiểm tra; hãy nhập lại tên chính xác.",
        )
    return (
        ResolvedDrug(input=name, status="unknown"),
        f"Chưa tìm thấy '{name}' trong CSDL nên chưa kiểm tra được tương tác của thuốc này. "
        "Không có kết quả không có nghĩa là an toàn.",
    )


def _pair_inputs(a: str, b: str, inputs_of: dict[str, list[str]]) -> list[str] | None:
    """Hai tên người dùng nhập khác nhau chứa a và b; None nếu a, b chỉ nằm chung một biệt dược phối hợp."""
    for ia in inputs_of[a]:
        for ib in inputs_of[b]:
            if ia != ib:
                return [ia, ib]
    return None


async def check_interactions(
    drugs: list[str], repo: DDIRepository, *, llm: BaseChatModel | None = None, max_llm_pairs: int = 8
) -> InteractionCheckResponse:
    # 1. normalize
    inputs = _dedupe_inputs(drugs)
    resolved, notes = [], []
    for name in inputs:
        drug, note = await _normalize(name, repo)
        resolved.append(drug)
        if note:
            notes.append(note)

    inputs_of: dict[str, list[str]] = {}
    name_of: dict[str, str] = {}
    for d in resolved:
        for i, n in zip(d.drug_ids, d.drug_names):
            inputs_of.setdefault(i, []).append(d.input)
            name_of[i] = n
    ids = list(inputs_of)

    # 2. lookup
    interactions = await repo.interactions_among(ids)
    rules = await repo.form_rules_among(ids)
    members = await repo.class_members(ids)

    # 3. rank: gộp theo cặp hoạt chất, mức của cặp = mức cao nhất giữa các nguồn
    pairs: dict[frozenset, PairResult] = {}

    def pair_for(a: str, b: str) -> PairResult | None:
        key = frozenset((a, b))
        if key not in pairs:
            used = _pair_inputs(a, b, inputs_of)
            if used is None:
                return None
            pairs[key] = PairResult(
                drug_ids=[a, b],
                drug_names=[name_of[a], name_of[b]],
                inputs=used,
                severity="none",
                severity_vi=SEVERITY_VI["none"],
                mechanisms=[],
            )
        return pairs[key]

    for it in interactions:
        p = pair_for(it.drug_a, it.drug_b)
        if p is not None:
            p.mechanisms.append(
                Mechanism(
                    interaction_id=it.interaction_id,
                    severity=it.severity,
                    severity_vi=SEVERITY_VI[it.severity],
                    mechanism_type=it.mechanism_type,
                    description=it.description,
                    management=it.management,
                    references=it.references,
                    source_id=it.source_id,
                    source_url=it.source_url,
                )
            )
    for r in rules:
        p = pair_for(r.drug_id, r.other_drug_id)
        if p is not None:
            p.form_notes.append(
                FormNote(
                    rule_id=r.rule_id,
                    action=r.action,
                    severity=r.severity,
                    drug_name=r.drug_name,
                    drug_form=r.drug_form,
                    effect_vi=r.effect_vi,
                    management_vi=r.management_vi,
                    evidence=r.evidence,
                    source_id=r.source_id,
                    source_url=r.source_url,
                )
            )
    for p in pairs.values():
        levels = [m.severity for m in p.mechanisms]
        # raise_severity / form_specific nâng mức; no_interaction_for_form chỉ là ghi chú, không hạ mức
        levels += [n.severity for n in p.form_notes if n.action != "no_interaction_for_form"]
        p.severity = max(levels, key=SEVERITY_RANK.__getitem__, default="none")
        p.severity_vi = SEVERITY_VI[p.severity]
    ranked = sorted(pairs.values(), key=lambda p: (-SEVERITY_RANK[p.severity], p.drug_names))

    # Trùng hoạt chất / trùng nhóm điều trị
    duplicates = []
    for i, ins in inputs_of.items():
        if len(ins) > 1:
            duplicates.append(
                DuplicateNote(
                    type="duplicate_active",
                    drug_ids=[i],
                    drug_names=[name_of[i]],
                    inputs=ins,
                    message=f"{', '.join(ins)} cùng chứa hoạt chất {name_of[i]}: dùng chung có thể làm tổng lượng hoạt "
                    "chất này vượt mức. Hãy hỏi bác sĩ hoặc dược sĩ.",
                )
            )
    by_class: dict[str, list] = {}
    for m in members:
        by_class.setdefault(m.class_name, []).append(m)
    for cls, ms in by_class.items():
        cls_ids = list(dict.fromkeys(m.drug_id for m in ms))
        cls_inputs = list(dict.fromkeys(x for i in cls_ids for x in inputs_of[i]))
        if len(cls_ids) > ms[0].max_concurrent and len(cls_inputs) > 1:
            duplicates.append(
                DuplicateNote(
                    type="duplicate_class",
                    drug_ids=cls_ids,
                    drug_names=[name_of[i] for i in cls_ids],
                    inputs=cls_inputs,
                    class_name=cls,
                    message=f"{', '.join(cls_inputs)} cùng thuộc nhóm '{cls}' (DDInter): dùng đồng thời nhiều thuốc cùng "
                    "nhóm có thể trùng lặp tác dụng. Hãy hỏi bác sĩ hoặc dược sĩ.",
                )
            )

    # Cặp (theo tên người dùng nhập) chưa có bản ghi nào
    covered = {frozenset(p.inputs) for p in ranked} | {
        frozenset(x) for d in duplicates for x in combinations(d.inputs, 2)
    }
    found = [d for d in resolved if d.drug_ids]
    no_record = []
    for x, y in combinations(found, 2):
        linked = any(frozenset((i, j)) in pairs for i in x.drug_ids for j in y.drug_ids)
        if not linked and frozenset((x.input, y.input)) not in covered:
            no_record.append([x.input, y.input])
            notes.append(NO_RECORD.format(a=x.input, b=y.input))

    # 4-5. explain + guardrail
    await explain_pairs(ranked, llm, max_llm_pairs=max_llm_pairs)

    findings, citations = [], {}
    for p in ranked:
        for m in p.mechanisms:
            findings.append(
                Finding(
                    type="interaction",
                    drug_ids=p.drug_ids,
                    severity=m.severity,
                    source_id=m.source_id,
                    record_id=str(m.interaction_id),
                )
            )
            citations[(m.source_id, str(m.interaction_id))] = m.source_url
        for n in p.form_notes:
            findings.append(
                Finding(
                    type="interaction",
                    drug_ids=p.drug_ids,
                    severity=n.severity,
                    source_id=n.source_id,
                    record_id=n.rule_id,
                )
            )
            citations[(n.source_id, n.rule_id)] = n.source_url
    for d in duplicates:
        findings.append(Finding(type=d.type, drug_ids=d.drug_ids))

    return InteractionCheckResponse(
        drugs=resolved,
        pairs=ranked,
        duplicates=duplicates,
        no_record_pairs=no_record,
        notes=notes,
        summary=_summary(found, ranked, duplicates),
        disclaimer=DISCLAIMER,
        findings=findings,
        citations=[Citation(source_id=s, record_id=r, url=u) for (s, r), u in citations.items()],
        llm_used=any(p.explanation_source == "llm" for p in ranked),
    )


def _summary(found: list[ResolvedDrug], ranked: list[PairResult], duplicates: list[DuplicateNote]) -> str:
    if len(found) < 2:
        return "Cần ít nhất 2 thuốc nhận diện được trong CSDL để kiểm tra tương tác thuốc - thuốc."
    parts = []
    if ranked:
        top = ranked[0]
        counts = {}
        for p in ranked:
            counts[p.severity_vi] = counts.get(p.severity_vi, 0) + 1
        detail = ", ".join(f"{n} cặp mức {s.lower()}" for s, n in counts.items())
        parts.append(
            f"Tìm thấy {len(ranked)} cặp có bản ghi tương tác ({detail}). Mức cao nhất: "
            f"{top.severity_vi.lower()}, giữa {top.inputs[0]} và {top.inputs[1]}."
        )
    else:
        parts.append(
            "Chưa tìm thấy bản ghi tương tác giữa các thuốc đã nhận diện. "
            "Chưa có bản ghi không có nghĩa là dùng chung an toàn."
        )
    if duplicates:
        parts.append(f"Có {len(duplicates)} cảnh báo trùng hoạt chất hoặc trùng nhóm thuốc.")
    return " ".join(parts)
