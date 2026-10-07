import pytest

from src.tools.normalizer import AliasRow

langgraph = pytest.importorskip("langgraph", reason="P0 BE khong can agent (P-Agent sau)")

from src.agents.graph import get_agent  # noqa: E402

CATALOG = {
    "aliases": [
        AliasRow(alias="warfarin", drug_id="DDInter1", source_id="ddinter", status="ok",
                 drug_name="Warfarin"),
        AliasRow(alias="aspirin", drug_id="DDInter2", source_id="ddinter", status="ok",
                 drug_name="Aspirin"),
    ],
    "drug_names": {"DDInter1": "Warfarin", "DDInter2": "Aspirin"},
}

INTERACTION = {
    "pair": ["DDInter1", "DDInter2"],
    "pair_names": ["Warfarin", "Aspirin"],
    "severity": "major",
    "summary": "Tang nguy co chay mau khi dung chung.",
    "mechanism": "synergy",
    "citations": [{"source_id": "ddinter", "label": "DDInter 2.0"}],
    "match_type": "exact",
}


@pytest.mark.asyncio
async def test_agent_returns_response():
    result = await get_agent().ainvoke({"query": "warfarin, aspirin", "catalog": CATALOG})
    assert result["response"]
    assert result["guardrail_result"]["pass"] is True


@pytest.mark.asyncio
async def test_agent_grounded_with_citation():
    result = await get_agent().ainvoke({
        "query": "warfarin, aspirin",
        "catalog": CATALOG,
        "interactions": [INTERACTION],
    })
    assert result["max_severity"] == "major"
    assert "Warfarin, Aspirin" in result["response"]
    assert "[1]" in result["response"]


@pytest.mark.asyncio
async def test_agent_clarify_on_suggest_no_auto_accept():
    result = await get_agent().ainvoke({"query": "warfarin, aspirinx", "catalog": CATALOG})
    assert result["pending_clarifications"]
    assert "xác nhận" in result["response"]


@pytest.mark.asyncio
async def test_agent_no_record_never_says_safe():
    result = await get_agent().ainvoke({
        "query": "warfarin, aspirin",
        "catalog": CATALOG,
        "interactions": [],
    })
    assert result["no_record_pairs"]
    assert "an toàn" not in result["response"]


@pytest.mark.asyncio
async def test_agent_guardrail_drops_uncited_finding():
    uncited = {**INTERACTION, "citations": []}
    result = await get_agent().ainvoke({
        "query": "warfarin, aspirin",
        "catalog": CATALOG,
        "interactions": [uncited],
    })
    assert result["ranked_findings"] == []
    assert result["guardrail_result"]["dropped_findings"] >= 0


@pytest.mark.asyncio
async def test_agent_error_on_empty_query():
    result = await get_agent().ainvoke({"query": "  ,  "})
    assert result["error"]
    assert result["response"]


@pytest.mark.asyncio
async def test_agent_keeps_food_record_and_flags_duplicate_active():
    catalog = {
        "aliases": [*CATALOG["aliases"],
                    AliasRow(alias="asca", drug_id="DDInter2", source_id="dav", status="ok", drug_name="Aspirin")],
        "drug_names": CATALOG["drug_names"],
    }
    food = {"kind": "food", "pair": ["DDInter1", "food:alcohol"], "pair_names": ["Warfarin", "rượu, bia"],
            "drug_ids": ["DDInter1"], "target": "alcohol", "severity": "moderate", "summary": "x",
            "citations": [{"source_id": "ddinter", "label": "DDInter 2.0", "record_id": "DDInter1|alcohol"}],
            "match_type": "exact"}
    result = await get_agent().ainvoke({"query": "warfarin, aspirin, asca", "catalog": catalog,
                                        "interactions": [INTERACTION, food]})
    kinds = {f.get("kind", "interaction") for f in result["ranked_findings"]}
    assert kinds == {"interaction", "food", "duplicate_active"}
    assert result["max_severity"] == "major"
