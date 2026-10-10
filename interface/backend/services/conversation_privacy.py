"""Local redaction before any conversational text crosses the provider boundary.

Pattern-based redaction is a supplementary control, not a universal PII detector.
Do not log the input or removed spans. History never becomes medical evidence.
"""
import re

from interface.backend.config import get_settings

CONTACT = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?:\+?84|0)[\s.-]*\d(?:[\s.-]*\d){8,10}\b", re.I)
IDENTIFIER = re.compile(r"\b(?:RX|CHECK)-[\w-]+\b|\b\d{9,12}\b|\bsk-[\w-]+\b", re.I)
URL = re.compile(r"(?:https?://|postgres(?:ql)?://|sqlite://)\S+", re.I)
LABELLED = re.compile(
    r"(?:tôi\s+(?:tên(?:\s+là)?|là)|tên\s+(?:tôi|bệnh nhân)|họ\s*tên|"
    r"my\s+name\s+is|patient\s*name|địa\s*chỉ|address|ngày\s*sinh|date\s*of\s*birth|"
    r"cccd|cmnd|password|mật\s*khẩu|api[_ -]?key|bearer|token|email|điện\s*thoại)"
    r"\s*[:=]?\s*[^,;\n.!?]*", re.I,
)
PERSONAL = re.compile(
    r"\b(?:tôi|bệnh\s+nhân|patient|my)\s+(?:đang\s+)?(?:bị|mắc|sống|ở|sinh|\d+\s*tuổi)"
    r"[^,;\n.!?]*", re.I,
)
PERSON_NAME = re.compile(r"\b(?:Nguyễn|Nguyen|Trần|Tran|Lê|Le|Phạm|Pham|Hoàng|Hoang|"
                         r"Huỳnh|Huynh|Vũ|Vu|Võ|Vo|Đặng|Dang|Bùi|Bui|Đỗ|Do|Hồ|Ho)"
                         r"(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,4}(?:\s+[A-Z])?\b")


def sanitize_conversation(text: str, drug_names: list[str]) -> str:
    # Preserve known medicine names while removing person names that resemble them.
    medicines = {}
    for index, name in enumerate(sorted(set(drug_names), key=len, reverse=True)):
        placeholder = f"MEDICINEPLACEHOLDER{index}"
        medicines[placeholder] = name
        text = re.sub(re.escape(name), placeholder, text, flags=re.I)
    settings = get_settings()
    for key, value in settings.model_dump().items():
        if isinstance(value, str) and len(value) >= 6 and (key.endswith("_key") or key == "database_url"):
            text = text.replace(value, "[đã ẩn]")
    text = LABELLED.sub("[đã ẩn thông tin cá nhân]", text)
    text = PERSONAL.sub("[đã ẩn thông tin cá nhân]", text)
    text = PERSON_NAME.sub("[đã ẩn tên]", text)
    text = CONTACT.sub("[đã ẩn liên hệ]", text)
    text = IDENTIFIER.sub("[đã ẩn mã]", text)
    text = URL.sub("[đã ẩn liên kết]", text)
    for placeholder, name in medicines.items():
        text = text.replace(placeholder, name)
    return text.strip()[:3000]
