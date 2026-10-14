"""Curated food-source facts, independent of prescriptions and model availability.

Vietnamese summaries were checked against the linked NIH ODS fact sheets on
2026-10-13. This catalog answers food-source questions only; absent foods are
not evidence of zero nutrient content. User text never becomes evidence.
"""
import re
from dataclasses import dataclass

from interface.backend.schemas.assistant import AssistantResponse
from interface.backend.schemas.ddi import Citation
from interface.backend.services.assistant_situations import normalized

DISCLAIMER = "Thông tin dinh dưỡng phổ thông; không thay thế tư vấn dinh dưỡng hoặc chỉ định y khoa cho từng người."


@dataclass(frozen=True)
class Food:
    label: str
    kind: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Topic:
    label: str
    aliases: tuple[str, ...]
    source: str
    foods: tuple[str, ...]
    note: str = ""


def food(label: str, kind: str, *aliases: str) -> Food:
    return Food(label, kind, tuple(normalized(value) for value in (label, *aliases)))


FOODS = {
    "spinach": food("cải bó xôi", "vegetable", "rau bina", "rau chân vịt", "spinach"),
    "kale": food("cải xoăn", "vegetable", "kale"),
    "broccoli": food("bông cải xanh", "vegetable", "súp lơ xanh", "broccoli"),
    "lettuce": food("xà lách", "vegetable"),
    "asparagus": food("măng tây", "vegetable"),
    "carrot": food("cà rốt", "vegetable"),
    "sweet_potato": food("khoai lang", "vegetable"),
    "potato": food("khoai tây", "vegetable"),
    "pepper": food("ớt chuông", "vegetable"),
    "tomato": food("cà chua", "vegetable"),
    "orange": food("cam", "fruit"),
    "kiwi": food("kiwi", "fruit"),
    "strawberry": food("dâu tây", "fruit"),
    "mango": food("xoài", "fruit"),
    "banana": food("chuối", "fruit"),
    "raisin": food("nho khô", "fruit"),
    "milk": food("sữa", "dairy", "sữa bò"),
    "yogurt": food("sữa chua", "dairy", "yogurt"),
    "cheese": food("phô mai", "dairy", "pho mát", "phô mát", "cheese"),
    "egg": food("trứng", "animal"),
    "egg_yolk": food("lòng đỏ trứng", "animal"),
    "beef_liver": food("gan bò", "animal"),
    "poultry": food("thịt gia cầm", "animal", "thịt gà", "thịt vịt"),
    "lean_meat": food("thịt nạc", "animal"),
    "fish": food("cá", "seafood"),
    "salmon": food("cá hồi", "seafood"),
    "mackerel": food("cá thu", "seafood"),
    "tuna": food("cá ngừ", "seafood"),
    "herring": food("cá trích", "seafood"),
    "sardine": food("cá mòi", "seafood"),
    "oyster": food("hàu", "seafood"),
    "clam": food("nghêu", "seafood", "ngao"),
    "shrimp": food("tôm", "seafood"),
    "canned_bones": food("cá mòi hoặc cá hồi đóng hộp ăn cả xương", "seafood"),
    "beans": food("các loại đậu", "legume", "đậu trắng", "đậu đỏ", "đậu hà lan"),
    "lentil": food("đậu lăng", "legume"),
    "soybean": food("đậu nành", "legume", "đậu tương"),
    "natto": food("natto (đậu nành lên men)", "legume", "natto", "đậu nành lên men"),
    "almond": food("hạnh nhân", "nut"),
    "peanut": food("lạc", "nut", "đậu phộng"),
    "sunflower_seed": food("hạt hướng dương", "nut"),
    "walnut": food("quả óc chó", "nut", "óc chó"),
    "flaxseed": food("hạt lanh", "nut"),
    "chia": food("hạt chia", "nut"),
    "nuts": food("các loại hạt", "nut"),
    "whole_grain": food("ngũ cốc nguyên hạt", "grain"),
    "soy_oil": food("dầu đậu nành", "oil"),
    "canola_oil": food("dầu cải", "oil", "dầu canola"),
    "sunflower_oil": food("dầu hướng dương", "oil"),
    "wheatgerm_oil": food("dầu mầm lúa mì", "oil"),
    "flax_oil": food("dầu hạt lanh", "oil"),
    "seaweed": food("rong biển", "vegetable"),
    "iodized_salt": food("muối có bổ sung i-ốt", "other", "muối i ốt", "muối iod"),
    "fortified_d": food("sữa hoặc ngũ cốc có bổ sung vitamin D", "fortified"),
    "fortified_calcium": food("đồ uống thực vật hoặc đậu phụ có bổ sung canxi", "fortified"),
    "fortified_b12": food("ngũ cốc hoặc men dinh dưỡng có bổ sung vitamin B12", "fortified"),
    "fortified_folate": food("ngũ cốc hoặc bánh mì có bổ sung axit folic", "fortified"),
    "fortified_iron": food("ngũ cốc có bổ sung sắt", "fortified"),
}

