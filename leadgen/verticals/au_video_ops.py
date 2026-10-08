"""Australian video/content businesses for editing and project support.

OSM filters are literal key=value strings (ORed), never raw Overpass syntax.
Selected office types and studios provide discovery coverage; the relevance gate
keeps only video categories or specific business-name context.
"""
from __future__ import annotations

import re
from html import unescape

from .. import Vertical, register
from ..audit import fetch
from ..signals import detect_socials, find_emails

CORE_CATEGORIES = {
    "videographer", "video_film_production", "audio_visual_production_and_design",
    "film_production", "video_production", "film",
}
SECONDARY_CATEGORIES = {
    "broadcasting_media_production", "media_agency", "real_estate_photography",
    "event_photography", "advertising_agency", "photographer", "photography", "studio",
}
EXCLUDED_CATEGORIES = {
    "video", "video_games", "video_game_store", "video_game_critic", "cinema",
    "music_production", "theatrical_productions", "print_media", "mass_media",
    "photography_classes", "electronics", "camera", "copyshop",
}
VIDEO_NAME = re.compile(
    r"\b(?:videos?|videograph(?:er|ers|y)|films?|filmmak(?:er|ers|ing)|"
    r"cinematograph(?:er|ers|y))\b|"
    r"\b(?:video|film|media|commercial|corporate|content|creative) production(?:s)?\b|"
    r"\bproduction (?:house|studios?)\b|"
    r"\b(?:content|creative|podcast|video) (?:studios?|agenc(?:y|ies))\b|"
    r"\breal estate (?:media|video)\b", re.I,
)
EXCLUDED_NAME = re.compile(
    r"\b(?:video games?|video rentals?|dvd|cinema tickets?|photography classes|"
    r"self photo studio|photo booth)\b|"
    r"^(?:stage|sound ?stage|building)\s*(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
    re.I,
)

# Literal office values avoid querying every office across large metro bboxes.
# amenity=studio also finds generic recording studios; these require video or
# podcast context rather than being accepted as video businesses automatically.
OSM_TAGS = [
    "office=company", "office=film", "office=media",
    "craft=videographer", "craft=photographer", "shop=photography",
    "office=film_production", "office=video_production", "office=advertising_agency",
    "studio=video", "studio=film", "studio=television", "amenity=studio",
]


def is_relevant(rec: dict) -> bool:
    name = rec.get("name") or ""
    category = (rec.get("category") or "").lower().replace(" ", "_")
    tags = rec.get("osm_tags") or {}
    if category in EXCLUDED_CATEGORIES or EXCLUDED_NAME.search(name):
        return False
    studios = {v.strip() for v in tags.get("studio", "").split(";")}
    if category in CORE_CATEGORIES or studios & {"video", "film", "television"}:
        return True
    if studios & {"art", "creative", "dance"}:
        return False
    context = " ".join([name, tags.get("description", "")])
    if VIDEO_NAME.search(context):
        return True
    return (category in {"photographer", "advertising_agency"}
            and bool(re.search(r"\bproductions?\b", name, re.I)))


def lead_status(rec: dict) -> str:
    site = bool((rec.get("website") or "").strip())
    email = bool((rec.get("email") or "").strip())
    phone = bool((rec.get("phone") or "").strip())
    if site and email and phone:
        return "HOT"
    if site and (email or phone):
        return "WARM"
    if site:
        return "COLD"
    return "UNKNOWN"


def _enrich(rec: dict, ctx: dict) -> dict:
    """Visit the homepage once; retain listed contacts even if it fails."""
    site = rec.get("website") or ""
    if not site:
        return rec
    if ctx.get("demo_html"):
        html = ctx["demo_html"](rec)
    else:
        response = fetch(site)
        if response is None or response.status_code >= 400:
            rec["enrich_error"] = "Homepage unavailable; listed contacts retained"
            return rec
        html = response.text
    html = unescape(html or "")
    if not rec.get("email"):
        emails = find_emails(html)
        if emails:
            rec["email"] = emails[0]
    if not rec.get("phone"):
        match = re.search(r'href\s*=\s*[\"\']tel:([^\"\'<>]+)', html, re.I)
        if match:
            rec["phone"] = match.group(1).split("?", 1)[0].strip()
    for network, handle in detect_socials(html).items():
        if handle and not rec.get(network):
            rec[network] = f"https://{network}.com/{handle}"
    return rec


def _score(rec: dict) -> tuple[int, str, str]:
    status = lead_status(rec)
    rec["lead_status"] = status
    rec["vertical"] = "au_video_ops"
    score, tier = {"HOT": (80, "A"), "WARM": (60, "B"),
                   "COLD": (30, "C"), "UNKNOWN": (10, "C")}[status]
    notes = f"{status}: listed contact availability; hiring intent unknown"
    if rec.get("enrich_error"):
        notes += f"; {rec['enrich_error']}"
    return score, tier, notes


MASTER_COLUMNS = [
    ("Business", "name"), ("Contact Name", "contact_name"), ("Role", "role"),
    ("City", "city"), ("State", "state"), ("Website", "website"),
    ("Email", "email"), ("Phone", "phone"), ("LinkedIn", "linkedin"),
    ("Address", "address"), ("Category", "category"), ("Vertical", "vertical"),
    ("Source", "source"), ("Source URL", "source_url"), ("Lead Status", "lead_status"),
]

register(Vertical(
    key="au_video_ops",
    label="AU video/content businesses for editing and project support",
    description="Focused video-production prospects with simple contact status; no hiring claim.",
    overture_categories=sorted(CORE_CATEGORIES | SECONDARY_CATEGORIES),
    osm_tags=OSM_TAGS,
    keep_chains=True,
    filter_fn=is_relevant,
    enrich_fn=_enrich,
    score_fn=_score,
    columns=MASTER_COLUMNS + [("Tier", "tier"), ("Score", "score"), ("Notes", "why")],
))
