"""
Australian video-production operations lead vertical.

Version 0.2

Goal:
Find Australian businesses that are genuinely relevant to:
- videography
- video production
- film production
- audio/video production
- real-estate media
- selected media agencies

Potential services:
- client follow-ups
- CRM/admin
- customer support
- project coordination
- QA
- operations support
"""

from __future__ import annotations

from .. import register, Vertical
from ._common import audit_enrich


# Strong Overture categories.
CORE_CATEGORIES = {
    "videographer",
    "video_film_production",
    "audio_visual_production_and_design",
}

# Potentially relevant, but need stronger business-name evidence.
SECONDARY_CATEGORIES = {
    "broadcasting_media_production",
    "media_agency",
    "real_estate_photography",
    "event_photography",
}

# Categories that produced obvious false positives in the Sydney test.
EXCLUDED_CATEGORIES = {
    "video_game_store",
    "video_game_critic",
    "video_and_video_game_rentals",
    "music_production",
    "music_production_services",
    "theatrical_productions",
    "books_mags_music_and_video",
    "media_news_company",
    "media_news_website",
    "mass_media",
    "print_media",
    "photography_store_and_services",
    "session_photography",
    "photography_classes",
    "media_restoration_service",
    "mediator",
    "media_critic",
    "social_media_agency",
    "social_media_company",
}

# Strong words that indicate the business itself is likely video-related.
STRONG_VIDEO_NAME_TERMS = (
    "video",
    "videographer",
    "videography",
    "film",
    "filmmaker",
    "filmmaking",
    "cinematography",
    "cinematographer",
    "video production",
    "film production",
)


def _normalise(value: object) -> str:
    return str(value or "").strip().lower()


def _score(rec: dict) -> tuple[int, str, str]:
    score = 0
    reasons = []

    name = _normalise(rec.get("name"))
    category = _normalise(rec.get("category"))

    # ---------------------------------------------------------
    # 1. Hard exclusion
    # ---------------------------------------------------------
    if category in EXCLUDED_CATEGORIES:
        return (
            0,
            "C",
            f"excluded category: {category}",
        )

    # ---------------------------------------------------------
    # 2. Core category
    # ---------------------------------------------------------
    if category in CORE_CATEGORIES:
        score += 55
        reasons.append(f"core category: {category}")

    # ---------------------------------------------------------
    # 3. Secondary category
    # ---------------------------------------------------------
    elif category in SECONDARY_CATEGORIES:
        score += 25
        reasons.append(f"secondary category: {category}")

    else:
        reasons.append("no strong video category")

    # ---------------------------------------------------------
    # 4. Strong business-name evidence
    # ---------------------------------------------------------
    matched_name_terms = [
        term
        for term in STRONG_VIDEO_NAME_TERMS
        if term in name
    ]

    if matched_name_terms:
        score += 25
        reasons.append(
            "video-related business name: "
            + ", ".join(matched_name_terms[:3])
        )

    # ---------------------------------------------------------
    # 5. Contactability
    # ---------------------------------------------------------
    if rec.get("website"):
        score += 5
        reasons.append("website listed")

    if rec.get("phone"):
        score += 3
        reasons.append("phone listed")

    if rec.get("email"):
        score += 2
        reasons.append("email listed")

    # ---------------------------------------------------------
    # 6. Website reachability
    # ---------------------------------------------------------
    audit = rec.get("audit") or {}

    if audit.get("reachable"):
        score += 5
        reasons.append("website reachable")

    score = min(score, 100)

    # ---------------------------------------------------------
    # 7. Tier
    # ---------------------------------------------------------
    if score >= 70:
        tier = "A"
    elif score >= 50:
        tier = "B"
    elif score >= 25:
        tier = "C"
    else:
        tier = "C"

    return score, tier, "; ".join(reasons)


def _opener(rec: dict) -> str:
    name = rec.get("name") or "your business"
    category = _normalise(rec.get("category"))

    if category == "real_estate_photography":
        return (
            f"{name} may be a fit for remote client follow-ups, "
            "project coordination, QA and admin support."
        )

    if category == "event_photography":
        return (
            f"{name} may be a fit for client communication, "
            "project tracking, QA and customer support."
        )

    if category == "media_agency":
        return (
            f"{name} may be a fit for client coordination, "
            "CRM/admin, project follow-up and operations support."
        )

    return (
        f"{name} may be a fit for remote client follow-ups, "
        "CRM/admin, project coordination, QA and operations support."
    )


COLUMNS = [
    ("Tier", "tier"),
    ("Score", "score"),
    ("Business", "name"),
    ("Category", "category"),
    ("City", "city"),
    ("State", "state"),
    ("Phone", "phone"),
    ("Email", "email"),
    ("Website", "website"),
    ("Why a Lead", "why"),
    ("Pitch Angle", "opener"),
    ("Address", "address"),
    ("Source", "source"),
    ("Source URL", "source_url"),
]


register(
    Vertical(
        key="au_video_ops",
        label="Australian video-production operations leads",
        description=(
            "Finds Australian video and production businesses that may fit "
            "remote client-support and operations services."
        ),

        # Keep first-pass discovery narrow.
        # We'll add broader sources later after quality is proven.
        overture_categories=[
            "videographer",
            "video_film_production",
            "audio_visual_production_and_design",
            "broadcasting_media_production",
            "media_agency",
            "real_estate_photography",
            "event_photography",
        ],

        # We intentionally test Overture first.
        # OSM can be added later with tighter tags.
        osm_tags=[],

        keep_chains=False,

        score_fn=_score,
        enrich_fn=audit_enrich,
        opener_fn=_opener,

        config={
            "target_country": "Australia",
            "service_focus": [
                "client follow-ups",
                "CRM updates",
                "customer support",
                "project coordination",
                "QA",
                "operations support",
            ],
        },

        columns=COLUMNS,
    )
)
