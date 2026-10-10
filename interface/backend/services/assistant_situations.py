"""Non-medical conversation replies; exact whole-message matches only.

Mixed greetings/questions must continue to the evidence flow. No database reads,
model calls, sensitive-data reflection or medical facts are needed for small talk.
"""
import re
import unicodedata


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9\s]", " ", text).strip()


def social_reply(text: str) -> str | None:
    text = re.sub(r"\s+", " ", normalized(text))
    greeting = r"(?:xin chao|chao|hello|hi|hey|alo)(?:\s+(?:ban|bot|tro ly|a|nhe|bac si|duoc si))*"
    thanks = r"(?:cam on|thank you|thanks|thank u)(?:\s+(?:ban|bot|tro ly|a|nhe|rat nhieu))*"
    goodbye = r"(?:tam biet|chao tam biet|bye|goodbye|hen gap lai)(?:\s+(?:ban|a|nhe))*"
    if re.fullmatch(greeting, text):
        return "Xin chào! Tôi là trợ lý hỗ trợ giải thích tương tác thuốc. Bạn muốn tôi giúp điều gì?"
    if re.fullmatch(thanks, text):
        return "Rất vui được hỗ trợ bạn. Nếu còn điểm nào chưa rõ, bạn cứ hỏi nhé."
    if re.fullmatch(goodbye, text):
        return "Tạm biệt bạn! Khi cần giải thích thêm về tương tác thuốc, bạn có thể quay lại đây."
    if text in {"ok", "oke", "okay", "duoc roi", "hieu roi", "da hieu", "ro roi", "vang", "da"}:
        return "Vâng. Nếu bạn muốn làm rõ thêm điều gì, tôi sẵn sàng hỗ trợ."
    if text in {"ban la ai", "ban co the lam gi", "ban giup duoc gi", "huong dan", "help", "giup toi"}:
        return ("Tôi có thể giúp bạn hiểu cơ chế, mức độ và nguồn bằng chứng của tương tác thuốc, "
                "hoặc chuẩn bị câu hỏi cho bác sĩ/dược sĩ. Bạn muốn hỏi về cặp thuốc hay kết quả nào?")
    return None


def requests_treatment(text: str) -> bool:
    text = normalized(text)
    return bool(re.search(
        r"\b(?:lieu nao|lieu bao nhieu|ke don cho|ke thuoc cho)\b|"
        r"\b(?:toi|minh)\s+(?:co\s+)?(?:nen|can|phai)\s+"
        r"(?:ngung|ngun?g|dung|uong|doi|tang|giam|bo)\b|"
        r"\b(?:hay|giup toi)\s+(?:ke don|ke thuoc|doi thuoc|tang lieu|giam lieu)\b", text))
