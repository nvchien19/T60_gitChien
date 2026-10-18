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


def _rx_aliases():
    return _aliases() + [
        AliasRow(alias="voltaren", drug_id="DDInter3", status="ok", source_id="dav", drug_name="Diclofenac"),
        AliasRow(alias="diclofenac", drug_id="DDInter3", status="ok", source_id="ddinter", drug_name="Diclofenac"),
        AliasRow(alias="metformin", drug_id="DDInter4", status="ok", source_id="ddinter", drug_name="Metformin"),
        AliasRow(alias="kali clorid", drug_id="DDInter5", status="ok", source_id="dav", drug_name="Potassium chloride"),
        AliasRow(alias="vitamin b12", drug_id="DDInter6", status="ok", source_id="dav", drug_name="Cyanocobalamin"),
    ]


def test_strength_on_prescription_is_ignored():
    for raw in ["Warfarin 5mg", "Warfarin 5 mg", "WARFARIN 2,5mg", "Warfarin 0.5 g", "Warfarin 5mg viên nén"]:
        r = normalize_name(raw, _rx_aliases(), {"DDInter1": "Warfarin"})
        assert r.status == "ok" and r.drug_id == "DDInter1", raw
        assert "đã bỏ hàm lượng" in r.note
    r = normalize_name("Metformin 500mg/5ml", _rx_aliases(), {})
    assert r.status == "ok" and r.drug_id == "DDInter4"
    r = normalize_name("Kali clorid 10%", _rx_aliases(), {})
    assert r.status == "ok" and r.drug_id == "DDInter5"


def test_number_inside_name_is_kept():
    # "B12" la mot phan cua ten, khong phai ham luong
    r = normalize_name("Vitamin B12 1000mcg", _rx_aliases(), {})
    assert r.status == "ok" and r.drug_id == "DDInter6"


def test_parenthesis_brand_and_ingredient():
    r = normalize_name("Voltaren (Diclofenac)", _rx_aliases(), {})
    assert r.status == "ok" and r.drug_id == "DDInter3"
    r = normalize_name("Thuoc la (Diclofenac 50mg)", _rx_aliases(), {})
    assert r.status == "ok" and r.drug_id == "DDInter3"


def test_parenthesis_conflict_is_not_auto_accepted():
    r = normalize_name("Voltaren (Warfarin)", _rx_aliases(), {})
    assert r.status == "suggest" and r.drug_id == ""
    assert {h["drug_id"] for h in r.suggestions} == {"DDInter1", "DDInter3"}


def test_variant_needs_exact_match():
    # Bo ham luong xong van khong khop exact -> khong tu nhan
    r = normalize_name("Warfarinn 5mg", _rx_aliases(), {})
    assert r.drug_id == "" and r.status in ("suggest", "unknown")


def test_square_bracket_ingredient():
    aliases = _rx_aliases()
    names = {a.drug_id: a.drug_name for a in aliases}
    r = normalize_name("Thuoclaxyz 500mg [Diclofenac]", aliases, names)
    assert r.status == "ok"
    assert r.canonical_name == names[r.drug_id]
