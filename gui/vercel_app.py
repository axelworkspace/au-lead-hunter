"""Public Vercel GUI. Calls the API through its runtime-injected service binding."""
import os
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024


def call_api(path, *, body=None):
    # Bindings exist at function runtime, never at build time. Preserve any path
    # prefix in the bound URL. No localhost, production hostname, or manual env
    # fallback is substituted when the binding is missing.
    base = os.environ.get("LEADGEN_API_URL")
    if not base:
        raise RuntimeError("The API service binding is missing.")
    url = base.rstrip("/") + "/" + path.lstrip("/")
    response = requests.request(
        "POST" if body is not None else "GET", url, json=body,
        timeout=(10, 280), allow_redirects=False,
    )
    return response.json(), response.status_code


@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(RuntimeError)
def missing_binding(error):
    return jsonify(error=str(error)), 503


@app.errorhandler(requests.RequestException)
@app.errorhandler(ValueError)
def unavailable_api(error):
    return jsonify(error="The lead service is unavailable. Please retry."), 502


@app.get("/")
def index():
    metadata, status = call_api("metadata")
    if status != 200:
        return jsonify(metadata), status
    return render_template("index.html", verticals=metadata["verticals"],
                           markets=metadata["markets"], serverless=True,
                           default_vertical=metadata["default_vertical"])


@app.get("/health")
def health():
    body, status = call_api("health")
    return jsonify(body), status


@app.post("/run")
def collect():
    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify(error="Send a JSON object."), 400
    body, status = call_api("run", body=params)
    return jsonify(body), status


@app.get("/check")
def check():
    body, status = call_api("check")
    return jsonify(body), status


@app.get("/recent")
def recent():
    # Completed results/downloads live in this browser session, not a shared
    # server process. No persistent history is promised in this deployment.
    return jsonify([])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