K_NOTE = ("NIH lưu ý người dùng warfarin cần giữ lượng vitamin K ăn vào ổn định; "
          "việc thay đổi chế độ ăn cần trao đổi với bác sĩ/dược sĩ.")
TOPICS = {
    "k": Topic("vitamin K", ("vitamin k", "vit k"), "VitaminK-HealthProfessional",
               ("spinach", "kale", "broccoli", "soy_oil", "canola_oil", "natto"), K_NOTE),
    "k1": Topic("vitamin K1", ("vitamin k1", "vit k1", "k1"), "VitaminK-HealthProfessional",
                ("spinach", "kale", "broccoli", "soy_oil", "canola_oil"), K_NOTE),
    "k2": Topic("vitamin K2", ("vitamin k2", "vit k2", "k2"), "VitaminK-HealthProfessional",
                ("natto", "cheese", "egg"), "Natto chứa nhiều K2; hàm lượng trong các thực phẩm lên men khác có thể thay đổi. " + K_NOTE),
    "a": Topic("vitamin A", ("vitamin a", "vit a"), "VitaminA-Consumer",
               ("carrot", "sweet_potato", "spinach", "mango", "egg", "milk", "cheese")),
    "c": Topic("vitamin C", ("vitamin c", "vit c"), "VitaminC-Consumer",
               ("orange", "kiwi", "pepper", "strawberry", "broccoli", "tomato"),
               "Bảo quản lâu và nấu nướng có thể làm giảm lượng vitamin C trong thực phẩm."),
    "d": Topic("vitamin D", ("vitamin d", "vit d"), "VitaminD-Consumer",
               ("salmon", "mackerel", "tuna", "egg_yolk", "fortified_d"),
               "Lòng đỏ trứng chỉ có lượng nhỏ; sữa và ngũ cốc chỉ thuộc nhóm tăng cường vitamin D khi nhãn ghi có bổ sung."),
    "e": Topic("vitamin E", ("vitamin e", "vit e"), "VitaminE-Consumer",
               ("almond", "peanut", "sunflower_seed", "sunflower_oil", "wheatgerm_oil", "spinach")),
    "b6": Topic("vitamin B6", ("vitamin b6", "vit b6", "b6"), "VitaminB6-Consumer",
                ("poultry", "fish", "potato")),
    "b9": Topic("folate (vitamin B9)", ("vitamin b9", "b9", "folate", "folat", "axit folic", "acid folic"),
                "Folate-Consumer", ("asparagus", "spinach", "orange", "beans", "peanut", "fortified_folate"),
                "Folate có tự nhiên trong thực phẩm; axit folic là dạng được bổ sung vào một số thực phẩm."),
    "b12": Topic("vitamin B12", ("vitamin b12", "vit b12", "b12"), "VitaminB12-Consumer",
                 ("fish", "poultry", "egg", "milk", "yogurt", "cheese", "clam", "oyster", "fortified_b12"),
                 "Thực phẩm thực vật không có B12 tự nhiên; sản phẩm tăng cường B12 cần được xác nhận trên nhãn."),
    "calcium": Topic("canxi", ("canxi", "calci", "calcium"), "Calcium-Consumer",
                     ("milk", "yogurt", "cheese", "canned_bones", "kale", "broccoli", "fortified_calcium"),
                     "Đậu phụ và đồ uống thực vật chỉ được xem là nguồn bổ sung canxi khi nhãn sản phẩm xác nhận có canxi."),
    "iron": Topic("sắt", ("sat", "iron"), "Iron-Consumer",
                  ("lean_meat", "poultry", "lentil", "beans", "spinach", "raisin", "fortified_iron"),
                  "Vitamin C hỗ trợ hấp thu sắt từ thực phẩm thực vật."),
    "potassium": Topic("kali", ("kali", "potassium"), "Potassium-Consumer",
                       ("banana", "potato", "spinach", "tomato", "lentil", "soybean", "yogurt")),
    "magnesium": Topic("magiê", ("magie", "magi e", "magnesium"), "Magnesium-Consumer",
                       ("beans", "nuts", "whole_grain", "spinach", "milk", "yogurt")),
    "zinc": Topic("kẽm", ("kem", "zinc"), "Zinc-Consumer",
                  ("oyster", "lean_meat", "fish", "poultry", "beans", "nuts", "egg"),
                  "Hàu là nguồn có hàm lượng kẽm cao; đậu, hạt và trứng cũng cung cấp một phần kẽm."),
    "iodine": Topic("i-ốt", ("i ot", "iot", "iod", "iodine"), "Iodine-Consumer",
                    ("fish", "shrimp", "seaweed", "milk", "yogurt", "egg", "iodized_salt"),
                    "Muối biển và muối đặc sản không mặc nhiên có bổ sung i-ốt; cần kiểm tra nhãn."),
    "omega3": Topic("omega-3", ("omega 3", "omega3"), "Omega3FattyAcids-Consumer",
                    ("salmon", "mackerel", "herring", "sardine", "walnut", "flaxseed", "chia", "flax_oil"),
                    "Cá cung cấp EPA/DHA; hạt và dầu thực vật cung cấp chủ yếu ALA, một dạng omega-3 khác."),
}

