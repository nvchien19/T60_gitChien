from src.tools.normalizer import AliasRow, normalize_name


def _aliases():
    return [
        AliasRow(alias="warfarin", drug_id="DDInter1", status="ok",
                 source_id="ddinter", drug_name="Warfarin"),
        AliasRow(alias="aspirin", drug_id="DDInter2", status="ok",
                 source_id="ddinter", drug_name="Aspirin"),
        AliasRow(alias="asca", drug_id="DDInter2", status="suggest",
                 source_id="dav", drug_name="Aspirin"),
    ]


def test_exact_ok_case_insensitive():
    r = normalize_name("Warfarin", _aliases(), {"DDInter1": "Warfarin"})
    assert r.status == "ok" and r.drug_id == "DDInter1"


def test_exact_suggest_needs_confirm():
    r = normalize_name("asca", _aliases(), {"DDInter2": "Aspirin"})
    assert r.status == "suggest" and r.suggestions


def test_vietnamese_no_diacritics():
    r = normalize_name("WARFARIN ", _aliases(), {"DDInter1": "Warfarin"})
    assert r.status == "ok"


def test_unknown():
    r = normalize_name("thuoc xyz khong ton tai", _aliases(), {})
    assert r.status == "unknown" and "Chưa có bản ghi" in r.note


def test_suggest_not_auto_accepted():
    r = normalize_name("asprin", _aliases(), {"DDInter2": "Aspirin"})
    assert r.status in ("suggest", "unknown")
    if r.status == "suggest":
        assert r.drug_id == ""  # khong tu ap dung


def test_combination_brand_checks_every_ingredient():
    aliases = [
        AliasRow(alias="augmentin", drug_id="DDInter394", status="ok", source_id="dav", drug_name="Clavulanic acid"),
        AliasRow(alias="augmentin", drug_id="DDInter83", status="ok", source_id="dav", drug_name="Amoxicillin"),
    ]
    r = normalize_name("Augmentin", aliases, {})
    assert r.status == "ok"  # khong hoi lai: hoi lai lam agent bo sot tuong tac
    assert r.drug_ids == ["DDInter394", "DDInter83"]
    r = normalize_name("augmetin", aliases, {})
    assert r.status == "suggest" and set(r.drug_ids) == {"DDInter394", "DDInter83"}
