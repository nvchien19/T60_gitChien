"""Evidence-only answers. User and database text never select tools or permissions.

DeepSeek receives public drug evidence and locally redacted conversational context.
There is no shell, dynamic tool dispatcher, or user-supplied tool name here.
The only permitted reads are prescription context and the registered source catalog.
"""
import re
import unicodedata
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.repositories.assistant import assistant_context
from interface.backend.repositories.ddi_repo import list_sources
from interface.backend.schemas.assistant import AssistantRequest, AssistantResponse
from interface.backend.schemas.ddi import Citation, FindingOut
from interface.backend.services.assistant_llm import PRIVATE, explain
from interface.backend.services.assistant_situations import requests_treatment, social_reply
from src.core.guardrails import DISCLAIMER, HANDOFF, sanitize_text
from src.tools.ranker import SEVERITY_VI


def folded(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
                   if unicodedata.category(c) != "Mn")


UNTRUSTED_INSTRUCTION = re.compile(
    r"ignore.{0,60}(instructions|rules)|system.?prompt|api.?key|secret|"
    r"bo qua.{0,60}(quy tac|huong dan)|tiet lo|mat khau|<script|"
    r"\[/?inst\]|<\|.*?\|>|developer message", re.I,
)
SEVERITIES = {"contraindicated", "major", "moderate", "minor"}


def safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if PRIVATE.search(folded(value)) or parsed.query or parsed.fragment:
            return ""
        return value if parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username else ""
    except ValueError:
        return ""


