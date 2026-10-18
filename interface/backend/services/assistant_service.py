"""Evidence-only answers. User and database text never select tools or permissions.

DeepSeek receives public drug evidence and locally redacted conversational context.
There is no shell, dynamic tool dispatcher, or user-supplied tool name here.
Permitted reads include prescription context, the catalog and fixed public label API.
General food-source answers use a separate curated public nutrition catalog.
"""
import re
import unicodedata
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.repositories.assistant import assistant_context, drug_in_catalog
from interface.backend.repositories.ddi_repo import list_sources
from interface.backend.schemas.assistant import AssistantRequest, AssistantResponse
from interface.backend.schemas.ddi import Citation, FindingOut
from interface.backend.services.assistant_external import explicit_drug_name, extract_drug_names, label_reply
from interface.backend.services.assistant_intent import abusive_message, classify_question, rule_route
from interface.backend.services.assistant_llm import PRIVATE, explain
from interface.backend.services.assistant_local_labels import local_label_reply
from interface.backend.services.assistant_nutrition import nutrition_reply
from interface.backend.services.assistant_situations import requests_treatment, social_reply
from interface.backend.services.assistant_usage import UsageMeter, active_usage
from interface.backend.services.progress import report
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
    meter = UsageMeter()
    context = active_usage.set(meter)
    try:
        result = await _answer(db, request)
        result.usage = meter.summary()
        return result
    finally:
        active_usage.reset(context)


