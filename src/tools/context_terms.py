"""Nhan dien thuc pham / benh nen / dang bao che nguoi dung nhac toi trong cau hoi (ham thuan, khong LLM).

Khoa cua tu dien khop CSDL: `food_interactions.food`, `disease_interactions.mesh_id`,
`dosage_form_rules.drug_form`. Tu khoa la tieng Viet co dau; cum tu 2 tu tro len duoc khop
them dang khong dau (vd "buoi chum"). Tu don khong dau de nham ("sua" = sữa / sửa) nen khong khop.
Tu dien nay la danh sach tu khoa pho bien, CHUA duoc duoc si duyet day du.
"""

import re
import unicodedata

from src.tools._khoa import khoa

FOOD_TERMS: dict[str, list[str]] = {
    "alcohol": ["rượu", "bia", "đồ uống có cồn", "alcohol"],
    "grapefruit juice": ["bưởi chùm", "nước bưởi", "bưởi", "grapefruit"],
    "high-fat foods": ["nhiều chất béo", "nhiều dầu mỡ", "đồ chiên rán", "thức ăn béo"],
    "food": ["thức ăn", "bữa ăn", "lúc đói", "lúc no", "bụng đói"],
    "Food High in Potassium": ["giàu kali", "nhiều kali", "chuối", "nước dừa"],
    "dairy products": ["sữa", "sữa chua", "phô mai", "pho mát", "milk"],
    "Tyrosine-rich foods": ["tyramin", "tyramine", "tyrosin", "đồ lên men", "thịt hun khói"],
    "coffee": ["cà phê", "cafe", "coffee", "caffein"],
    "orange juice": ["nước cam"],
    "cigarette": ["thuốc lá", "hút thuốc"],
    "bran": ["cám"],
    "grain": ["ngũ cốc"],
    "cereal": ["ngũ cốc ăn sáng"],
    "spinach": ["rau bina", "cải bó xôi", "rau chân vịt"],
    "rhubarb": ["đại hoàng"],
    "green tea": ["trà xanh", "chè xanh"],
    "cola": ["cola", "coca", "pepsi"],
    "soft drinks": ["nước ngọt có ga", "nước ngọt"],
    "soybean": ["đậu nành", "đậu phụ"],
    "dietary fiber": ["chất xơ"],
    "high-fiber meal": ["nhiều chất xơ"],
    "citrus fruits": ["cam quýt", "quả cam", "quýt", "chanh"],
    "Iodine-rich foods": ["i-ốt", "iod", "rong biển", "tảo bẹ"],
    "pomegranates": ["lựu"],
    "walnuts": ["óc chó"],
    "cranberry juice": ["nam việt quất", "cranberry"],
    "food high in vitamin K": ["vitamin k", "rau xanh", "rau lá xanh", "cải bó xôi", "rau bina", "bông cải",
                               "súp lơ xanh", "cải xoăn"],
}