MEDICINE_CONTEXT = re.compile(
    r"\b(?:thuoc|tuong tac|dung chung|ket hop|phoi hop|chong chi dinh|warfarin|coumadin|"
    r"aspirin|metformin|khong duoc dung|luu y khi uong|uong cung|uong kem|tac dung phu|"
    r"thuc pham chuc nang|vien uong|an toan|co duoc|duoc khong|anh huong)\b|"
    r"\b(?:toi|minh)\s+(?:dang\s+)?(?:dung|uong)\b"
)
FOOD_CUE = re.compile(r"\b(?:thuc pham|thuc an|dinh duong|an gi|food|foods|giau|co trong|nguon thuc vat|rau|trai cay|hoa qua)\b")
NUTRIENT_CUE = re.compile(r"\b(?:vitamin|vit|khoang chat|duong chat|omega|protein|chat xo|canxi|kali|sat|kem|magie|folate|iot|i ot)\b")
FOLLOW_UP = re.compile(r"^(?:con|vay|the|rau nao|trai cay nao|loai nao|ke them|cho vi du|noi ro hon|giai thich them)\b")
SOURCE_QUESTION = re.compile(r"\b(?:thuc pham|thuc an|an gi|giau|co trong|chua|cung cap|nguon|rau nao|trai cay nao|hoa qua|bao gom|ke them|cho vi du)\b")
UNSUPPORTED = re.compile(
    r"\b(?:bao nhieu|ham luong|mg|mcg|gram|calo|kcal|nhieu nhat|it nhat|tot nhat|so sanh|"
    r"khong co|khong chua|co phai|chi co|tranh|han che|bo sung|trieu chung|thieu chat|thieu vitamin|"
    r"vi sao|tai sao|loi ich|co che)\b|\b(?:nhieu|it|cao|thap|tot)\b.{0,80}\bnhat\b"
)
PERSONAL_DIET = re.compile(
    r"\b(?:benh|suy than|tieu duong|dai thao duong|tang huyet ap|ung thu|mang thai|bau|"
    r"tre em|em be|di ung|chan doan|chua benh|dieu tri|giam can|tang can|thuc don|ke hoach)\b"
)


def contains(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def named_foods(text: str) -> list[str]:
    matches = [(key, match.start(), match.end()) for key, item in FOODS.items() for alias in item.aliases
               for match in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text)]
    # Keep the most specific phrase at each location, without erasing a separate
    # mention elsewhere (e.g. 'sữa và sữa chua').
    return list(dict.fromkeys(key for key, start, end in matches if not any(
        other_start <= start and other_end >= end and other_end - other_start > end - start
        for _, other_start, other_end in matches)))


