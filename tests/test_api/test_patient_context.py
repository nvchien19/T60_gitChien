import json
import sqlite3

import pytest

from interface.backend.services.patient_context import matches, result_label
from tests.conftest import TEST_DB

LIVER = "MESH:D008107"
KIDNEY = "MESH:D007674"


def _seed():
    with sqlite3.connect(TEST_DB) as con:
        con.execute("INSERT OR IGNORE INTO sources (source_id, name, citation, url, license, last_updated)"
                    " VALUES ('medrt','MED-RT','NLM','https://rxnav.nlm.nih.gov','public','2026-10-10')")
        con.execute("INSERT OR IGNORE INTO sources (source_id, name, citation, url, license, last_updated)"
                    " VALUES ('cpic','CPIC','CPIC','https://cpicpgx.org','CC0 1.0','2026-10-10')")
        con.executemany(
            'INSERT INTO disease_interactions (drug_id, drug_name, disease, mesh_id, severity, description,'
            ' "references", source_id) VALUES (?,?,?,?,?,?,?,?)',
            [("DDInter1", "Warfarin", "fixture Liver Diseases", LIVER, "major", "Bleeding risk in liver disease",
              "ref-liver", "ddinter"),
             ("DDInter1", "Warfarin", "fixture Liver Diseases", LIVER, "contraindicated", "", "MED-RT CI_with", "medrt"),
             ("DDInter2", "Aspirin", "fixture Kidney Diseases", KIDNEY, "contraindicated", "", "MED-RT CI_with",
              "medrt")])
        con.executemany(
            "INSERT INTO gene_interactions (id, drug_id, drug_name, genes, lookupkey, implication_text, recommendation,"
            " classification, population, comments, guideline_name, guideline_url, source_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(990001, "DDInter1", "warfarin", json.dumps({"CYP2C9": "Poor Metabolizer"}), "{}", "Reduced clearance",
              "Fixture: lower dose per guideline", "Strong", "general", "", "Fixture guideline",
              "https://cpicpgx.org/guidelines/fixture", "cpic"),
             (990002, "DDInter1", "warfarin", json.dumps({"CYP2C9": "Normal Metabolizer"}), "{}", "Normal clearance",
              "Fixture: standard dose", "Strong", "general", "", "Fixture guideline",
              "https://cpicpgx.org/guidelines/fixture", "cpic"),
             (990003, "DDInter2", "aspirin",
              json.dumps({"CYP2C9": "Poor Metabolizer", "HLA-B": "No Result"}), "{}", "Two-gene implication",
              "Fixture: two-gene advice", "Moderate", "general", "", "Fixture guideline",
              "https://cpicpgx.org/guidelines/fixture", "cpic")])


def _clean():
    with sqlite3.connect(TEST_DB) as con:
        con.execute("DELETE FROM disease_interactions WHERE disease LIKE 'fixture %'")
        con.execute("DELETE FROM gene_interactions WHERE id >= 990000")


@pytest.fixture
def context_data():
    _seed()
    yield
    _clean()


def test_matches_requires_every_gene_and_treats_missing_as_no_result():
    assert matches({"CYP2D6": "Poor Metabolizer"}, {"CYP2D6": "Poor Metabolizer"})
    assert not matches({"CYP2D6": "Poor Metabolizer"}, {"CYP2D6": "Normal Metabolizer"})
    assert not matches({"CYP2D6": "Poor Metabolizer"}, {"CYP2C19": "Poor Metabolizer"})
    assert matches({"CYP2D6": "Poor Metabolizer", "CYP2C19": "No Result"}, {"CYP2D6": "Poor Metabolizer"})
    assert not matches({"CYP2D6": "Poor Metabolizer", "CYP2C19": "Poor Metabolizer"}, {"CYP2D6": "Poor Metabolizer"})
    assert not matches({"CYP2D6": "No Result", "CYP2C19": "No Result"}, {"TPMT": "Normal Metabolizer"})


def test_result_label():
    assert result_label("HLA-B*15:02 positive") == "HLA-B*15:02 dương tính"
    assert result_label("Poor Metabolizer") == "Chuyển hóa kém"
    assert result_label("something new") == "something new"


@pytest.mark.asyncio
async def test_options_list_only_what_the_db_can_check(client, context_data):
    data = (await client.get("/api/v1/patient-context/options")).json()
    liver = next(c for c in data["conditions"] if c["mesh_id"] == LIVER)
    assert liver["sources"] == ["ddinter", "medrt"] and liver["n_drugs"] == 1
    cyp = next(g for g in data["genes"] if g["gene"] == "CYP2C9")
    assert {r["value"] for r in cyp["results"]} == {"Poor Metabolizer", "Normal Metabolizer"}
    # "No Result" là gen chưa xét nghiệm, không phải một kết quả để chọn
    assert next(g for g in data["genes"] if g["gene"] == "HLA-B")["results"] == []


