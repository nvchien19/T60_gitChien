"""Tool 2 — interaction_lookup helpers thuantuy (khong DB session).

DB rows duoc truyen vao duoi dang dict tu repositories.
Quy tac lop 2 theo data/mvp/README.md + dosage_form_rules/ara_interactions.
"""

import math
from itertools import combinations


def _num_key(d: str) -> tuple:
    """Sap theo SO DDInter (numeric): DDInter999 < DDInter1000. DAV:* xep sau."""
    import re
    m = re.match(r"DDInter(\d+)$", d or "")
    if m:
        return (0, int(m.group(1)))
    return (1, d or "")


def sorted_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if _num_key(a) <= _num_key(b) else (b, a)


def all_pairs(drug_ids: list[str]) -> list[tuple[str, str]]:
    uniq = sorted(set(drug_ids))
    return [sorted_pair(a, b) for a, b in combinations(uniq, 2)]


def cross_input_pairs(groups: list[list[str]]) -> list[tuple[str, str]]:
    """Cap hoat chat giua HAI ten nhap khac nhau. `groups`: drug_ids cua tung ten nhap.

    Hai hoat chat chi nam chung trong mot biet duoc phoi hop khong tao thanh cap can tra.
    """
    out = {sorted_pair(a, b) for g1, g2 in combinations(groups, 2) for a in g1 for b in g2 if a != b}
    return sorted(out, key=lambda p: (_num_key(p[0]), _num_key(p[1])))


def cosine(u: list[float], v: list[float]) -> float:
    n = min(len(u), len(v))
    if n == 0:
        return 0.0
    dot = sum(u[i] * v[i] for i in range(n))
    nu = math.sqrt(sum(x * x for x in u[:n]))
    nv = math.sqrt(sum(x * x for x in v[:n]))
    if nu == 0 or nv == 0:
        return 0.0
    return dot / (nu * nv)


def apply_dosage_rule(base_sev: str | None, rule: dict, drug_route: str = "oral",
                      forms: frozenset[str] | set[str] = frozenset()) -> dict | None:
    """Tra ve finding lop2 hoac None neu rule khong ap dung.

    action: raise_severity (ap moi dang) / form_specific (dung form/route)
            / no_interaction_for_form (chi ha khi lop1 != contraindicated).
    forms: dang bao che nguoi dung NEU RO (vd {"tablet"}). Rong = khong biet -> van ap dung
           rule (thien ve canh bao, tranh bo sot).
    """
    action = rule.get("action", "")
    want_form = rule.get("drug_form") or "any"
    if action == "form_specific" and forms and want_form != "any" and want_form not in forms:
        return None
    if action == "raise_severity":
        return {"severity": rule.get("severity") or "contraindicated",
                "summary": rule.get("effect_vi", ""),
                "management": rule.get("management_vi", ""),
                "citations": [{"source_id": rule.get("source_id", "openfda"),
                               "label": rule.get("evidence", ""),
                               "record_id": rule.get("rule_id", ""),
                               "source_url": rule.get("source_url", "")}],
                "match_type": "exact", "layer": "dosage_form"}
    if action == "form_specific":
        want_route = rule.get("drug_route") or ""
        ok = True
        if want_route and want_route != "any" and drug_route != want_route:
            ok = False
        # form check do caller truyen drug_form qua drug_route neu can; don gian: chi check route
        if not ok:
            return None
        return {"severity": rule.get("severity") or base_sev or "moderate",
                "summary": rule.get("effect_vi", ""),
                "management": rule.get("management_vi", ""),
                "citations": [{"source_id": rule.get("source_id", "openfda"),
                               "label": rule.get("evidence", ""),
                               "record_id": rule.get("rule_id", ""),
                               "source_url": rule.get("source_url", "")}],
                "match_type": "exact", "layer": "dosage_form"}
    if action == "no_interaction_for_form":
        if (base_sev or "") == "contraindicated":
            return None
        return {"downgrade_only": True, "severity": rule.get("severity") or "minor",
                "citations": [{"source_id": rule.get("source_id", "openfda"),
                               "label": rule.get("evidence", ""),
                               "record_id": rule.get("rule_id", ""),
                               "source_url": rule.get("source_url", "")}],
                "match_type": "exact", "layer": "dosage_form"}
    return None


def ara_applies(ara: dict, victim_id: str, drug_routes: dict[str, str]) -> bool:
    """ARA chi ap dung khi victim dung DUONG UONG (route_scope=oral)."""
    if victim_id not in (ara.get("victim_drug_ids") or []):
        return False
    if (ara.get("route_scope") or "oral") == "oral" and drug_routes.get(victim_id, "oral") != "oral":
        return False
    if ara.get("victim_is_combination"):
        need = set(ara.get("victim_drug_ids") or [])
        if not need.issubset(set(drug_routes.keys())):
            return False
    return True