def topic_keys(text: str) -> list[str]:
    keys = [key for key, topic in TOPICS.items() if any(contains(text, alias) for alias in topic.aliases)]
    # 'vitamin C và D' shares the vitamin prefix; do not silently drop D.
    for match in re.finditer(r"\b(?:vitamin|vit)\s+[a-z][0-9]*(?:\s+(?:(?:va|hoac)\s+)?(?:vitamin\s+)?[a-z][0-9]*)*\b", text):
        for token in match[0].split():
            if token in TOPICS and token not in keys:
                keys.append(token)
    # Folded 'kem' also means ice cream; only treat it as zinc in nutrient-source grammar.
    if "zinc" in keys and not (contains(text, "zinc") or re.search(
            r"\b(?:giau|co|chua|cung cap|nguon|khoang chat|con) kem\b|\bkem (?:co trong|tu|trong thuc pham)\b", text)):
        keys.remove("zinc")
    return keys


def vitamin_codes(text: str) -> list[str]:
    codes = []
    for match in re.finditer(r"\b(?:vitamin|vit)\s+[a-z][0-9]*(?:\s+(?:(?:va|hoac)\s+)?(?:vitamin\s+)?[a-z][0-9]*)*\b", text):
        codes.extend(token for token in match[0].split() if re.fullmatch(r"[a-z][0-9]*", token))
    return codes


def previous_nutrition(history: list[dict]) -> str:
    # Resolve consecutive user follow-ups, resetting at an unrelated user's subject.
    # Assistant replies can never supply evidence or choose a new nutrient.
    context = ""
    for turn in history:
        if turn["role"] == "user":
            text = normalized(turn["content"])
            if direct_nutrition(text):
                context = text
            elif context and not MEDICINE_CONTEXT.search(text) and (FOLLOW_UP.search(text) or topic_keys(text)):
                keys = topic_keys(text) or topic_keys(context)
                personal = " benh" if PERSONAL_DIET.search(context) else ""
                plant = " nguon thuc vat" if re.search(r"\b(?:nguon thuc vat|tu thuc vat|an chay|thuan chay)\b", context) else ""
                context = "thuc pham cung cap " + " va ".join(normalized(TOPICS[key].label) for key in keys) + personal + plant
            else:
                context = ""
    return context


def direct_nutrition(text: str) -> bool:
    if MEDICINE_CONTEXT.search(text):
        return False
    presence = re.search(r"\b(?:co|chua|cung cap)\b.*\b(?:vitamin|canxi|kali|sat|kem|magie|omega)\b.*\bkhong\b", text)
    return bool((FOOD_CUE.search(text) or named_foods(text) or presence)
                and (topic_keys(text) or NUTRIENT_CUE.search(text)))


def is_nutrition_question(message: str, history: list[dict]) -> bool:
    text = normalized(message)
    if MEDICINE_CONTEXT.search(text):
        return False
    if direct_nutrition(text):
        return True
    return bool(previous_nutrition(history) and (FOLLOW_UP.search(text) or topic_keys(text)))


