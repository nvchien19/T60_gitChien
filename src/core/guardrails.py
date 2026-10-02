"""Guardrails rule-based (W5): chan khuyen thuoc, chan 'an toan' khi no_record,
bat buoc citation. Khong LLM."""

import re

BANNED_ADVICE = re.compile(
    r"ngưng|dừng|bỏ thuốc|đổi sang|tăng liều|giảm liều|nên dùng|kê cho|kê đơn",
    re.IGNORECASE,
)
BANNED_SAFE = re.compile(r"an toàn|không sao|không nguy hiểm", re.IGNORECASE)

# Hai hằng dưới đây KHÔNG được chứa từ nào khớp BANNED_ADVICE. `sanitize_text`
# thay thế bằng HANDOFF rồi lọc lại toàn bộ text, nếu HANDOFF tự chứa từ cấm
# (ngưng/đổi/giảm liều) thì lượt lọc sau sẽ khớp chính chuỗi vừa chèn -> lặp.
NO_RECORD_MSG = "Chưa có bản ghi trong CSDL — chưa đủ căn cứ để kết luận."
HANDOFF = "Liên hệ bác sĩ/dược sĩ để được đánh giá. Mọi thay đổi về liệu trình cần theo chỉ định của bác sĩ."
DISCLAIMER = (
    "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. "
    "Liên hệ bác sĩ/dược sĩ để được đánh giá. Mức nghiêm trọng cao cần liên hệ y tế ngay."
)


def sanitize_text(text: str, is_no_record: bool = False) -> str:
    if not text:
        return text
    t = BANNED_ADVICE.sub(HANDOFF, text)
    if is_no_record:
        t = BANNED_SAFE.sub("chưa có bản ghi trong CSDL", t)
    return t


def guardrail_assert(findings: list[dict]) -> list[dict]:
    """Bo finding thieu source_id (log) + sanitize text. Tra ve findings sach."""
    clean = []
    for f in findings:
        cites = f.get("citations") or []
        if not cites or not any(c.get("source_id") for c in cites):
            continue  # thieu citation = khong tra (log o caller)
        no_rec = f.get("match_type") == "no_record"
        for k in ("summary", "mechanism", "management"):
            if isinstance(f.get(k), str):
                f[k] = sanitize_text(f[k], is_no_record=no_rec)
        clean.append(f)
    return clean
