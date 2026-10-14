"""Prefer stored, hash-validated Vietnamese label translations over live API."""
import re
from uuid import UUID

from interface.backend.repositories.assistant import localized_drug_labels
from interface.backend.schemas.ddi import Citation
from interface.backend.services.assistant_situations import normalized
from interface.backend.services.assistant_translation import vietnamese_excerpt

HEADINGS = {"boxed_warning": "Cảnh báo quan trọng", "contraindications": "Chống chỉ định",
            "drug_interactions": "Thông tin tương tác theo nhãn", "do_not_use": "Cảnh báo không sử dụng",
            "ask_doctor_or_pharmacist": "Lưu ý trao đổi với bác sĩ/dược sĩ"}


async def local_label_reply(db, names, message, unsafe, detail):
    query = normalized(message)
    # Local table does not store indications or adverse_reactions. Do not replace
    # these questions with unrelated contraindications or interaction evidence.
    if any(term in query for term in ("tac dung gi", "cong dung", "tac dung phu")):
        return "", [], False
    requested = (["drug_interactions"] if any(t in query for t in ("tuong tac", "dung chung", "ket hop"))
                 else ["contraindications"] if "chong chi dinh" in query else list(HEADINGS))
    lines, citations = [], []
    found = False
    for name in list(dict.fromkeys(names))[:3]:
        if unsafe(name):
            continue
        for row in await localized_drug_labels(db, name):
            available = [key for key in requested if row.get(key) and not unsafe(row[key])]
            if not available:
                continue
            try:
                set_id = str(UUID(row["id"]))
            except ValueError:
                continue
            missing = set(row["untranslated_fields"])
            # Prefer already translated sections for a general lookup.
            if len(requested) > 1:
                available.sort(key=lambda key: key in missing)
            available = available[:1 if detail == "brief" else 3]
            texts = {}
            generated = False
            for key in available:
                source = re.sub(r"<[^>]*>", " ", row[key]).strip()[:1600]
                if key in missing:
                    text = await vietnamese_excerpt(source, unsafe)
                    generated = generated or bool(text)
                else:
                    text = source
                if text:
                    texts[key] = text
            available = list(texts)
            title = f"{name} — nhãn thuốc trong CSDL"
            lines.append(title)
            for key in available:
                text = texts[key]
                limit = 280 if detail == "brief" else 1600
                if len(text) > limit:
                    text = text[:limit].rsplit(" ", 1)[0] + "… [trích đoạn]"
                lines.append(f"{HEADINGS[key]}:\n{text}")
            if not available:
                lines.append("Hiện chưa có bản dịch tiếng Việt đã kiểm chứng cho phần nhãn thuốc này. Vui lòng thử lại sau.")
            else:
                found = True
            if available and (generated or row["machine_translation"]):
                lines.append("Nội dung dùng bản dịch máy; cần đối chiếu nguồn gốc khi đánh giá." if generated else
                             "Nội dung dùng bản dịch máy đã lưu; cần đối chiếu nguồn gốc khi đánh giá.")
            citations.append(Citation(source_id="openfda", source_name="FDA Labels — dữ liệu trong CSDL",
                                      label=f"Nhãn thuốc {name}",
                                      source_url=f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"))
            break
    if not citations:
        return "", [], False
    lines.append("Thông tin nhãn không xác nhận mức độ tương tác của cặp thuốc; thiếu dữ liệu không chứng minh phối hợp an toàn.")
    return "\n\n".join(lines), citations, found
