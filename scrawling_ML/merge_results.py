# merge_listings.py
import json
import re
import csv
from collections import OrderedDict
from pathlib import Path
import unicodedata

# -------- Helpers --------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_text(s):
    if s is None:
        return None
    s = str(s).strip()
    s = unicodedata.normalize("NFKC", s)
    return s

def parse_int(v):
    if v is None:
        return None
    s = str(v)
    # remove non-digit except minus
    s2 = re.sub(r"[^\d\-]", "", s)
    try:
        return int(s2) if s2 != "" else None
    except ValueError:
        return None

def canonicalize_location(loc):
    if not loc:
        return None
    # common separators: ',', '/', '|', '-'
    parts = re.split(r"[,/|-]", loc)
    parts = [p.strip().title() for p in parts if p.strip()]
    if not parts:
        return None
    # join first two if exist
    return ", ".join(parts[:2])

def fingerprint(rec):
    t = (rec.get("title") or "").lower()
    t = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", t)).strip()
    y = rec.get("year") or ""
    p = str(rec.get("price") or "")
    return f"{t}|{y}|{p}"

def normalize_listing(raw, source_label):
    # map possible field names
    title = normalize_text(raw.get("title") or raw.get("name") or "")
    price = parse_int(raw.get("price"))
    mileage = parse_int(raw.get("mileage_km") or raw.get("mileage"))
    year = parse_int(raw.get("year"))
    model = normalize_text(raw.get("model") or "")
    province_city = canonicalize_location(raw.get("province_city") or raw.get("location") or raw.get("city"))
    link = normalize_text(raw.get("link") or raw.get("url"))
    # extra fields preserved minimally
    extra = {}
    for k in raw.keys():
        if k not in {"title","price","mileage_km","mileage","year","model","province_city","location","link","url"}:
            extra[k] = raw[k]
    ordered = OrderedDict([
        ("title", title or None),
        ("price", price),
        ("mileage_km", mileage),
        ("year", year),
        ("model", model or None),
        ("province_city", province_city or None),
        ("link", link or None),
        ("source", source_label),
        ("extra", extra or None)
    ])
    return ordered

# -------- Main merge flow --------
def merge_files(autotrader_path, kijiji_path, out_json="result.json", out_ndjson="merged.ndjson", out_csv="merged.csv"):
    a = load_json(autotrader_path)
    k = load_json(kijiji_path)

    listings = []
    # load autotrader
    src = a.get("source") or "autotrader"
    a_list = a.get("listings") if isinstance(a.get("listings"), list) else []
    for item in a_list:
        listings.append(normalize_listing(item, src))

    # load kijiji
    src = k.get("source") or "kijiji"
    k_list = k.get("listings") if isinstance(k.get("listings"), list) else []
    for item in k_list:
        listings.append(normalize_listing(item, src))

    # dedupe: link preferred, then fingerprint
    seen_links = set()
    seen_fp = set()
    merged = []
    for rec in listings:
        link = rec.get("link")
        if link:
            if link in seen_links:
                continue
            seen_links.add(link)
        fp = fingerprint(rec)
        if fp in seen_fp:
            continue
        seen_fp.add(fp)
        merged.append(rec)

    # write JSON with metadata
    out_obj = {
        "brand": a.get("brand") or k.get("brand") or None,
        "location": a.get("location") or k.get("location") or None,
        "total_number_merged": len(merged),
        "listings": merged
    }
    Path(out_json).write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Merged {len(merged)} listings -> {out_json}")

# -------- Run if executed as script --------
if __name__ == "__main__":
    merge_files("results/autotrader_result.json", "results/kijiji_result.json")

