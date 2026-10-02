from src.core.guardrails import guardrail_assert, sanitize_text


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
