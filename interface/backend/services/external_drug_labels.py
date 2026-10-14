"""Read public labels from a fixed FDA endpoint; never infer DDI severity."""
import asyncio
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from time import monotonic
from uuid import UUID

import httpx

from interface.backend.config import get_settings

ENDPOINT = "https://api.fda.gov/drug/label.json"
FIELDS = {
    "indications_and_usage": "Chỉ định theo nhãn",
    "purpose": "Mục đích theo nhãn",
    "warnings": "Cảnh báo",
    "contraindications": "Chống chỉ định",
    "adverse_reactions": "Tác dụng không mong muốn",
    "drug_interactions": "Thông tin tương tác trong nhãn",
}


@dataclass
class LabelResult:
    status: str
    name: str
    sections: dict[str, str] = field(default_factory=dict)
    url: str = ""
    updated: str = ""


_cache: OrderedDict[str, tuple[float, LabelResult]] = OrderedDict()
_slots = asyncio.Semaphore(4)


def valid_name(name: str) -> bool:
    # Only names, never full chat messages, patient data, URLs or query syntax.
    return bool(re.fullmatch(r"[A-Za-zÀ-ỹ][A-Za-zÀ-ỹ0-9 +()./-]{1,99}", name))


def _names(record: dict) -> list[str]:
    data = record.get("openfda", {})
    if not isinstance(data, dict):
        return []
    return [value for key in ("generic_name", "brand_name")
            if isinstance(data.get(key), list)
            for value in data[key] if isinstance(value, str)]


async def lookup_label(name: str) -> LabelResult:
    settings = get_settings()
    name = name.strip()
    if not settings.external_drug_lookup_enabled or not valid_name(name):
        return LabelResult("unavailable", name)
    key = name.casefold()
    cached = _cache.get(key)
    if cached and cached[0] > monotonic():
        _cache.move_to_end(key)
        return cached[1]
    # FDA exact fields are case-sensitive and many labels use UPPERCASE.
    variants = list(dict.fromkeys((name, name.upper(), name.lower(), name.title())))
    params = {
        "search": " OR ".join(f'openfda.{column}.exact:"{variant}"'
                              for column in ("generic_name", "brand_name")
                              for variant in variants),
        "limit": 10,
        "sort": "effective_time:desc",
    }
    if settings.openfda_api_key:
        params["api_key"] = settings.openfda_api_key
    try:
        async with asyncio.timeout(settings.external_drug_timeout_s):
            async with _slots:
                async with httpx.AsyncClient(timeout=settings.external_drug_timeout_s,
                                             follow_redirects=False) as client:
                    response = await client.get(ENDPOINT, params=params)
        if response.status_code == 404:
            payload = response.json()
            if payload.get("error", {}).get("code") != "NOT_FOUND":
                return LabelResult("unavailable", name)
            result = LabelResult("not_found", name)
        else:
            response.raise_for_status()
            records = response.json().get("results")
            if not isinstance(records, list):
                return LabelResult("unavailable", name)
            result = LabelResult("not_found", name)
            for record in records:
                if not isinstance(record, dict) or key not in [n.casefold() for n in _names(record)]:
                    continue
                # Require a concrete, validated record link for attribution.
                set_id = str(UUID(record["set_id"]))
                sections = {}
                for column in FIELDS:
                    values = record.get(column, [])
                    if isinstance(values, list):
                        text = " ".join(v for v in values if isinstance(v, str))
                        text = re.sub(r"<[^>]*>", " ", text)
                        text = re.sub(r"\s+", " ", text).strip()
                        if text:
                            sections[column] = text[:1600] + ("… [trích đoạn]" if len(text) > 1600 else "")
                if sections:
                    updated = record.get("effective_time", "")
                    result = LabelResult("found", name, sections,
                                         f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}",
                                         updated if isinstance(updated, str) and re.fullmatch(r"\d{8}", updated) else "")
                    break
    except (httpx.HTTPError, TimeoutError, ValueError, TypeError, KeyError, AttributeError):
        # Do not log the request URL: it may contain a provider key.
        return LabelResult("unavailable", name)
    _cache[key] = (monotonic() + (3600 if result.status == "found" else 300), result)
    _cache.move_to_end(key)
    while len(_cache) > 256:
        _cache.popitem(last=False)
    return result
