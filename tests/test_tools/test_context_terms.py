from src.tools.context_terms import detect_diseases, detect_foods, detect_forms
from src.tools.lookup_core import apply_dosage_rule, cross_input_pairs


def test_detect_foods():
    assert "food high in vitamin K" in detect_foods("ăn nhiều rau xanh như cải bó xôi có ảnh hưởng không?")
    assert detect_foods("Uống Ciprofloxacin với sữa được không?") == {"dairy products"}
    assert "grapefruit juice" in detect_foods("hay uong nuoc buoi chum")      # cum tu khong dau van khop
    assert detect_foods("nhờ sửa giúp đơn thuốc") == set()                    # "sửa" khong phai "sữa"


def test_detect_diseases_and_forms():
    assert "MESH:D001249" in detect_diseases("Tôi bị hen suyễn, đau răng")
    assert detect_diseases("Tôi hẹn bác sĩ ngày mai") == set()
    assert detect_forms("palbociclib VIÊN NANG") == {"capsule"}
    assert detect_forms("palbociclib") == set()


def test_cross_input_pairs_skip_same_product():
    pairs = cross_input_pairs([["DDInter394", "DDInter83"], ["DDInter1174"]])
    assert pairs == [("DDInter83", "DDInter1174"), ("DDInter394", "DDInter1174")]


def test_form_specific_rule_respects_stated_form():
    rule = {"action": "form_specific", "severity": "moderate", "drug_form": "capsule", "rule_id": "R1"}
    assert apply_dosage_rule(None, rule, forms={"tablet"}) is None
    assert apply_dosage_rule(None, rule, forms={"capsule"})["citations"][0]["record_id"] == "R1"
    assert apply_dosage_rule(None, rule) is not None                          # khong ro dang -> van canh bao
