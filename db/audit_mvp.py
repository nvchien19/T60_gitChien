"""Kiểm tra độ sạch của data/mvp/*.csv so với db/mvp_schema.sql. Chỉ dùng thư viện chuẩn."""
import csv, re, sys, unicodedata, pathlib, collections, datetime

sys.stdout.reconfigure(encoding="utf-8")
csv.field_size_limit(2**30)
MVP = pathlib.Path(sys.argv[1])
SCHEMA = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")

def load(t):
    with open(MVP / f"{t}.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

# ---- đọc schema: cột, NOT NULL, kiểu ----
tables = {}
for m in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\);", SCHEMA, re.S):
    cols = {}
    for ln in m.group(2).splitlines():
        ln = ln.split("--")[0].strip().rstrip(",")
        mm = re.match(r'"?(\w+)"?\s+(text|integer|boolean|date|double precision)\b(.*)', ln)
        if mm:
            cols[mm.group(1)] = (mm.group(2), "NOT NULL" in mm.group(3) or "PRIMARY KEY" in mm.group(3),
                                 re.search(r"REFERENCES (\w+)", mm.group(3)))
    tables[m.group(1)] = cols
tables.pop("severity_levels")
SEV = {"contraindicated", "major", "moderate", "minor", "none"}
data = {t: load(t) for t in tables}
issues = collections.OrderedDict()
def add(key, n, ex=None):
    if n:
        issues[key] = (n, ex)

BAD_CHARS = re.compile(r"[ ​-‏  ﻿�­\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
MOJI = re.compile(r"Ã[\x80-\xbf¡-¿]|â€|Â[\xa0-\xbf]|Ä[\x90\x91]|á»|áº")
HTML = re.compile(r"&(amp|lt|gt|nbsp|quot|#\d+|#x[0-9a-f]+);|</?(br|p|b|i|sup|sub|span|div|a|li|ul|td|tr|em|strong)\b[^>]*>", re.I)
NULLISH = {"nan", "none", "null", "n/a", "na", "-", "--", "?", "undefined", "nat"}

pk = {"sources": "source_id", "drugs": "drug_id", "products": "product_id",
      "interaction_mechanisms": "mechanism_id", "drug_interactions": "interaction_id", "fda_labels": "label_set_id"}
ids = {t: {r[k] for r in data[t]} for t, k in pk.items()}

for t, cols in tables.items():
    rows = data[t]
    hdr = list(rows[0].keys())
    if hdr != list(cols):
        add(f"{t}: cột CSV lệch schema", 1, f"{hdr} vs {list(cols)}")
    seen = collections.Counter(tuple(r.values()) for r in rows)
    add(f"{t}: dòng trùng hoàn toàn", sum(c - 1 for c in seen.values() if c > 1),
        next((k[:4] for k, c in seen.items() if c > 1), None))
    if t in pk:
        c = collections.Counter(r[pk[t]] for r in rows)
        add(f"{t}: trùng khóa chính", sum(v - 1 for v in c.values() if v > 1))
    for col, (typ, notnull, ref) in cols.items():
        if col not in rows[0]:
            continue
        cnt = collections.Counter(); ex = {}
        for r in rows:
            v = r[col]
            def hit(k):
                cnt[k] += 1; ex.setdefault(k, v[:90])
            if v == "":
                if notnull: hit("rỗng ở cột NOT NULL")
                continue
            if v != v.strip(): hit("thừa khoảng trắng đầu/cuối")
            if "  " in v and typ == "text": hit("hai khoảng trắng liền")
            if "\n" in v or "\r" in v or "\t" in v: hit("xuống dòng/tab trong ô")
            if BAD_CHARS.search(v): hit("ký tự ẩn (NBSP, zero-width, điều khiển, U+FFFD)")
            if MOJI.search(v): hit("lỗi mã hóa (mojibake)")
            if HTML.search(v): hit("còn thẻ/entity HTML")
            if v.strip().lower() in NULLISH: hit("giá trị giả rỗng (nan/None/-)")
            if unicodedata.normalize("NFC", v) != v: hit("Unicode chưa NFC")
            if typ == "integer" and not re.fullmatch(r"-?\d+", v): hit("không phải số nguyên")
            if typ == "boolean" and v not in ("True", "False"): hit("không phải boolean")
            if typ == "double precision":
                try: float(v)
                except ValueError: hit("không phải số thực")
            if typ == "date":
                try: datetime.date.fromisoformat(v)
                except ValueError: hit("ngày sai định dạng")
            if ref:
                rt = ref.group(1)
                if rt == "severity_levels":
                    if v not in SEV: hit("severity lạ")
                elif v not in ids[rt]: hit(f"khóa ngoại không tồn tại ({rt})")
        for k, n in cnt.items():
            add(f"{t}.{col}: {k}", n, ex[k])

# ---- kiểm tra nghiệp vụ ----
def khoa(s):
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9%]+", " ", s).strip()

