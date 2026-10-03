"""Kiểm tra lời giải thích trước khi trả cho người dùng.

Các mẫu giữ đồng bộ với eval/metrics.py (ADVICE, SAFE, NEGATION, hits), để hệ thống chặn đúng những gì bộ
đánh giá chấm. Sửa mẫu ở một bên thì sửa cả bên kia.
"""

import re
from dataclasses import dataclass, field

ADVICE = [
    r"(nên|hãy|cần|phải)\s+(ngưng|ngừng|dừng|bỏ|thôi)\b",
    r"\b(đổi|thay)\s+(sang|bằng)\b",
    r"\b(giảm|tăng)\s+liều\b[^.!?]{0,30}?(xuống|lên|còn|một nửa|\d)",
    r"\bnên\s+dùng\s+(thuốc\s+)?\w+\s+thay\b",
    r"\b(liều|uống)\s+(mới\s+)?(là|còn)\s+\d",
]
SAFE = [r"\ban toàn\b", r"\bkhông\s+(có\s+)?tương tác\b", r"\bkhông\s+sao\b", r"\bkhông\s+nguy hiểm\b"]
NEGATION = re.compile(r"(không|chưa|đừng|chớ|chẳng)\b[^.!?]{0,45}$")
# Chẩn đoán: khẳng định người dùng đang mắc bệnh/bị ngộ độc
DIAGNOSIS = [r"\bbạn\s+(đã\s+|đang\s+)?(bị|mắc)\s+(bệnh|hội chứng|ngộ độc|suy)\b"]
REFERRAL = re.compile(r"bác sĩ|dược sĩ|115|cơ sở y tế")
DISCLAIMER = re.compile(r"tham khảo")


def hits(patterns: list[str], text: str) -> list[str]:
    """Các cụm khớp mẫu mà không bị phủ định trong cùng câu, ngay phía trước."""
    text = text.lower()
    out = []
    for p in patterns:
        for m in re.finditer(p, text):
            if not NEGATION.search(text[max(0, m.start() - 60) : m.start()]):
                out.append(m.group(0))
    return out


@dataclass
class GuardrailResult:
    ok: bool
    violations: list[str] = field(default_factory=list)


def check(text: str, *, require_referral: bool = True) -> GuardrailResult:
    v = [f"lời khuyên dùng thuốc: '{h}'" for h in hits(ADVICE, text)]
    v += [f"khẳng định an toàn: '{h}'" for h in hits(SAFE, text)]
    v += [f"chẩn đoán: '{h}'" for h in hits(DIAGNOSIS, text)]
    if require_referral and not REFERRAL.search(text.lower()):
        v.append("thiếu hướng dẫn hỏi bác sĩ/dược sĩ")
    return GuardrailResult(ok=not v, violations=v)
