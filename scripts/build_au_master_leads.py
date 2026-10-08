#!/usr/bin/env python3
"""Collect AU video prospects using the existing engine; never reuse empty CSVs."""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leadgen import get_vertical, run_pipeline
from leadgen.audit import hostname, is_weak_url
from leadgen.export import write_csv, write_outputs
from leadgen.quality import merge_records
from leadgen.verticals.au_video_ops import MASTER_COLUMNS, lead_status

# Sydney was reviewed first; collect other markets sequentially through OSM.
MARKETS = {
    "Sydney": ("Sydney, New South Wales, Australia", "NSW"),
    "Melbourne": ("Melbourne, Victoria, Australia", "VIC"),
    "Brisbane": ("Brisbane, Queensland, Australia", "QLD"),
    "Perth": ("Perth, Western Australia, Australia", "WA"),
    "Adelaide": ("Adelaide, South Australia, Australia", "SA"),
}


def _text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10 and digits.startswith("0"):
        digits = "61" + digits[1:]
    if digits.startswith("0061"):
        digits = digits[2:]
    return digits


def _identities(rec: dict) -> list[tuple]:
    keys = []
    site = rec.get("website") or ""
    if site and not is_weak_url(site)[0]:
        domain = hostname(site).removeprefix("www.")
        if domain:
            keys.append(("domain", domain))
    phone = _phone(rec.get("phone") or "")
    if phone:
        keys.append(("phone", phone))
    name = _text(rec.get("name") or "")
    if name:
        keys.append(("name", name, _text(rec.get("city") or ""),
                     _text(rec.get("state") or "")))
    return keys


def _different_branches(a: dict, b: dict) -> bool:
    for field in ("city", "state", "address"):
        av, bv = _text(a.get(field) or ""), _text(b.get(field) or "")
        if av and bv and av != bv:
            return True
    return False


def dedupe_master(records: list[dict]) -> list[dict]:
    """Domain, then AU phone, then name/location; retain distinct known branches."""
    out = []
    index: dict[tuple, list[dict]] = {}
    for rec in records:
        rec = dict(rec)
        target = None
        for key in _identities(rec):
            target = next((r for r in index.get(key, [])
                           if not _different_branches(r, rec)), None)
            if target is not None:
                break
        if target is None:
            target = rec
            out.append(target)
        else:
            merge_records(target, rec)
            for field in ("contact_name", "role", "linkedin", "vertical"):
                if not target.get(field) and rec.get(field):
                    target[field] = rec[field]
        for key in set(_identities(target) + _identities(rec)):
            bucket = index.setdefault(key, [])
            if not any(r is target for r in bucket):
                bucket.append(target)
    for rec in out:
        rec["lead_status"] = lead_status(rec)
    return out


def read_cached(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {h for h, _ in MASTER_COLUMNS}
        if not required.issubset(reader.fieldnames or []):
            return []
        return [{key: row.get(header, "") for header, key in MASTER_COLUMNS}
                for row in reader if (row.get("Business") or "").strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs/au_master")
    parser.add_argument("--markets", nargs="+", choices=list(MARKETS), default=list(MARKETS))
    parser.add_argument("--reuse", action="store_true", help="reuse nonempty per-market CSVs")
    parser.add_argument("--no-enrich", action="store_true", help="skip homepage requests")
    parser.add_argument("--enrich-cap", type=int, default=150)
    args = parser.parse_args(argv)
    if args.enrich_cap < 0:
        parser.error("--enrich-cap must be nonnegative")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    all_records = []
    failed_markets = []
    for city in dict.fromkeys(args.markets):
        market, state = MARKETS[city]
        stem = args.out_dir / f"{city.lower()}_au_video_ops"
        csv_path = Path(f"{stem}_crm.csv")
        records = read_cached(csv_path) if args.reuse else []
        if records:
            all_records.extend(records)
            continue
        messages = []

        def log(message):
            messages.append(str(message))
            print(message, flush=True)

        try:
            records = run_pipeline(
                get_vertical("au_video_ops"), market, sources=("osm",),
                enrich=not args.no_enrich, enrich_cap=args.enrich_cap, log=log,
            )
        except (ValueError, RuntimeError) as exc:
            print(f"{city} collection failed: {exc}. Existing outputs retained.", file=sys.stderr)
            failed_markets.append(city)
            continue
        if any("OSM failed:" in message for message in messages):
            print("OSM collection failed. Existing outputs retained.", file=sys.stderr)
            failed_markets.append(city)
            continue
        if not records:
            print(f"No relevant {city} businesses returned; inspect source coverage. "
                  "Existing outputs retained.", file=sys.stderr)
            failed_markets.append(city)
            continue
        for rec in records:
            # City/state fallbacks describe the queried market, not a verified address.
            if not rec.get("city") or not rec.get("state"):
                rec["why"] += f"; missing location filled from {city} market"
            rec["city"] = rec.get("city") or city
            rec["state"] = rec.get("state") or state
        write_outputs(records, get_vertical("au_video_ops").columns, str(stem))
        all_records.extend(records)
    if failed_markets:
        print(f"Incomplete collection: {', '.join(failed_markets)}. Successful city files saved; "
              "existing master CSV retained. Retry with --reuse.", file=sys.stderr)
        return 1
    master = dedupe_master(all_records)
    master_path = args.out_dir / "australia_leads_master.csv"
    with tempfile.NamedTemporaryFile(dir=args.out_dir, suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)
    try:
        write_csv(master, MASTER_COLUMNS, str(temp_path))
        os.replace(temp_path, master_path)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"Collected/cached {len(all_records)} rows; {len(master)} unique businesses")
    print("Lead status:", dict(Counter(r["lead_status"] for r in master)))
    print(f"Master CSV: {master_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