D = data
num = lambda x: int(x[7:]) if x.startswith("DDInter") else None
di = D["drug_interactions"]
add("drug_interactions: tự tương tác", sum(r["drug_a"] == r["drug_b"] for r in di))
add("drug_interactions: drug_a không < drug_b", sum(1 for r in di if num(r["drug_a"]) is None or num(r["drug_b"]) is None or num(r["drug_a"]) >= num(r["drug_b"])))
c = collections.Counter((r["drug_a"], r["drug_b"], r["mechanism_id"]) for r in di)
add("drug_interactions: trùng (a,b,cơ chế)", sum(v - 1 for v in c.values() if v > 1))
c2 = collections.Counter((r["drug_a"], r["drug_b"]) for r in di)
print("cặp duy nhất:", len(c2), "| cặp >2 cơ chế:", sum(v > 2 for v in c2.values()))
c3 = collections.Counter((r["drug_a"], r["drug_b"], r["severity"], r["mechanism_type"]) for r in di)
mech = {r["mechanism_id"]: r for r in D["interaction_mechanisms"]}
used = collections.Counter(r["mechanism_id"] for r in di)
add("interaction_mechanisms: cơ chế không cặp nào dùng", sum(1 for k in mech if k not in used), next((k for k in mech if k not in used), None))
add("interaction_mechanisms: n_pairs lệch số cặp thực", sum(1 for k, r in mech.items() if int(r["n_pairs"]) != used[k]),
    next(((k, r["n_pairs"], used[k]) for k, r in mech.items() if int(r["n_pairs"]) != used[k]), None))
add("drug_interactions: mechanism_type lệch bảng cơ chế", sum(r["mechanism_type"] != mech[r["mechanism_id"]]["mechanism_type"] for r in di))
add("drug_interactions: source_url sai mẫu", sum(not re.fullmatch(r"https://ddinter2\.scbdd\.com/server/interact/\d+/", r["source_url"]) for r in di))
dc = collections.Counter(r["description"] for r in D["interaction_mechanisms"])
add("interaction_mechanisms: mô tả trùng nhau (khác id)", sum(v - 1 for v in dc.values() if v > 1))
print("mechanism_type:", collections.Counter(r["mechanism_type"] for r in D["interaction_mechanisms"]).most_common())

drugs = {r["drug_id"]: r for r in D["drugs"]}
partners = collections.defaultdict(set)
for r in di:
    partners[r["drug_a"]].add(r["drug_b"]); partners[r["drug_b"]].add(r["drug_a"])
add("drugs: n_interactions lệch thực tế", sum(int(r["n_interactions"]) != len(partners[k]) for k, r in drugs.items()))
add("drug_interactions: both_in_vn lệch drugs.in_vn", sum((r["both_in_vn"] == "True") != (drugs[r["drug_a"]]["in_vn"] == "True" and drugs[r["drug_b"]]["in_vn"] == "True") for r in di))
add("drugs: in_vn lệch n_products_valid", sum((r["in_vn"] == "True") != (int(r["n_products_valid"]) > 0) for r in drugs.values()))
nm = collections.Counter(r["name"].lower() for r in drugs.values())
add("drugs: trùng tên (khác id)", sum(v - 1 for v in nm.values() if v > 1), [k for k, v in nm.items() if v > 1][:5])
add("drugs: drug_id sai mẫu", sum(not re.fullmatch(r"DDInter\d+|DAV:.+|EXT:.+", k) for k in drugs))
print("drug_type:", collections.Counter(r["drug_type"] for r in drugs.values()).most_common(8))
print("route_variant:", collections.Counter(r["route_variant"] for r in drugs.values()).most_common())
add("drugs: atc_code sai mẫu", sum(1 for r in drugs.values() if r["atc_code"] and not re.fullmatch(r"[A-Z]\d{2}[A-Z]{2}\d{2}(;\s?[A-Z]\d{2}[A-Z]{2}\d{2})*", r["atc_code"])),
    next((r["atc_code"] for r in drugs.values() if r["atc_code"] and not re.fullmatch(r"[A-Z]\d{2}[A-Z]{2}\d{2}(;\s?[A-Z]\d{2}[A-Z]{2}\d{2})*", r["atc_code"])), None))
add("drugs: drugbank_id sai mẫu", sum(1 for r in drugs.values() if r["drugbank_id"] and not re.fullmatch(r"DB\d{5}", r["drugbank_id"])),
    next((r["drugbank_id"] for r in drugs.values() if r["drugbank_id"] and not re.fullmatch(r"DB\d{5}", r["drugbank_id"])), None))

