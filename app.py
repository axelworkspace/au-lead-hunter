"""Internal, stateless Vercel API. Collection finishes within the request."""
import base64
import json
import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request

from leadgen import all_verticals, get_vertical, run_pipeline
from leadgen.diagnostics import check_connectivity
from leadgen.export import write_outputs
from leadgen.geo import MARKETS
from leadgen.pipeline import load_crm_names

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024


@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return jsonify(status="ok", service="app")


@app.get("/metadata")
def metadata():
    return jsonify(verticals=[
        {"key": key, "label": v.label, "description": v.description,
         "competitor_input": v.competitor_input, "default_sources": ["osm"]}
        for key, v in sorted(all_verticals().items()) if v.osm_tags
    ], markets=sorted(MARKETS), default_vertical="au_video_ops")


@app.get("/check")
def check():
    return jsonify(check_connectivity())


def _bounded_int(params, key, default, maximum):
    value = params.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{key} must be an integer") from None
    if number < 0:
        raise ValueError(f"{key} must be nonnegative")
    return min(number, maximum)


@app.post("/run")
def collect():
    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify(error="Send a JSON object."), 400
    try:
        vertical = get_vertical(params.get("vertical") or "au_video_ops")
        if not vertical.osm_tags:
            raise ValueError("This vertical requires a source outside hosted OSM collection.")
        market = (params.get("market") or "").strip()
        demo = params.get("demo", False)
        enrich = params.get("enrich", True)
        if not isinstance(demo, bool) or not isinstance(enrich, bool):
            raise ValueError("demo and enrich must be booleans")
        if not demo and not market:
            raise ValueError("market is required (or use Demo mode)")
        sources = params.get("sources") or ["osm"]
        if not isinstance(sources, list) or any(s != "osm" for s in sources):
            raise ValueError("Hosted collection currently supports live map data (OSM).")
        limit = _bounded_int(params, "limit", 200, 200) or 200
        cap = _bounded_int(params, "enrich_cap", 20, 20)
        crm = params.get("crm_csv") or ""
        if not isinstance(crm, str):
            raise ValueError("crm_csv must be text")
        exclude = load_crm_names(crm, is_text=True) if crm else None
    except (KeyError, ValueError, AttributeError, TypeError) as exc:
        return jsonify(error=str(exc)), 400

    logs = []
    try:
        # Temporary output files belong to this invocation only. No global job
        # store, detached thread, or later request is needed to retrieve them.
        with tempfile.TemporaryDirectory(prefix="au-leads-") as output_dir:
            leads = run_pipeline(
                vertical, market or "(demo)", sources=("osm",), limit=limit,
                enrich=enrich, enrich_cap=cap, exclude_names=exclude,
                demo=demo, log=logs.append,
            )
            if len(leads) > limit:
                logs.append(f"Showing/exporting the first {limit} of {len(leads)} leads.")
            leads = leads[:limit]
            stem = str(Path(output_dir) / "leads")
            csv_path, xlsx_path = write_outputs(leads, vertical.columns, stem, lambda _: None)
            logs.append("Prepared CSV and Excel downloads.")
            exports = {
                kind: {"name": f"{vertical.key}.{kind}", "mime": mime,
                       "data": base64.b64encode(Path(path).read_bytes()).decode("ascii")}
                for kind, path, mime in [
                    ("csv", csv_path, "text/csv;charset=utf-8"),
                    ("xlsx", xlsx_path,
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ]
            }
        stats = {tier: sum(r.get("tier") == tier for r in leads) for tier in "ABC"}
        payload = {"done": True, "error": None, "log": logs,
                   "stats": {"total": len(leads), **stats}, "leads": leads,
                   "columns": vertical.columns, "exports": exports,
                   "notice": None if leads else "No matching businesses returned."}
        if len(json.dumps(payload).encode("utf-8")) > 3_000_000:
            return jsonify(error="Results are too large; lower the collect limit."), 413
        return jsonify(payload)
    except (ValueError, RuntimeError) as exc:
        return jsonify(error=str(exc), done=True, log=logs), 502
    except Exception:
        app.logger.exception("Collection failed")
        return jsonify(error="Collection failed. Please retry or try the offline sample.",
                       done=True, log=logs), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5001)))