async def answer(db: AsyncSession, request: AssistantRequest) -> AssistantResponse:
    def response(text: str, status: str, **kwargs):
        return AssistantResponse(reply=f"{text}\n\n{HANDOFF}", status=status,
                                 disclaimer=DISCLAIMER, **kwargs)

    message = folded(request.message)
    if UNTRUSTED_INSTRUCTION.search(message):
        return response("Tôi chỉ giải thích bằng chứng tương tác thuốc đã được backend xác minh.",
                        "out_of_scope")
    small_talk = social_reply(request.message)
    if small_talk:
        return AssistantResponse(reply=small_talk, status="answered", disclaimer=DISCLAIMER)
    if requests_treatment(request.message):
        return response("Tôi không đưa ra chẩn đoán hoặc chỉ định điều trị, liều dùng hay thay đổi thuốc. "
                        "Tôi có thể giúp bạn hiểu bằng chứng tương tác để trao đổi với bác sĩ/dược sĩ.",
                        "out_of_scope")
    if not request.prescription_id or request.prescription_id == "chưa chọn":
        return response("Hãy chọn đơn thuốc và chạy kiểm tra để tôi có bằng chứng để giải thích.",
                        "needs_clarification")
    prescription, check, medications = await assistant_context(
        db, request.prescription_id, request.check_id)
    if prescription is None:
        raise HTTPException(404, "Không tìm thấy đơn thuốc")
    if request.check_id and (check is None or check.prescription_id != prescription.id):
        raise HTTPException(422, "Kết quả kiểm tra không thuộc đơn thuốc")
    if check is None or check.status != "done" or not isinstance(check.result, dict):
        return response("Đơn thuốc chưa có kết quả kiểm tra đầy đủ. Hãy chạy kiểm tra trước.",
                        "no_evidence")
    data = check.result
    current = sorted((m.name, m.drug_id, m.dose or "") for m in medications)
    snapshot = sorted((m.get("name", ""), m.get("drug_id"), m.get("dose") or "")
                      for m in (check.meds_snapshot or []))
    if current != snapshot or prescription.last_checked is None:
        return response("Đơn thuốc đã thay đổi sau lần kiểm tra này. Hãy kiểm tra lại đơn hiện tại.",
                        "needs_clarification", check_id=check.id)
    sources = {s.source_id: s for s in await list_sources(db)}
    findings = []
    explanation_findings = []
    food_pair_keys = set()
    limitations = ["Kết quả dựa trên lần kiểm tra đã lưu; không bao gồm thuốc ngoài đơn này."]
    stored_findings = [(raw, False) for raw in data.get("findings", [])]
    stored_findings.extend((raw, True) for raw in data.get("food_findings", []))
    for raw, is_food in stored_findings:
        try:
            finding = FindingOut.model_validate(raw)
        except (ValidationError, TypeError):
            limitations.append("Một phát hiện có dữ liệu không hợp lệ đã bị loại bỏ.")
            continue
        if finding.severity not in SEVERITIES or len(finding.pair) != 2:
            continue
        public_text = " ".join([*finding.pair, finding.summary, finding.mechanism, finding.management, finding.original_management])
        if PRIVATE.search(folded(public_text)):
            limitations.append("Một phát hiện có dấu hiệu chứa thông tin nhạy cảm đã bị loại bỏ.")
            continue
        if UNTRUSTED_INSTRUCTION.search(folded(" ".join([
            *finding.pair, finding.summary, finding.mechanism, finding.management, finding.original_management]))):
            limitations.append("Một phát hiện chứa nội dung không đáng tin cậy đã bị loại bỏ.")
            continue
        verified = []
        for cite in finding.citations:
            source = sources.get(cite.source_id)
            if source is None:
                continue
            url = safe_url(cite.source_url)
            source_url = safe_url(source.url or "")
            # A record link must belong to the registered evidence provider.
            if url and urlsplit(url).hostname != urlsplit(source_url).hostname:
                url = ""
            verified.append(Citation(source_id=source.source_id, source_name=source.source_id if PRIVATE.search(folded(source.name)) else source.name,
                                     label="", source_url=url or source_url))
        if not verified:
            limitations.append("Một phát hiện thiếu nguồn được xác minh đã bị loại bỏ.")
            continue
        finding.citations = verified
        finding.severity_vi = SEVERITY_VI[finding.severity]
        finding.summary = sanitize_text(finding.summary)
        finding.mechanism = sanitize_text(finding.mechanism)
        # Public source recommendation is available for attribution, never as a directive.
        recommendation = finding.original_management or finding.management
        explanation_findings.append(finding.model_copy(update={"management": recommendation,
                                     "original_management": "", "original_mechanism": ""}))
        if is_food:
            food_pair_keys.add(tuple(sorted(finding.pair)))
        # Treatment advice is never repeated by the conversational assistant.
        finding.management = ""
        finding.original_management = ""
        finding.original_mechanism = ""
        findings.append(finding)
        if finding.untranslated_fields:
            limitations.append("Một số mô tả chưa có bản dịch tiếng Việt; đang hiển thị nguyên văn nguồn.")
        if finding.machine_translation:
            limitations.append("Một số nội dung dùng bản dịch máy; cần đối chiếu nguồn gốc khi đánh giá.")
    severities_by_pair = {}
    for finding in findings:
        key = tuple(sorted(finding.pair))
        severities_by_pair.setdefault(key, set()).add(finding.severity)
    if any(len(levels) > 1 for levels in severities_by_pair.values()):
        limitations.append("Các nguồn ghi nhận mức độ khác nhau cho cùng một cặp; cần bác sĩ/dược sĩ đánh giá sự khác biệt.")
    named = [f for f in findings if any(folded(name) in message for name in f.pair)]
    if named:
        findings = named
        explanation_findings = [f for f in explanation_findings if any(folded(name) in message for name in f.pair)]
    citations = []
    for finding in findings:
        for citation in finding.citations:
            if citation not in citations:
                citations.append(citation)
    lines = []
    unknown = data.get("unknown") or []
    def public_name(value):
        if (isinstance(value, str) and 0 < len(value) <= 200
                and not PRIVATE.search(folded(value))
                and not UNTRUSTED_INSTRUCTION.search(folded(value))):
            return value
        return ""

    if unknown:
        names = list(dict.fromkeys(public_name(item.get("input")) for item in unknown
                                   if isinstance(item, dict)))
        names = [name for name in names if name]
        label = ", ".join(names[:10]) or "một số tên thuốc trong đơn"
        limitations.append(
            f"Tên chưa được xác minh trong lần kiểm tra đã lưu: {label}. "
            "Điều này không khẳng định thuốc không có trong database. "
            "Vui lòng xác nhận tên/hoạt chất; nếu danh mục vừa được cập nhật, hãy chạy kiểm tra lại."
        )
    missing_pairs = []
    for pair in data.get("no_record_pairs") or []:
        if isinstance(pair, list) and len(pair) == 2 and all(public_name(n) for n in pair):
            missing_pairs.append(" + ".join(pair))
    if missing_pairs:
        limitations.append(
            "Lần kiểm tra đã lưu chưa tìm thấy bản ghi tương tác cho: "
            + "; ".join(dict.fromkeys(missing_pairs))
            + ". Thuốc có trong danh mục không đồng nghĩa có bản ghi cho mọi cặp; "
            "thiếu bản ghi không chứng minh phối hợp an toàn."
        )
    if not findings:
        lines.append("Chưa có bằng chứng tương tác đã xác minh trong kết quả này để trả lời câu hỏi."
                     + (" Cần xác nhận các tên thuốc bên dưới trước khi kiểm tra đầy đủ." if unknown else
                        " Nếu dữ liệu vừa được cập nhật, hãy chạy kiểm tra lại."))
    if any(term in message for term in ("nen", "lieu", "dung thuoc", "doi thuoc", "ke don", "chan doan")):
        lines.append("Tôi không đưa ra chẩn đoán hoặc chỉ định điều trị. Bạn có thể hỏi bác sĩ/dược sĩ: "
                     "Cảnh báo này ảnh hưởng thế nào đến đơn hiện tại và cần theo dõi gì?")
    elif "hoi duoc si" in message or "hoi bac si" in message:
        lines.append("Bạn có thể hỏi: Cảnh báo nào cần ưu tiên đánh giá? "
                     "Cần bổ sung thông tin nào để đánh giá đơn thuốc?")
    elif "muc do" in message:
        lines.append("Mức độ được lấy từ bản ghi nguồn của từng cặp; "
                     "không phải kết luận về tình trạng cụ thể của người dùng.")
    llm_used = False
    fallback_reason = ""
    if findings:
        food_pairs = {tuple(sorted(f.pair)) for f in findings
                      if tuple(sorted(f.pair)) in food_pair_keys}
        explanation, fallback_reason = await explain(
            request.message, explanation_findings, citations,
            history=[turn.model_dump() for turn in request.history], food_pairs=food_pairs)
        if explanation:
            lines = [explanation]
            llm_used = True
        elif fallback_reason == "no_supported_answer":
            lines = ["Bằng chứng trong database hiện chưa trả lời được điều bạn vừa hỏi. "
                     "Bạn muốn làm rõ cơ chế hoặc mức độ của cặp thuốc nào trong kết quả?"]
        elif fallback_reason == "irrelevant_answer":
            lines = ["Tôi chưa có câu trả lời đã kiểm chứng đúng trọng tâm cho câu hỏi này. "
                     "Bạn đang hỏi về phối hợp thuốc trong đơn hay thực phẩm/đồ uống cần lưu ý?"]
        elif fallback_reason == "ambiguous_question":
            lines = ["Bạn đang muốn hỏi về cặp thuốc hoặc điểm nào trong câu trả lời trước? "
                     "Bạn nói rõ hơn để tôi giải thích đúng ý nhé."]
        elif fallback_reason == "out_of_scope_question":
            lines = ["Tôi hỗ trợ giải thích tương tác thuốc dựa trên bằng chứng. "
                     "Bạn muốn hỏi điều gì về thuốc hoặc kết quả kiểm tra?"]
        elif fallback_reason == "treatment_request":
            lines = ["Tôi không đưa ra chẩn đoán hoặc chỉ định điều trị. "
                     "Tôi có thể giúp bạn hiểu cảnh báo tương tác để trao đổi với bác sĩ/dược sĩ."]
        elif fallback_reason not in {"", "not_applicable"}:
            lines = ["Hiện tôi chưa tạo được câu trả lời đã kiểm chứng cho câu hỏi này. "
                     "Bạn có thể thử hỏi lại hoặc xem nguồn bằng chứng trong kết quả kiểm tra."]
    if (not llm_used and findings
            and fallback_reason in {"irrelevant_answer", "unsafe_output", "ungrounded_output", "unverified_output"}
            and re.search(r"\b(tranh|avoid|khong nen ket hop|khong duoc dung chung)\b", message)):
        lines = ["Nếu bạn hỏi về phối hợp thuốc trong đơn, nguồn đã ghi nhận cảnh báo cho:"]
        for finding in findings:
            marks = " ".join(f"[{citations.index(c) + 1}]" for c in finding.citations)
            lines.append(f"• {' + '.join(finding.pair)}: {finding.severity_vi} theo nguồn {marks}.")
        lines.append("Cảnh báo tương tác không tự động có nghĩa phải tránh mọi phối hợp. "
                     "Bác sĩ/dược sĩ cần đánh giá phối hợp nào cần tránh cho trường hợp cụ thể. "
                     "Nếu bạn hỏi về thực phẩm/đồ uống, bạn vui lòng nói rõ.")
    if not lines:
        lines = ["Bạn muốn tôi giải thích điểm nào hoặc cặp thuốc nào trong kết quả kiểm tra?"]
    lines.extend(note for note in dict.fromkeys(limitations)
                 if not llm_used or note != "Kết quả dựa trên lần kiểm tra đã lưu; không bao gồm thuốc ngoài đơn này.")
    status = "answered" if llm_used else "no_evidence"
    if (unknown and not llm_used) or fallback_reason in {"no_supported_answer", "ambiguous_question", "irrelevant_answer"}:
        status = "needs_clarification"
    if fallback_reason in {"out_of_scope_question", "treatment_request"}:
        status = "out_of_scope"
    return response("\n\n".join(lines), status,
                    check_id=check.id,
                    findings=findings, citations=citations,
                    llm_used=llm_used, fallback_reason=fallback_reason,
                    limitations=list(dict.fromkeys(limitations)))
