"""Offline regression coverage for AU targeting, OSM mapping, and master exports."""
import csv
import importlib.util
from pathlib import Path

import pytest

from leadgen import get_vertical, run_pipeline
from leadgen import pipeline, sources
from leadgen.verticals.au_video_ops import is_relevant, lead_status, _enrich

SPEC = importlib.util.spec_from_file_location(
    "au_master", Path(__file__).resolve().parents[2] / "scripts/build_au_master_leads.py")
master = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(master)


@pytest.mark.parametrize("rec,expected", [
    ({"name": "Aeon Films", "category": "company"}, True),
    ({"name": "Mak Video", "category": "photographer"}, True),
    ({"name": "North", "category": "video_film_production"}, True),
    ({"name": "North", "category": "studio", "osm_tags": {"studio": "video"}}, True),
    ({"name": "Harbour Podcast Studio", "category": "studio"}, True),
    ({"name": "A Creative Agency", "category": "advertising_agency"}, True),
    ({"name": "Video Games Sydney", "category": "shop"}, False),
    ({"name": "Film Cameras", "category": "electronics"}, False),
    ({"name": "Video Ezy", "category": "video"}, False),
    ({"name": "City Cinema", "category": "cinema"}, False),
    ({"name": "Creative Accounting", "category": "accountant"}, False),
    ({"name": "ABC Media", "category": "company"}, False),
    ({"name": "Sydney Photos", "category": "photographer"}, False),
    ({"name": "Music Box", "category": "studio", "osm_tags": {"studio": "audio"}}, False),
    ({"name": "Stage 6", "category": "studio", "osm_tags": {"studio": "video"}}, False),
    ({"name": "Building 48, Fox Lighting", "osm_tags": {"studio": "video"}}, False),
    ({"name": "Creative Studio", "osm_tags": {"studio": "art; creative"}}, False),
    ({"name": "Muse Creative Content Studios", "category": "photographer"}, True),
    ({"name": "Zoom Productions", "category": "photographer"}, True),
    ({"name": "Unknown", "category": "studio", "osm_tags": {"studio": "radio;television"}}, True),
    ({"name": "Sound Stage Two", "osm_tags": {"studio": "video"}}, False),
    ({"name": "Hama Film Self Photo Studio", "category": "photographer"}, False),
])
def test_relevance(rec, expected):
    assert is_relevant(rec) is expected


@pytest.mark.parametrize("site,email,phone,status", [
    ("site", "hello@site", "02 9000 0000", "HOT"),
    ("site", "", "02 9000 0000", "WARM"),
    ("site", "hello@site", "", "WARM"),
    ("site", "", "", "COLD"),
    ("", "hello@site", "02 9000 0000", "UNKNOWN"),
    (None, None, None, "UNKNOWN"),
])
def test_simple_status(site, email, phone, status):
    assert lead_status({"website": site, "email": email, "phone": phone}) == status