al = D["aliases"]
add("aliases: alias khác khoa(alias)", sum(khoa(r["alias"]) != r["alias"] for r in al), next((r["alias"] for r in al if khoa(r["alias"]) != r["alias"]), None))
add("aliases: alias < 3 ký tự", sum(len(r["alias"]) < 3 for r in al))
add("aliases: trùng khóa (alias,drug_id,source_id)", sum(v - 1 for v in collections.Counter((r["alias"], r["drug_id"], r["source_id"]) for r in al).values() if v > 1))
add("aliases: drug_name lệch drugs.name", sum(r["drug_name"] != drugs[r["drug_id"]]["name"] for r in al if r["drug_id"] in drugs),
    next(((r["drug_name"], drugs[r["drug_id"]]["name"]) for r in al if r["drug_id"] in drugs and r["drug_name"] != drugs[r["drug_id"]]["name"]), None))
print("alias_type:", collections.Counter((r["alias_type"], r["status"]) for r in al).most_common())
add("aliases: alias chỉ toàn số", sum(bool(re.fullmatch(r"[\d %]+", r["alias"])) for r in al), next((r["alias"] for r in al if re.fullmatch(r"[\d %]+", r["alias"])), None))
noalias = set(drugs) - {r["drug_id"] for r in al}
add("drugs: hoạt chất không có alias nào", len(noalias), sorted(noalias)[:5])
# alias 'ok' trỏ tới nhiều hoạt chất không phải phối hợp (mơ hồ)
amb = collections.defaultdict(set)
for r in al:
    if r["status"] == "ok" and r["alias_type"] != "brand_vi":
        amb[r["alias"]].add(drugs[r["drug_id"]]["base_name"] if r["drug_id"] in drugs else r["drug_id"])
ambl = {k: v for k, v in amb.items() if len(v) > 1}
add("aliases: tên hoạt chất (ok) trỏ tới >1 hoạt chất gốc khác nhau", len(ambl), list(ambl.items())[:4])

pr = {r["product_id"]: r for r in D["products"]}
print("products.status:", collections.Counter(r["status"] for r in pr.values()))
print("route:", len(collections.Counter(r["route"] for r in pr.values())), "form_group:", collections.Counter(r["form_group"] for r in pr.values()).most_common(30))
print("route_source:", collections.Counter(r["route_source"] for r in pr.values()))
add("products: registration_no rỗng", sum(not r["registration_no"] for r in pr.values()))
rc = collections.Counter(r["registration_no"] for r in pr.values() if r["registration_no"])
add("products: trùng số đăng ký", sum(v - 1 for v in rc.values() if v > 1), [k for k, v in rc.items() if v > 1][:3])
add("products: active_ingredients rỗng", sum(not r["active_ingredients"] for r in pr.values()))
add("products: valid nhưng expiry_date đã qua (trước 2026-09-30)", sum(1 for r in pr.values() if r["status"] == "valid" and r["expiry_date"] and r["expiry_date"] < "2026-09-30"))
add("products: expired nhưng expiry_date còn hạn", sum(1 for r in pr.values() if r["status"] == "expired" and r["expiry_date"] and r["expiry_date"] >= "2026-09-30"))
add("products: expiry_date ngoài khoảng 2000-2040", sum(1 for r in pr.values() if r["expiry_date"] and not ("2000" <= r["expiry_date"][:4] <= "2040")),
    next((r["expiry_date"] for r in pr.values() if r["expiry_date"] and not ("2000" <= r["expiry_date"][:4] <= "2040")), None))
print("manufacturer_country top:", collections.Counter(r["manufacturer_country"] for r in pr.values()).most_common(12))
print("category:", collections.Counter(r["category"] for r in pr.values()).most_common(12))

pi = D["product_ingredients"]
print("pi status:", collections.Counter(r["status"] for r in pi), "route_match:", collections.Counter(r["route_match"] for r in pi))
add("product_ingredients: trùng (product_id, position)", sum(v - 1 for v in collections.Counter((r["product_id"], r["position"]) for r in pi).values() if v > 1))
add("product_ingredients: ok/suggest mà không có drug_id", sum(1 for r in pi if r["status"] in ("ok", "suggest") and not r["drug_id"]))
add("product_ingredients: unknown/excluded mà có drug_id DDInter", sum(1 for r in pi if r["status"] in ("unknown", "excluded") and r["drug_id"].startswith("DDInter")),
    next((tuple(r.values()) for r in pi if r["status"] in ("unknown", "excluded") and r["drug_id"].startswith("DDInter")), None))
add("product_ingredients: ingredient rỗng", sum(not r["ingredient"] for r in pi))
haspi = {r["product_id"] for r in pi}
add("products: không có dòng hoạt chất nào", sum(1 for k in pr if k not in haspi), [pr[k]["name"] for k in pr if k not in haspi][:3])
print("match_method:", collections.Counter((r["match_method"], r["status"]) for r in pi).most_common(30))