def nutrition_reply(message: str, history: list[dict], detail: str = "brief") -> AssistantResponse | None:
    if not is_nutrition_question(message, history):
        return None
    text = normalized(message)
    prior = previous_nutrition(history)
    if PERSONAL_DIET.search(text) or (FOLLOW_UP.search(text) and PERSONAL_DIET.search(prior)):
        return AssistantResponse(
            reply="Chế độ ăn cho bệnh lý, thai kỳ hoặc trẻ em cần được chuyên gia đánh giá theo từng người. "
                  "Tôi có thể giải thích nguồn thực phẩm cung cấp chất dinh dưỡng; hãy trao đổi với bác sĩ hoặc chuyên gia dinh dưỡng về chế độ ăn cụ thể.",
            status="out_of_scope", disclaimer=DISCLAIMER)
    if UNSUPPORTED.search(text):
        return AssistantResponse(
            reply="Nguồn dinh dưỡng hiện có chưa đủ để xác định hàm lượng, xếp hạng, lượng ăn hoặc giới hạn phù hợp cho câu hỏi này. "
                  "Bạn có thể hỏi những thực phẩm nào cung cấp một vitamin hoặc khoáng chất cụ thể.",
            status="no_evidence", disclaimer=DISCLAIMER)
    keys = topic_keys(text) or topic_keys(prior)
    # Unknown explicit vitamins must not inherit a previous nutrient.
    requested_vitamins = vitamin_codes(text)
    unknown = [name for name in requested_vitamins if name not in TOPICS]
    if unknown or not keys:
        return AssistantResponse(
            reply="Tôi chưa có nguồn thực phẩm đã đối chiếu cho chất dinh dưỡng bạn hỏi. "
                  "Hiện tôi hỗ trợ vitamin A, C, D, E, K/K1/K2, B6, B9, B12; canxi, sắt, kali, magiê, kẽm, i-ốt và omega-3.",
            status="no_evidence", disclaimer=DISCLAIMER)
    presence_question = bool(contains(text, "khong") and re.search(r"\b(?:co|chua|cung cap)\b", text))
    if not SOURCE_QUESTION.search(text) and not presence_question and not (prior and FOLLOW_UP.search(text)):
        return AssistantResponse(
            reply="Bạn muốn biết thực phẩm nào cung cấp chất dinh dưỡng này? Tôi hiện có nguồn để trả lời về thực phẩm cung cấp, "
                  "chưa có dữ liệu đủ cho câu hỏi dinh dưỡng khác.", status="needs_clarification", disclaimer=DISCLAIMER)
    kinds = []
    for pattern, kind in ((r"\brau (?:nao|gi)\b", "vegetable"),
                          (r"\b(?:trai cay|hoa qua) (?:nao|gi)\b", "fruit"),
                          (r"\bhat (?:nao|gi)\b", "nut")):
        if re.search(pattern, text):
            kinds.append(kind)
    mentioned = named_foods(text)
    # Group-list wording asks for sources; an explicit food asks only about that food.
    specific_food = bool((mentioned or contains(text, "khong")) and re.search(r"\b(?:co|chua|cung cap)\b", text)
                         and not re.search(r"\b(?:thuc pham nao|thuc an nao|nhung gi|bao gom|ke ten)\b", text))
    plant_context = text + (" " + prior if FOLLOW_UP.search(text) else "")
    plant_only = bool(re.search(r"\b(?:nguon thuc vat|tu thuc vat|an chay|thuan chay)\b", plant_context))
    plant_kinds = {"vegetable", "fruit", "legume", "nut", "grain", "oil"}
    plant_fortified = {"fortified_b12", "fortified_calcium", "fortified_folate", "fortified_iron"}
    citations, lines = [], []
    for key in keys:
        topic = TOPICS[key]
        selected = [name for name in topic.foods if not kinds or FOODS[name].kind in kinds]
        if plant_only:
            selected = [name for name in selected if FOODS[name].kind in plant_kinds or name in plant_fortified]
        if specific_food:
            selected = [name for name in selected if name in mentioned]
            if not selected or any(name not in topic.foods for name in mentioned):
                lines.append(f"Danh mục hiện có chưa đủ để xác nhận câu hỏi về thực phẩm cụ thể và {topic.label}; "
                             "việc chưa liệt kê không có nghĩa thực phẩm không chứa chất này.")
                continue
        if not selected:
            lines.append(f"Danh mục hiện có chưa liệt kê nhóm thực phẩm bạn yêu cầu cho {topic.label}; "
                         "điều này không có nghĩa nhóm đó không chứa chất này.")
            continue
        source_url = f"https://ods.od.nih.gov/factsheets/{topic.source}/"
        if key == "d":
            source_url = "https://ods.od.nih.gov/pdf/factsheets/VitaminD-Consumer.pdf"
        cite = Citation(source_id=f"nih-ods-{key}", source_name="NIH — Office of Dietary Supplements",
                        label=f"Nguồn thực phẩm cung cấp {topic.label}", source_url=source_url)
        citations.append(cite)
        mark = f"[{len(citations)}]"
        if specific_food:
            lines.append(f"Có, {', '.join(FOODS[name].label for name in selected)} cung cấp {topic.label} {mark}.")
        elif detail == "expanded":
            lines.append(f"Một số nguồn thực phẩm cung cấp {topic.label} {mark}:\n"
                         + "\n".join(f"• {FOODS[name].label}." for name in selected))
        else:
            lines.append(f"Thực phẩm cung cấp {topic.label} gồm {', '.join(FOODS[name].label for name in selected)} {mark}.")
        if topic.note and (detail == "expanded" or key in {"k", "k1", "k2", "d", "b12", "calcium"}):
            lines.append(f"{topic.note} {mark}")
    return AssistantResponse(reply="\n\n".join(lines), status="answered" if citations else "no_evidence",
                             citations=citations, disclaimer=DISCLAIMER,
                             limitations=["Ví dụ thực phẩm từ nguồn công khai đã đối chiếu; danh sách không đầy đủ và không dùng để xác định khẩu phần hay mức độ tương tác thuốc."])
