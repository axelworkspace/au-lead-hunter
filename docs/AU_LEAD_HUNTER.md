# AU Lead Hunter

Find Australian video-production, videography, and content/creative businesses
that could use editing or project support. Contact availability determines lead
status; this tool does not claim businesses are hiring. Missing decision makers
and unreachable websites do not disqualify an otherwise relevant business.

From the repository root:

```bash
source .venv/bin/activate
python scripts/build_au_master_leads.py --markets Sydney
# After reviewing Sydney, collect the five supported cities:
python scripts/build_au_master_leads.py
```

Cities: Sydney, Melbourne, Brisbane, Perth, Adelaide. The collector reuses the
existing leadgen pipeline with the `au_video_ops` vertical and OSM. It does not
run Overture or the optional historical research chain. The original Overture
vertical is preserved as `au_video_ops_overture`, including its scoring, pitch
angles, and export columns. The research/approval scripts from the newer main
branch remain available unchanged.

Outputs under `outputs/au_master/`:

- `<city>_au_video_ops_crm.csv` and `<city>_au_video_ops.xlsx`
- `australia_leads_master.csv` combining the selected cities

The master contains business, contact name/role (when available), city/state,
website, email, phone, LinkedIn, address, category, vertical, source/source URL,
and lead status. Missing city/state are filled from the queried market; the city
CSV's Notes column marks those fallbacks rather than claiming verified addresses.

Statuses: HOT = website + email + phone; WARM = website + either email or phone;
COLD = website only; UNKNOWN = no website, even if other contacts exist. These
reflect available fields, not independently verified reachability or hiring intent.

Default enrichment visits each listed homepage once, up to 150 businesses per
city, to extract email, `tel:` links, and social links. Use `--no-enrich` to retain
only source-listed contacts, or `--enrich-cap N` to adjust the cap. Nothing invents
contacts or makes decision-maker research mandatory.

Fresh collection is the default. `--reuse` explicitly reuses valid, nonempty city
CSVs and retries missing/empty ones; it skips homepage enrichment for reused rows.
After changing targeting or refreshing contacts, omit `--reuse`.
Collection failure returns a nonzero exit status and retains existing outputs;
if a city fails, successful city files remain available and the existing master
is preserved. Retry with `--reuse` to resume. A successful smaller market selection
replaces the master with that selected scope.

Master dedupe prefers normalized website hostname, AU phone, then name/location.
Known different cities, states, or addresses are retained as distinct branches.
The existing engine also deduplicates each city's raw records before export.

OSM `osm_tags` are a list of literal `key=value` strings or bare keys, ORed by
`leadgen.sources._overpass_body`. They are not regexes or raw Overpass expressions.
The vertical discovers selected office types, photographers, and studios, then filters
by video category, studio media, business name, or an OSM description. Numbered
sound stages, facility buildings, retail video, cinemas, and art-only studios are
excluded. Generic words like “media” or “creative” alone do not qualify a record.
OSM business coverage is sparse; it is not a comprehensive AU company directory.
Large broadcasters may remain because they have relevant internal video workflows.

Cloud network settings must allow `nominatim.openstreetmap.org`, `overpass-api.de`,
`overpass.kumi.systems`, and `overpass.private.coffee`. Homepage enrichment also
needs the actual website and any redirect destinations allowed. A blocked homepage
retains existing contacts and records an enrichment error. No API keys are required.

```bash
python -m leadgen --vertical au_video_ops \
  --market "Sydney, New South Wales, Australia" --sources osm \
  --out outputs/au_master/sydney_au_video_ops
python -m pytest leadgen/tests -q
```

Use the wrapper to create the output directory automatically. Generated CSV/XLSX
files are already Git-ignored. OSM source URLs remain in the export; derived data
uses OpenStreetMap's ODbL license and requires appropriate attribution.

## Initial validated collection (8 October 2026)

The final live run used the focused OSM query with homepage enrichment disabled:

| City | Raw named OSM candidates | Relevant / deduped / scored | A / B / C |
| --- | ---: | ---: | --- |
| Sydney | 347 | 14 | 1 / 1 / 12 |
| Melbourne | 469 | 10 | 1 / 2 / 7 |
| Brisbane | 231 | 10 | 2 / 1 / 7 |
| Perth | 206 | 2 | 0 / 0 / 2 |
| Adelaide | 140 | 1 | 0 / 0 / 1 |

The master contains 37 unique businesses: 4 HOT, 4 WARM, 8 COLD, 21 UNKNOWN.
16 have websites, 6 have emails, 7 have phones, and 22 have addresses.
Examples include Thor Productions, Cutting Edge, HERO SHOT Corporate Headshots
& Video, Taxi Film Production, Traffic Film Production, and GLUE Content.

Name/category review removed numbered stages, art-only studios, and self-service
photo studios. A measured false-positive rate would require independent company
verification, which was not performed. Contact availability and hiring intent
remain unverified. This sparse OSM sample does not demonstrate hundreds/thousands
of AU prospects; broader public-source coverage would be a separate improvement.

Overpass returned transient rate-limit/time-out/server errors during collection.
Smaller office selectors retained Sydney's selected prospects while reducing the
query size; service-status checks and a later Adelaide retry completed collection.
Tests: 264 engine tests passed, plus the existing GUI end-to-end checks. All five
city workbooks and the master CSV's columns/statuses were validated. Homepage
requests were blocked by the cloud allowlist; source-listed contacts were retained.
Required API and discovered-website domain additions and startup instructions were
saved to the environment draft for review. Publication/new-task restoration have
not been verified. The handoff's newer local commits were absent from this checkout;
the focused vertical and collector were recreated on the available engine.

## Contact enrichment follow-up (8 October 2026)

Homepage access now works for the allowed website destinations. Live enrichment
across all five cities retained all 37 leads and all previously available contact
fields. The updated master contains 5 HOT, 5 WARM, 6 COLD, and 21 UNKNOWN leads,
with 16 websites, 8 emails, 8 phones, and 2 LinkedIn profiles.

New fields were extracted for HERO SHOT Corporate Headshots & Video (email and
LinkedIn), The Studio Forest Hill (email), and Docklands Studios Melbourne (phone
and LinkedIn). Docklands succeeded on a later homepage retry. CSV status logic and
all five city workbooks were validated. These are extracted contact fields;
deliverability and hiring intent were not verified.

Taxi Film returned HTTP 403, Cutting Edge returned HTTP 503, and Vine Street
returned HTTP 404 during checks. Their records and source-listed details were
retained. Redirect destinations `sevenwestmedia.com.au`, `www.dcfstudios.com.au`,
and `villageroadshowstudios.com.au` were added to the saved network draft; requests
following those redirects succeeded. Review/save and publication of the updated
draft remain separate platform actions.