def multi(t, col):
    bad = [(r[col]) for r in D[t] for x in re.split(r"[;,]\s*", r[col]) if x and x not in drugs]
    add(f"{t}.{col}: drug_id trong danh sách không tồn tại", len(bad), bad[:2])
for t, col in [("ara_interactions", "victim_drug_ids"), ("ara_interactions", "ara_drug_ids"), ("pk_ddi", "perpetrator_id"),
               ("pk_ddi", "victim_id"), ("fda_labels", "drug_ids"), ("ingredient_map", "drug_ids"), ("ingredient_map", "dav_drug_id")]:
    multi(t, col)
for t in ["food_interactions", "disease_interactions", "duplication_classes"]:
    add(f"{t}: drug_name lệch drugs.name", sum(r["drug_name"] != drugs[r["drug_id"]]["name"] for r in D[t] if r["drug_id"] in drugs))
add("dosage_form_rules: tên lệch drugs.name", sum(r["drug_name"] != drugs[r["drug_id"]]["name"] or r["other_drug_name"] != drugs[r["other_drug_id"]]["name"] for r in D["dosage_form_rules"]),
    next(((r["drug_name"], drugs[r["drug_id"]]["name"], r["other_drug_name"], drugs[r["other_drug_id"]]["name"]) for r in D["dosage_form_rules"] if r["drug_name"] != drugs[r["drug_id"]]["name"] or r["other_drug_name"] != drugs[r["other_drug_id"]]["name"]), None))
fi = D["food_interactions"]
add("food_interactions: trùng (drug_id, food)", sum(v - 1 for v in collections.Counter((r["drug_id"], r["food"], r["description"]) for r in fi).values() if v > 1))
print("food:", len({r["food"] for r in fi}), "food_vi == food:", sum(r["food"] == r["food_vi"] for r in fi))
ds = D["disease_interactions"]
add("disease_interactions: trùng (drug_id, disease, description)", sum(v - 1 for v in collections.Counter((r["drug_id"], r["disease"], r["description"]) for r in ds).values() if v > 1))
add("disease_interactions: mesh_id sai mẫu", sum(1 for r in ds if r["mesh_id"] and not re.fullmatch(r"MESH:[DC]\d+(\|MESH:[DC]\d+)*", r["mesh_id"])), next((r["mesh_id"] for r in ds if r["mesh_id"] and not re.fullmatch(r"MESH:[DC]\d+(\|MESH:[DC]\d+)*", r["mesh_id"])), None))
add("duplication_classes: trùng (class, drug)", sum(v - 1 for v in collections.Counter((r["class_name"], r["drug_id"]) for r in D["duplication_classes"]).values() if v > 1))
pk_ = D["pk_ddi"]
add("pk_ddi: trùng (perpetrator, victim) theo DrugBank", sum(v - 1 for v in collections.Counter((r["perpetrator_drugbank"], r["victim_drugbank"]) for r in pk_).values() if v > 1))
add("pk_ddi: auc_fold_change <= 0", sum(float(r["auc_fold_change"]) <= 0 for r in pk_))
add("pk_ddi: không nối được cả hai phía", sum(1 for r in pk_ if not r["perpetrator_id"] or not r["victim_id"]))
print("pk magnitude:", collections.Counter(r["magnitude"] for r in pk_))
fl = D["fda_labels"]
add("fda_labels: effective_time sai", sum(1 for r in fl if not ("19900101" <= r["effective_time"] <= "20261004")), next((r["effective_time"] for r in fl if not ("19900101" <= r["effective_time"] <= "20261004")), None))
add("fda_labels: không nối được hoạt chất nào", sum(not r["drug_ids"] for r in fl))
add("fda_labels: mọi mục nội dung đều rỗng", sum(1 for r in fl if not any(r[c] for c in ["boxed_warning", "contraindications", "drug_interactions", "do_not_use", "ask_doctor_or_pharmacist"])))
ar = D["ara_interactions"]
print("ara table/effect/sev:", collections.Counter((r["table"], r["severity"]) for r in ar).most_common(), collections.Counter(r["ara_class"] for r in ar))
add("ara_interactions: victim không nối được drug_id", sum(not r["victim_drug_ids"] for r in ar), [r["victim"] for r in ar if not r["victim_drug_ids"]][:5])
print("sources:", [(r["source_id"], r["last_updated"]) for r in D["sources"]])
used_src = {r["source_id"] for t in D for r in D[t] if "source_id" in r}
add("sources: nguồn không bảng nào dùng", len(ids["sources"] - used_src), ids["sources"] - used_src)

print("\n===== VẤN ĐỀ (%d) =====" % len(issues))
for k, (n, ex) in issues.items():
    print(f"{n:>8,}  {k}" + (f"   vd: {ex!r}" if ex is not None else ""))
