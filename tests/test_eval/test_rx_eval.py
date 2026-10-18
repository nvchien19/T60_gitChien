"""Kiểm tra bộ chấm chức năng kiểm tra đơn (eval/run_rx_eval.py) và bộ ca đơn thật đã đóng băng."""
import json
import pathlib
import sys

EVAL = pathlib.Path(__file__).resolve().parents[2] / "eval"
sys.path.insert(0, str(EVAL))

from run_rx_eval import _sys_level, binary, names_match, same_ingredient, weighted_kappa, wilson  # noqa: E402

GOLDEN = EVAL / "golden"


def _load(name):
    return [json.loads(line) for line in (GOLDEN / name).open(encoding="utf-8")]


def test_same_ingredient_handles_salts_synonyms_and_vietnamese():
    assert same_ingredient("Metoprolol", "metoprolol")
    assert same_ingredient("Nefopam hydroclorid", "nefopam")
    assert same_ingredient("Acetylsalicylic acid", "aspirin")
    assert same_ingredient("Natri fluorid", "sodium fluoride")
    assert same_ingredient("Acid folic", "folic acid")
    assert same_ingredient("Betamethasone (topical)", "betamethasone")
    assert not same_ingredient("Sodium bicarbonate", "potassium bicarbonate")
    assert not same_ingredient("Amlodipine", "amiodarone")


def test_names_match_requires_same_set():
    assert names_match(["calcipotriene", "betamethasone"], ["Betamethasone (topical)", "Calcipotriol (topical)"])
    assert not names_match(["amoxicillin", "clavulanate"], ["Amoxicillin"])
    assert not names_match(["acetaminophen"], ["Acetaminophen", "Oxycodone"])


def test_binary_and_wilson():
    m = binary([True, True, False, False], [True, False, False, True])
    assert (m["tp"], m["fn"], m["tn"], m["fp"]) == (1, 1, 1, 1)
    assert m["sensitivity"] == 0.5 and m["specificity"] == 0.5
    lo, hi = wilson(9, 10)
    assert lo < 0.9 < hi and hi <= 1.0
    assert wilson(0, 0) is None


def test_weighted_kappa_bounds():
    assert weighted_kappa([1, 2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4]) == 1.0
    assert weighted_kappa([1, 1, 4, 4], [4, 4, 1, 1], [1, 2, 3, 4]) < 0


def test_sys_level_uses_al_ashwal_scale():
    pred = {"findings": [{"severity": "minor", "sources": ["ddinter"]}, {"severity": "major", "sources": ["x"]}]}
    assert _sys_level(pred) == 4
    assert _sys_level(pred, sources={"ddinter"}) == 2
    assert _sys_level({"findings": []}) == 1


def test_frozen_sets_are_consistent():
    aa = _load("pair_set_alashwal.jsonl")
    assert len(aa) == 255 and len({p["pair_id"] for p in aa}) == 255
    assert sum(p["drugscom"] >= 3 for p in aa) == 79
    assert sum(p["micromedex"] >= 3 for p in aa) == 47
    onc = _load("pair_set_onc.jsonl")
    assert len({p["pair_id"] for p in onc}) == len(onc) and not any(p["rule"] == "ONC-08" for p in onc)
    rx = _load("rx_golden_set.jsonl")
    assert len({c["id"] for c in rx}) == len(rx)
    for case in rx:
        inputs = case["drugs"]
        assert len(inputs) >= 2 and len({d.lower() for d in inputs}) == len(inputs)
        for d in case["expected_duplicates"] + case["must_alert"]:
            assert set(d["pair"]) <= set(inputs)


def test_quote_check_ignores_case_dashes_and_spaces():
    sys.path.insert(0, str(GOLDEN))
    from build_authoritative_ref import _plain
    label = "Strong CYP3A4 inhibitors\u2014such as clarithromycin \u2014 increase  exposure."
    assert _plain("strong cyp3a4 inhibitors-such as clarithromycin - increase exposure") in _plain(label)
    assert _plain("ketoconazole increases exposure") not in _plain(label)


def test_authoritative_reference_is_consistent():
    path = GOLDEN / "pair_ref_authoritative.jsonl"
    if not path.exists():
        return
    aa = {p["pair_id"]: p for p in _load("pair_set_alashwal.jsonl")}
    ref = _load(path.name)
    assert {r["pair_id"] for r in ref} == set(aa)
    evidence = {r["pair_id"]: r for r in _load("refs/fda_label_evidence_alashwal.jsonl")}
    kegg = {r["pair_id"]: r for r in _load("refs/kegg_ddi_alashwal.jsonl")}
    for r in ref:
        assert r["votes"]["micromedex"] == (aa[r["pair_id"]]["micromedex"] >= 3)
        assert r["n_sources"] == sum(r["votes"].values())
        assert r["ref_any"] == (r["n_sources"] >= 1) and r["ref_two"] == (r["n_sources"] >= 2)
        # nhãn FDA chỉ được tính khi có câu trích nguyên văn đã đối chiếu
        positive = [s for s in evidence[r["pair_id"]]["sides"] if s["status"] == "positive"]
        assert r["votes"]["fda_label"] == bool(positive)
        assert all(s["quote_verified"] and s["quote"] for s in positive)
        assert r["votes"]["japan_label"] == (r["pair_id"] in kegg and kegg[r["pair_id"]]["explained"])