def test_osm_pipeline_query_mapping_and_filter(monkeypatch, tmp_path):
    bbox = (-34.12, 150.6, -33.4, 151.4)
    monkeypatch.setattr(pipeline, "resolve_market", lambda _: (bbox, "Sydney"))
    bodies = []

    class Response:
        status_code = 200

        def json(self):
            return {"elements": [
                {"type": "node", "id": 1, "lat": -33.8, "lon": 151.1,
                 "tags": {"name": "North", "amenity": "studio", "studio": "video",
                          "contact:website": "https://north.test", "contact:phone": "02 9000 0000",
                          "contact:email": "hello@north.test", "addr:city": "Sydney"}},
                {"type": "node", "id": 2, "tags": {"name": "A Bank", "office": "company"}},
            ]}

    def post(url, *, data, **kwargs):
        bodies.append(data)
        return Response()

    monkeypatch.setattr(sources.requests, "post", post)
    enriched = []
    v = get_vertical("au_video_ops")
    monkeypatch.setattr(v, "enrich_fn", lambda r, ctx: enriched.append(r["name"]))
    records = run_pipeline(v, "Sydney", sources=("osm",),
                           out_stem=str(tmp_path / "sydney"), log=lambda _: None)
    assert len(records) == 1 and enriched == ["North"]
    assert records[0]["lead_status"] == "HOT"
    assert records[0]["phone"] == "02 9000 0000"  # not rewritten as a US number
    assert records[0]["source_url"] == "https://www.openstreetmap.org/node/1"
    assert 'nwr["office"="film"]' in bodies[0]
    assert 'nwr["studio"="video"]' in bodies[0]
    with (tmp_path / "sydney_crm.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["Business"] == "North" and rows[0]["Lead Status"] == "HOT"


def test_contact_enrichment_retains_listed_data():
    rec = {"website": "https://north.test", "phone": "02 9000 0000"}
    _enrich(rec, {"demo_html": lambda _: '<a href="mailto:hello@north.test">Email</a>'
             '<a href="tel:+61299999999">Phone</a>'})
    assert rec["phone"] == "02 9000 0000" and rec["email"] == "hello@north.test"


def test_failed_sole_osm_source_does_not_overwrite_exports(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "resolve_market", lambda _: ((0, 0, 1, 1), "Sydney"))

    def failed(*args):
        raise RuntimeError("all mirrors failed")

    monkeypatch.setattr(pipeline, "osm_collect", failed)
    path = tmp_path / "sydney_crm.csv"
    path.write_text("existing leads\n")
    with pytest.raises(RuntimeError, match="OSM collection failed"):
        run_pipeline(get_vertical("au_video_ops"), "Sydney", sources=("osm",),
                     out_stem=str(tmp_path / "sydney"), log=lambda _: None)
    assert path.read_text() == "existing leads\n"


def test_contact_failure_retains_business(monkeypatch):
    import leadgen.verticals.au_video_ops as v
    monkeypatch.setattr(v, "fetch", lambda _: None)
    rec = {"name": "North Films", "website": "https://north.test", "phone": "02 9000 0000"}
    assert _enrich(rec, {}) is rec
    assert lead_status(rec) == "WARM" and rec["enrich_error"]


def test_master_merges_contacts_and_preserves_branches():
    records = [
        {"name": "North Films", "city": "Sydney", "website": "https://www.north.test"},
        {"name": "North Video", "city": "Sydney", "website": "http://north.test/contact",
         "email": "hello@north.test", "phone": "02 9000 0000"},
        {"name": "North Film Co", "city": "Sydney", "phone": "+61 2 9000 0000"},
        {"name": "North Films", "city": "Melbourne", "website": "https://north.test"},
        {"name": "Local Films", "city": "Sydney", "address": "1 A St"},
        {"name": "Local Films", "city": "Sydney", "address": "2 B St"},
        {"name": "LOCAL FILMS", "city": "Sydney", "address": "1 A St", "email": "hi@local.test"},
    ]
    merged = master.dedupe_master(records)
    assert len(merged) == 4
    assert merged[0]["lead_status"] == "HOT"
    assert merged[1]["city"] == "Melbourne"
    assert merged[2]["email"] == "hi@local.test"


def test_empty_cache_is_refreshed_and_failure_retains_outputs(monkeypatch, tmp_path):
    path = tmp_path / "sydney_au_video_ops_crm.csv"
    path.write_text(",".join(h for h, _ in master.MASTER_COLUMNS) + "\n")
    assert master.read_cached(path) == []
    before = path.read_bytes()
    old_master = tmp_path / "australia_leads_master.csv"
    old_master.write_text("existing output\n")

    def failed(*args, **kwargs):
        kwargs["log"]("  OSM failed: network blocked")
        return []

    monkeypatch.setattr(master, "run_pipeline", failed)
    assert master.main(["--reuse", "--out-dir", str(tmp_path), "--markets", "Sydney"]) == 1
    assert path.read_bytes() == before
    assert old_master.read_text() == "existing output\n"


def test_master_script_exports_pipeline_result(monkeypatch, tmp_path):
    monkeypatch.setattr(master, "run_pipeline", lambda *a, **k: [
        {"name": "North Films", "website": "https://north.test", "why": "COLD",
         "vertical": "au_video_ops", "lead_status": "COLD", "source": "osm"}])
    assert master.main(["--out-dir", str(tmp_path), "--no-enrich", "--markets", "Sydney"]) == 0
    with (tmp_path / "australia_leads_master.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1 and rows[0]["City"] == "Sydney"
    assert rows[0]["State"] == "NSW" and rows[0]["Lead Status"] == "COLD"
    monkeypatch.setattr(master, "run_pipeline", lambda *a, **k: pytest.fail("cache not reused"))
    assert master.main(["--out-dir", str(tmp_path), "--reuse", "--markets", "Sydney"]) == 0


def test_five_markets_keep_separate_city_exports(monkeypatch, tmp_path):
    def collect(v, market, **kwargs):
        return [{"name": "North Films", "website": "https://north.test", "why": "COLD",
                 "vertical": "au_video_ops", "lead_status": "COLD", "source": "osm"}]

    monkeypatch.setattr(master, "run_pipeline", collect)
    assert master.main(["--out-dir", str(tmp_path), "--no-enrich"]) == 0
    with (tmp_path / "australia_leads_master.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert {r["City"] for r in rows} == set(master.MARKETS)
    assert {r["State"] for r in rows} == {"NSW", "VIC", "QLD", "WA", "SA"}
    assert len(list(tmp_path.glob('*_crm.csv'))) == 5