DISEASE_TERMS: dict[str, list[str]] = {
    "MESH:D001249": ["hen", "hen suyễn", "hen phế quản", "suyễn"],                       # Asthma
    "MESH:D007674": ["suy thận", "bệnh thận", "thận yếu"],                               # Kidney Diseases
    "MESH:D007676": ["suy thận mạn", "bệnh thận mạn"],                                   # Kidney Failure, Chronic
    "MESH:D006435": ["chạy thận", "lọc máu"],                                            # Hemodialysis
    "MESH:D008107": ["bệnh gan", "viêm gan", "xơ gan", "suy gan", "men gan cao"],        # Liver Diseases
    "MESH:D048550": ["suy gan"],                                                         # Hepatic Insufficiency
    "MESH:D017093": ["suy gan"],                                                         # Liver Failure
    "MESH:D003920": ["tiểu đường", "đái tháo đường"],                                    # Diabetes Mellitus
    "MESH:D003866": ["trầm cảm"],                                                        # Depressive Disorder
    "MESH:D007022": ["huyết áp thấp", "tụt huyết áp", "hạ huyết áp"],                    # Hypotension
    "MESH:D006973": ["tăng huyết áp", "cao huyết áp", "huyết áp cao"],                   # Hypertension
    "MESH:D006333": ["suy tim"],                                                         # Heart Failure
    "MESH:D004827": ["động kinh"],                                                       # Epilepsy
    "MESH:D012640": ["co giật", "động kinh"],                                            # Seizures
    "MESH:D005901": ["glôcôm", "glaucoma", "tăng nhãn áp", "cườm nước"],                 # Glaucoma
    "MESH:D010437": ["loét dạ dày", "loét tá tràng", "viêm loét dạ dày"],                # Peptic Ulcer
    "MESH:D001145": ["rối loạn nhịp tim", "loạn nhịp tim"],                              # Arrhythmias, Cardiac
    "MESH:D008133": ["qt kéo dài"],                                                      # Long QT Syndrome
    "MESH:D007037": ["suy giáp"],                                                        # Hypothyroidism
    "MESH:D006980": ["cường giáp"],                                                      # Hyperthyroidism
    "MESH:D006470": ["xuất huyết"],                                                      # Hemorrhage
    "MESH:D000740": ["thiếu máu"],                                                       # Anemia
    "MESH:D009157": ["nhược cơ"],                                                        # Myasthenia Gravis
    "MESH:D006949": ["mỡ máu cao", "rối loạn mỡ máu", "tăng lipid máu"],                 # Hyperlipidemias
    "MESH:D003324": ["bệnh mạch vành"],                                                  # Coronary Artery Disease
    "MESH:D000437": ["nghiện rượu"],                                                     # Alcoholism
    "MESH:D003704": ["sa sút trí tuệ"],                                                  # Dementia
    "MESH:D020734": ["parkinson"],                                                       # Parkinsonian Disorders
    "MESH:D006947": ["tăng kali máu"],                                                   # Hyperkalemia
    "MESH:D007008": ["hạ kali máu"],                                                     # Hypokalemia
    "MESH:D016055": ["bí tiểu"],                                                         # Urinary Retention
    "MESH:D013927": ["huyết khối"],                                                      # Thrombosis
    "MESH:D013923": ["huyết khối", "thuyên tắc"],                                        # Thromboembolism
    "MESH:D001714": ["rối loạn lưỡng cực"],                                              # Bipolar Disorder
    "MESH:D003092": ["viêm đại tràng"],                                                  # Colitis
    "MESH:D008171": ["bệnh phổi", "copd", "phổi tắc nghẽn"],                             # Lung Diseases
    "MESH:D002318": ["bệnh tim mạch"],                                                   # Cardiovascular Diseases
    "MESH:D006331": ["bệnh tim"],                                                        # Heart Diseases
    "MESH:D007003": ["hạ đường huyết"],                                                  # Hypoglycemia
}

FORM_TERMS: dict[str, list[str]] = {
    "capsule": ["viên nang", "capsule"],
    "tablet": ["viên nén", "tablet"],
}


_SEP = re.compile(r"[^\w%-]+")


def _mentions(text: str, keywords: list[str]) -> bool:
    low = " " + _SEP.sub(" ", unicodedata.normalize("NFC", text or "").lower()) + " "
    bare = f" {khoa(text)} "
    for kw in keywords:
        if f" {kw} " in low or (" " in kw and f" {khoa(kw)} " in bare):
            return True
    return False


def _detect(text: str, terms: dict[str, list[str]]) -> set[str]:
    return {key for key, kws in terms.items() if _mentions(text, kws)}


def detect_foods(text: str) -> set[str]:
    """Khoa `food_interactions.food` cua cac thuc pham duoc nhac toi."""
    return _detect(text, FOOD_TERMS)


def detect_diseases(text: str) -> set[str]:
    """`mesh_id` cua cac benh nen duoc nhac toi."""
    return _detect(text, DISEASE_TERMS)


def detect_forms(text: str) -> set[str]:
    """Dang bao che duoc neu ro (capsule / tablet)."""
    return _detect(text, FORM_TERMS)