@pytest.mark.asyncio
async def test_check_without_context_returns_no_context_findings(client, context_data):
    data = (await client.post("/api/v1/interactions/check", json={"drugs": ["warfarin", "aspirin"]})).json()
    assert data["disease_findings"] == [] and data["gene_findings"] == []


@pytest.mark.asyncio
async def test_disease_findings_match_exact_mesh_and_keep_sources(client, context_data):
    data = (await client.post("/api/v1/interactions/check", json={
        "drugs": ["warfarin", "aspirin"], "conditions": [LIVER, KIDNEY]})).json()
    rows = data["disease_findings"]
    assert len(rows) == 2
    # chỉ MED-RT: không có mô tả của nguồn, hệ thống nói rõ điều đó thay vì tự viết cơ chế
    kidney = next(r for r in rows if r["details"]["mesh_id"] == KIDNEY)
    assert kidney["pair"][0] == "Aspirin" and kidney["severity"] == "contraindicated"
    assert "Nguồn không kèm mô tả" in kidney["summary"] and kidney["original_mechanism"] == ""
    assert [c["source_id"] for c in kidney["citations"]] == ["medrt"]
    # DDInter có mô tả, MED-RT được ghi thêm như nguồn thứ hai
    liver = next(r for r in rows if r["details"]["mesh_id"] == LIVER)
    assert liver["severity"] == "major" and liver["summary"].startswith("Bleeding risk in liver disease")
    assert "MED-RT cũng ghi nhận" in liver["summary"]
    assert [c["source_id"] for c in liver["citations"]] == ["ddinter", "medrt"]
    assert liver["citations"][0]["label"] == "ref-liver"
    only_liver = (await client.post("/api/v1/interactions/check", json={
        "drugs": ["aspirin"], "conditions": [LIVER]})).json()
    assert only_liver["disease_findings"] == []


@pytest.mark.asyncio
async def test_gene_findings_quote_cpic_with_citation(client, context_data):
    data = (await client.post("/api/v1/interactions/check", json={
        "drugs": ["warfarin", "aspirin"], "genes": {"CYP2C9": "Poor Metabolizer"}})).json()
    rows = data["gene_findings"]
    assert [r["pair"][0] for r in rows] == ["Warfarin", "Aspirin"]
    warfarin, aspirin = rows
    assert warfarin["severity"] == "pgx" and warfarin["severity_vi"] == "Khuyến cáo mạnh"
    assert warfarin["management"] == "Fixture: lower dose per guideline"
    assert warfarin["original_management"] == "Fixture: lower dose per guideline"
    assert warfarin["pair"][1] == "CYP2C9: Chuyển hóa kém"
    assert warfarin["details"]["same_as_normal"] is False
    assert warfarin["citations"][0]["source_url"] == "https://cpicpgx.org/guidelines/fixture"
    assert aspirin["details"]["untested_genes"] == ["HLA-B"]
    normal = (await client.post("/api/v1/interactions/check", json={
        "drugs": ["warfarin"], "genes": {"CYP2C9": "Normal Metabolizer"}})).json()["gene_findings"]
    assert len(normal) == 1 and normal[0]["details"]["same_as_normal"] is True


@pytest.mark.asyncio
async def test_prescription_context_is_validated_saved_and_used(client, context_data):
    rx = (await client.post("/api/v1/prescriptions", json={"medications": [{"name": "warfarin"}]})).json()["id"]
    bad = await client.put(f"/api/v1/prescriptions/{rx}/context", json={"conditions": ["MESH:D000000"], "genes": {}})
    assert bad.status_code == 422
    bad_gene = await client.put(f"/api/v1/prescriptions/{rx}/context",
                                json={"conditions": [], "genes": {"CYP2C9": "No Result"}})
    assert bad_gene.status_code == 422
    saved = await client.put(f"/api/v1/prescriptions/{rx}/context",
                             json={"conditions": [LIVER], "genes": {"CYP2C9": "Poor Metabolizer"}})
    assert saved.status_code == 200
    assert saved.json() == {"conditions": [LIVER], "genes": {"CYP2C9": "Poor Metabolizer"}}
    listed = (await client.get("/api/v1/prescriptions?limit=100")).json()["items"]
    assert next(p for p in listed if p["id"] == rx)["patient_context"] == saved.json()
    check = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()
    record = (await client.get(f"/api/v1/checks/{check['check_id']}")).json()
    assert len(record["disease_findings"]) == 1 and len(record["gene_findings"]) == 1
    assert record["patient_context"] == saved.json()
    listed = (await client.get("/api/v1/prescriptions?limit=100")).json()["items"]
    assert next(p for p in listed if p["id"] == rx)["status"] == "Có tương tác"