async def _answer(db: AsyncSession, request: AssistantRequest) -> AssistantResponse:
    def response(text: str, status: str, **kwargs):
        if request.detail == "brief":
            # Keep two complete content sentences; handoff is the third sentence.
            text = "\n\n".join(re.split(r"(?<=[.!?])\s+", text.strip())[:2])
            if text and text[-1] not in ".!?":
                text += "."
            critical = []
            for note in kwargs.get("limitations", []):
                if note.startswith("Tên chưa được xác minh"):
                    critical.append(note.split(". ", 1)[0])
                elif note.startswith("Lần kiểm tra đã lưu chưa tìm thấy"):
                    pairs = note.split(": ", 1)[1].split(". ", 1)[0]
                    critical.append(f"Chưa có bản ghi tương tác cho: {pairs}; thiếu bản ghi không chứng minh phối hợp an toàn")
            if any(c.source_id == "openfda" for c in kwargs.get("citations", [])):
                critical.append("Thông tin nhãn không xác nhận mức độ tương tác của cặp thuốc; thiếu dữ liệu không chứng minh phối hợp an toàn")
            if critical:
                first = re.split(r"(?<=[.!?])\s+", text.strip())[0]
                text = first + "\n\n" + "; ".join(critical).rstrip(".") + "."
            handoff = "Liên hệ bác sĩ/dược sĩ để được đánh giá."
        else:
            handoff = HANDOFF
        return AssistantResponse(reply=f"{text}\n\n{handoff}", status=status,
                                 disclaimer=DISCLAIMER, **kwargs)

    message = folded(request.message)
    def unsafe(text):
        return bool(PRIVATE.search(folded(text)) or UNTRUSTED_INSTRUCTION.search(folded(text)))

    routed_names = []
    explicit_lookup = bool(explicit_drug_name(request.message))

    async def external_answer(names, check_id=""):
        if explicit_lookup:
            text, cites, found = await local_label_reply(db, names, request.message, unsafe, request.detail)
            if text:
                # Preserve section breaks and translation notices even in brief mode.
                return AssistantResponse(reply=f"{text}\n\n{HANDOFF if request.detail == 'expanded' else 'Liên hệ bác sĩ/dược sĩ để được đánh giá.'}",
                                         status="answered" if found else "no_evidence", citations=cites, check_id=check_id,
                                         disclaimer=DISCLAIMER,
                                         limitations=["Thông tin nhãn thuốc trong CSDL; không thay đổi kết quả kiểm tra tương tác."])
        # Catalog membership is not evidence for a general label question.
        # Explicit single-drug lookups must not fall back to unrelated RX pairs.
        absent = [name for name in names if not unsafe(name)
                  and (explicit_lookup or not await drug_in_catalog(db, name))]
        if not absent:
            return None
        report("label_lookup")
        text, cites, found = await label_reply(absent, request.message, unsafe, detail=request.detail)
        if not text:
            if explicit_lookup:
                return response("Hiện chưa thể tra cứu thông tin nhãn thuốc: chức năng tra cứu nguồn ngoài chưa khả dụng.",
                                "no_evidence", check_id=check_id)
            return None
        return response(text, "answered" if found else "no_evidence", citations=cites,
                        check_id=check_id, limitations=[
                            "Tra cứu nhãn thuốc bên ngoài; không bổ sung hoặc thay đổi kết quả kiểm tra tương tác."])

    if UNTRUSTED_INSTRUCTION.search(message):
        return response("Tôi chỉ giải thích bằng chứng tương tác thuốc đã được backend xác minh.",
                        "out_of_scope")
    if abusive_message(request.message):
        return AssistantResponse(reply="Tôi có thể hỗ trợ câu hỏi về thuốc. Bạn vui lòng diễn đạt lại câu hỏi một cách tôn trọng để tôi tiếp tục hỗ trợ.",
                                 status="out_of_scope", disclaimer=DISCLAIMER)
    small_talk = social_reply(request.message)
    if small_talk:
        return AssistantResponse(reply=small_talk, status="answered", disclaimer=DISCLAIMER)
    if requests_treatment(request.message):
        return response("Tôi không đưa ra chẩn đoán hoặc chỉ định điều trị, liều dùng hay thay đổi thuốc. "
                        "Tôi có thể giúp bạn hiểu bằng chứng tương tác để trao đổi với bác sĩ/dược sĩ.",
                        "out_of_scope")
    report("routing")
    decision = await classify_question(request.message, [turn.model_dump() for turn in request.history], unsafe)
    if decision.moderation != "allowed":
        return AssistantResponse(reply="Tôi không xử lý lời công kích hoặc yêu cầu vượt quy tắc. Bạn vui lòng đặt lại câu hỏi về thuốc một cách tôn trọng.",
                                 status="out_of_scope", disclaimer=DISCLAIMER)
    if decision.intent == "nutrition":
        food_answer = nutrition_reply(request.message, [turn.model_dump() for turn in request.history], request.detail)
        if food_answer:
            return food_answer
        return AssistantResponse(reply="Bạn muốn biết thực phẩm nào cung cấp vitamin hoặc khoáng chất nào? Hãy nêu chất dinh dưỡng bạn muốn tìm hiểu.",
                                 status="needs_clarification", disclaimer=DISCLAIMER)
    if decision.intent in {"out_of_scope", "treatment"}:
        return response("Tôi chỉ hỗ trợ tra cứu thuốc, giải thích bằng chứng tương tác và nguồn thực phẩm cung cấp chất dinh dưỡng. Tôi không chẩn đoán, kê đơn hoặc chỉ định thay đổi thuốc hay liều dùng.",
                        "out_of_scope")
    if decision.intent == "unclear":
        return AssistantResponse(reply="Bạn muốn tra cứu thông tin thuốc, hỏi tương tác, giải thích kết quả hay tìm thực phẩm cung cấp chất dinh dưỡng? Hãy cho biết tên thuốc, chất dinh dưỡng hoặc điểm bạn muốn làm rõ.",
                                 status="needs_clarification", disclaimer=DISCLAIMER)
    routed_names = decision.drug_names
    if decision.intent == "follow_up":
        # References select an existing user's subject, never reuse assistant facts as evidence.
        for turn in reversed(request.history):
            if turn.role == "user":
                previous = rule_route(turn.content, [])
                if previous.intent == "drug_lookup":
                    routed_names = routed_names or previous.drug_names
                    decision.intent = "drug_lookup"
                break
    explicit_lookup = decision.intent == "drug_lookup" and bool(routed_names)
    if not request.prescription_id or request.prescription_id == "chưa chọn":
        names = routed_names or await extract_drug_names(request.message, unsafe)
        if names and (external := await external_answer(names)):
            return external
        return response("Hãy chọn đơn thuốc và chạy kiểm tra để tôi có bằng chứng để giải thích.",
                        "needs_clarification")
    report("context")
    prescription, check, medications = await assistant_context(
        db, request.prescription_id, request.check_id)
    if prescription is None:
        raise HTTPException(404, "Không tìm thấy đơn thuốc")
    if request.check_id and (check is None or check.prescription_id != prescription.id):
        raise HTTPException(422, "Kết quả kiểm tra không thuộc đơn thuốc")
    names = routed_names or await extract_drug_names(request.message, unsafe, known_names=[m.name for m in medications])
    if check is None and names and (external := await external_answer(names)):
        return external
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
    if names and (external := await external_answer(names, check.id)):
        return external
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
        recommendation = finding.management or finding.original_management
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
        relevant_names = [name for name in names if folded(name) in message]
        drug_question = any(term in message for term in (
            "thuoc", "tuong tac", "tac dung", "chong chi dinh", "canh bao", "dung chung", "ket hop"))
        if relevant_names or (not findings and drug_question):
            absent = [name for name in (relevant_names or names)
                      if not await drug_in_catalog(db, name)]
            if absent:
                report("label_lookup")
            external_text, external_cites, external_found = await label_reply(
                absent, request.message, unsafe, detail=request.detail)
        else:
            external_text, external_cites, external_found = "", [], False
    else:
        external_text, external_cites, external_found = "", [], False
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
            history=[turn.model_dump() for turn in request.history], food_pairs=food_pairs, detail=request.detail)
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
    if external_text:
        if not findings:
            lines = [external_text]
        else:
            lines.append(external_text)
        citations.extend(c for c in external_cites if c not in citations)
    if request.detail == "expanded":
        lines.extend(note for note in dict.fromkeys(limitations)
                 if not llm_used or note != "Kết quả dựa trên lần kiểm tra đã lưu; không bao gồm thuốc ngoài đơn này.")
    status = "answered" if llm_used else "no_evidence"
    if (unknown and not llm_used) or fallback_reason in {"no_supported_answer", "ambiguous_question", "irrelevant_answer"}:
        status = "needs_clarification"
    if fallback_reason in {"out_of_scope_question", "treatment_request"}:
        status = "out_of_scope"
    elif external_text and not findings:
        status = "answered" if external_found else "no_evidence"
    return response("\n\n".join(lines), status,
                    check_id=check.id,
                    findings=findings, citations=citations,
                    llm_used=llm_used, fallback_reason=fallback_reason,
                    limitations=list(dict.fromkeys(limitations)))
