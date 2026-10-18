from src.core.guardrails import HANDOFF, guardrail_assert, sanitize_text


def test_blocks_advice():
    t = sanitize_text("Bạn nên ngưng thuốc này")
    assert "bác sĩ" in t and "nên ngưng thuốc này" not in t


def test_blocks_safe_on_no_record():
    t = sanitize_text("Thuốc này an toàn", is_no_record=True)
    assert "an toàn" not in t


def test_drops_finding_without_citation():
    out = guardrail_assert([{"pair": ["a", "b"], "severity": "major",
                             "summary": "ok", "citations": []}])
    assert out == []


def test_keeps_grounded_finding():
    f = {"pair": ["a", "b"], "severity": "major", "summary": "Tăng chảy máu.",
         "citations": [{"source_id": "ddinter"}]}
    assert len(guardrail_assert([f])) == 1


def test_advice_sentence_replaced_whole_not_mid_sentence():
    src = ("Nên tránh dùng đồng thời hai thuốc. Có thể cần giảm liều. "
           "Theo dõi chảy máu. Liệu pháp có thể yêu cầu tạm ngưng.")
    t = sanitize_text(src)
    assert t == f"Nên tránh dùng đồng thời hai thuốc. {HANDOFF} Theo dõi chảy máu."
    assert t.count("Liên hệ bác sĩ") == 1


def test_handoff_not_repeated_when_already_present():
    t = sanitize_text(f"Tăng nguy cơ chảy máu. {HANDOFF} Bạn nên ngưng thuốc.")
    assert t == f"Tăng nguy cơ chảy máu. {HANDOFF}"


def test_text_without_advice_unchanged():
    src = "Dùng đồng thời có thể làm tăng nồng độ 0.5 mg/L.\nTheo dõi INR."
    assert sanitize_text(src) == src
