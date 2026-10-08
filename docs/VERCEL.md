# Vercel services

The repository deploys as two Flask services in one Vercel project:

| Service | Root / entry point | Public routing | Calls |
| --- | --- | --- | --- |
| `app` | `.` / `app.py` | Internal; no public rewrite | None |
| `gui` | `gui` / `vercel_app.py` | `/(.*)` | `app` through `LEADGEN_API_URL` |

`vercel.json` contains the complete service definitions. The binding is on the
calling `gui` service. Vercel injects `LEADGEN_API_URL` at function runtime; do not
set it in project settings, `.env` files, or build commands. The frontend reads it
inside each request and preserves any path prefix in the bound URL. The browser
calls same-origin `/run`, `/check`, and `/recent`; its requests go to the public
GUI, which forwards the relevant operations to the internal API. `/health` checks
the bound API. `/metadata` is an API-only route, without a public frontend route.

Use repository root `.` in Vercel project settings, with no top-level build/runtime
overrides; the two services declare their own Flask framework and entry points.
Python is pinned to 3.12. Root dependencies include Flask for the API; the GUI's
own `pyproject.toml` declares only Flask and requests, without requiring the core
engine or native desktop dependencies in its service build.

## Test locally

Install Vercel CLI 63.0.2 or newer and run from the repository root:

```bash
# Leave any activated Python virtual environment first; Vercel manages its own.
vercel dev --local
```

This starts both services and injects the binding without linking an account.
To test with linked project settings instead, use `vercel dev` after `vercel link`.
Open the local address the CLI prints and click “Try a sample”. The sample uses
the bundled web-design fixtures (five fictional businesses), exercising the same
internal service request and CSV/XLSX download flow without live network access.
For AU collection, the default vertical is `au_video_ops`; enter Sydney or another
AU city. Only OSM is enabled for hosted collection. The CLI collector continues
to provide the existing multi-city master workflow.

The configuration was validated with Vercel CLI 63.0.2's bundled schema, and
`vercel dev --local` was exercised with both services: public page, bound API
health, five-lead demo, CSV/XLSX payloads, and browser script syntax. Regression
checks run with `python -m pytest leadgen/tests -q` and `python gui/test_gui.py`.
Cloud deployment/build on a linked Vercel account has not been tested.

## Hosted execution

The hosted API completes collection inside the request. It returns preview rows,
counts, logs, and encoded exports together. The browser creates download links
from those exports; no later request needs an in-memory job ID or files on a
different function instance. Temporary output files are cleaned up per invocation.
The shared template also supports the original local GUI's background jobs,
progress polling, history, and server-side downloads. The desktop build recipe
includes the extracted template.

Hosted runs export up to 200 rows and visit at most 20 websites. Both service
functions request a 300-second maximum duration; the frontend's API timeout is
280 seconds. Vercel plan limits still apply, and slow upstream requests can time
out. Completed downloads live in the browser session; persistent job history,
durable scheduled collection, and background execution are not provided here.
Use the Python CLI/persistent host for larger runs. Overture remains outside the
hosted test flow while its schema compatibility is unresolved.

`.vercelignore` excludes generated outputs, CSV/XLSX, virtual environments, caches,
and private local configuration from uploads. `vercel.json` is
explicitly unignored; `.vercel/` project metadata remains ignored. The service
names, routing, binding, and hosted limits have been confirmed. Import or link
`axelworkspace/au-lead-hunter` and deploy using its repository-root config.
A cloud deployment still needs a linked Vercel account.
