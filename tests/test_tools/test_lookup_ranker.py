from src.tools.lookup_core import all_pairs, apply_dosage_rule, ara_applies, cosine
from src.tools.ranker import merge_severity, rank_findings


def test_all_pairs_sorted():
    assert all_pairs(["DDInter2", "DDInter1", "DDInter1"]) == [("DDInter1", "DDInter2")]


def test_merge_keeps_highest_with_all_citations():
    recs = [
        {"pair": ["a", "b"], "severity": "moderate", "match_type": "exact",
         "citations": [{"source_id": "ddinter"}]},
        {"pair": ["a", "b"], "severity": "contraindicated", "match_type": "exact",
         "citations": [{"source_id": "openfda"}]},
    ]
    m = merge_severity(recs)
    assert m["severity"] == "contraindicated" and len(m["citations"]) == 2


def test_rank_order_and_no_record_separate():
    recs = [
        {"pair": ["a", "b"], "severity": "minor", "match_type": "exact", "citations": [{"source_id": "x"}]},
        {"pair": ["a", "c"], "severity": "major", "match_type": "exact", "citations": [{"source_id": "x"}]},
        {"pair": ["b", "c"], "severity": "unknown", "match_type": "no_record", "citations": []},
    ]
    merged, max_sev, no_rec = rank_findings(recs)
    assert [m["severity"] for m in merged] == ["major", "minor"]
    assert max_sev == "major" and no_rec == [["b", "c"]]


def test_dosage_raise_applies_all_forms():
    out = apply_dosage_rule("moderate", {"action": "raise_severity", "severity": "contraindicated",
                                         "source_id": "openfda"}, drug_route="topical")
    assert out and out["severity"] == "contraindicated"


def test_ara_requires_oral():
    ara = {"victim_drug_ids": ["V"], "victim_is_combination": False, "route_scope": "oral"}
    assert ara_applies(ara, "V", {"V": "oral"})
    assert not ara_applies(ara, "V", {"V": "topical"})


def test_cosine():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
