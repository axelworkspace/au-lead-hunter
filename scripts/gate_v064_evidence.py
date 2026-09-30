import csv
import re
from collections import defaultdict
from datetime import datetime

INPUT = "sydney_video_ops_v063_ranked_evidence.csv"
OUTPUT = "sydney_video_ops_v064_gated_evidence.csv"

MAX_PASS_PER_COMPANY = 4


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def has_any(text, terms):
    text = text.lower()
    return any(term in text for term in terms)


def count_terms(text, terms):
    text = text.lower()
    return sum(term in text for term in terms)


def gate(row):

    claim = clean(row.get("Claim", ""))
    lower = claim.lower()

    evidence_type = row.get("Evidence Type", "")
    score = int(row.get("Evidence Score") or 0)

    failures = []
    reviews = []
    strengths = []

    # ==================================================
    # 1. BASIC QUALITY
    # ==================================================

    if len(claim) < 70:
        failures.append("INSUFFICIENT_CONTEXT")

    if len(claim) > 700:
        reviews.append("OVERSIZED_CONTEXT")

    if score < 35:
        failures.append("LOW_RANKING_SCORE")

    # ==================================================
    # 2. NAVIGATION / UI POLLUTION
    # ==================================================

    nav_terms = [
        "search search",
        "toggle navigation",
        "skip to content",
        "privacy policy",
        "cookie policy",
        "terms and conditions",
    ]

    nav_hits = count_terms(lower, nav_terms)

    if nav_hits:
        failures.append("NAVIGATION_POLLUTION")

    menu_terms = [
        "home",
        "about",
        "services",
        "contact",
        "portfolio",
        "case studies",
        "industries",
    ]

    menu_hits = count_terms(lower, menu_terms)

    if menu_hits >= 5:
        reviews.append("MENU_HEAVY_CONTEXT")

    # ==================================================
    # 3. TESTIMONIAL / REVIEW CONTAMINATION
    # ==================================================

    testimonial_terms = [
        "highly recommended",
        "exceeded our expectations",
        "outstanding experience",
        "amazing to work with",
        "couldn't recommend",
        "couldn’t recommend",
        "thank you enough",
        "we contracted",
        "we hired",
        "we engaged",
        "review us",
        "based on reviews",
    ]

    testimonial_hits = count_terms(
        lower,
        testimonial_terms,
    )

    if testimonial_hits:
        failures.append("CUSTOMER_TESTIMONIAL")

    # Do NOT reject a company merely because it
    # offers "testimonial videos" as a service.

    if (
        "testimonial video" in lower
        and testimonial_hits == 0
    ):
        strengths.append(
            "TESTIMONIAL_VIDEO_SERVICE"
        )

    # ==================================================
    # 4. STALE-DATE DETECTION
    # ==================================================

    years = [
        int(y)
        for y in re.findall(
            r"\b(20\d{2})\b",
            claim,
        )
    ]

    if years:

        newest_year = max(years)

        current_year = datetime.now().year

        if newest_year <= current_year - 5:
            reviews.append(
                f"POSSIBLY_STALE_{newest_year}"
            )

    # ==================================================
    # 5. TYPE VALIDATION — TEAM / WORKFLOW
    # ==================================================

    workflow_terms = [
        "our team",
        "our crew",
        "production manager",
        "post-production manager",
        "post production manager",
        "project manager",
        "client feedback",
        "pre-production",
        "pre production",
        "post-production",
        "post production",
        "every stage",
        "final delivery",
        "production process",
        "workflow",
        "from concept",
        "end-to-end",
        "end to end",
    ]

    role_terms = [
        "founder",
        "director",
        "producer",
        "videographer",
        "cinematographer",
        "editor",
        "manager",
        "drone pilot",
    ]

    workflow_hits = count_terms(
        lower,
        workflow_terms,
    )

    role_hits = count_terms(
        lower,
        role_terms,
    )

    if evidence_type == "TEAM_WORKFLOW":

        if workflow_hits == 0 and role_hits == 0:
            failures.append(
                "TYPE_MISMATCH_TEAM_WORKFLOW"
            )

        elif workflow_hits:
            strengths.append(
                "WORKFLOW_SUPPORTED"
            )

        elif role_hits:
            reviews.append(
                "ROLE_ONLY_NOT_WORKFLOW"
            )

    # ==================================================
    # 6. TYPE VALIDATION — PROJECT
    # ==================================================

    project_terms = [
        "case study",
        "project",
        "campaign",
        "our work",
        "our clients",
        "worked with",
        "produced for",
        "created for",
        "filmed for",
        "delivered for",
    ]

    project_hits = count_terms(
        lower,
        project_terms,
    )

    if evidence_type == "PROJECT":

        strong_project_terms = [
            "case study",
            "worked with",
            "working with",
            "produced for",
            "created for",
            "filmed for",
            "delivered for",
            "project for",
            "campaign for",
            "client:",
            "client -",
        ]

        weak_project_terms = [
            "our work",
            "our clients",
            "project",
            "campaign",
        ]

        strong_project_hits = count_terms(
            lower,
            strong_project_terms,
        )

        weak_project_hits = count_terms(
            lower,
            weak_project_terms,
        )

        # Service/menu language can mention projects
        # without proving an actual completed project.
        service_pitch_terms = [
            "do you need",
            "we offer",
            "our services",
            "services include",
            "promotional videos",
            "training videos",
            "testimonial videos",
            "video production services",
        ]

        service_pitch_hits = count_terms(
            lower,
            service_pitch_terms,
        )

        if strong_project_hits:
            strengths.append(
                "PROJECT_SIGNAL_SUPPORTED"
            )

        elif weak_project_hits and not service_pitch_hits:
            reviews.append(
                "WEAK_PROJECT_EVIDENCE"
            )

        else:
            failures.append(
                "TYPE_MISMATCH_PROJECT"
            )
    # ==================================================
    # 7. TYPE VALIDATION — SERVICE
    # ==================================================

    service_terms = [
        "video production",
        "videography",
        "video editing",
        "editing",
        "photography",
        "animation",
        "motion graphics",
        "social media",
        "drone",
        "commercial",
        "wedding",
        "event video",
        "corporate video",
        "training video",
    ]

    service_hits = count_terms(
        lower,
        service_terms,
    )
    if evidence_type == "SERVICE":

        if service_hits == 0:
            failures.append(
                "TYPE_MISMATCH_SERVICE"
            )
        else:
            strengths.append(
                "SERVICE_SUPPORTED"
            )
    # ==================================================
    # 8. OPERATIONAL USEFULNESS
    # ==================================================

    ops_terms = [
        "client",
        "customer",
        "feedback",
        "project",
        "booking",
        "schedule",
        "quote",
        "production",
        "editing",
        "delivery",
        "team",
        "manager",
        "workflow",
        "pre-production",
        "post-production",
    ]

    ops_hits = count_terms(
        lower,
        ops_terms,
    )

    if ops_hits >= 3:
        strengths.append(
            "STRONG_OPS_RELEVANCE"
        )

    elif ops_hits == 0:
        reviews.append(
            "LOW_OPS_RELEVANCE"
        )
    # ==================================================
    # BIOGRAPHY / TEAM PROFILE POLLUTION
    # ==================================================

    biography_terms = [
        "in his spare time",
        "in her spare time",
        "when he's not",
        "when he’s not",
        "when she's not",
        "when she’s not",
        "you can find him",
        "you can find her",
        "his passion",
        "her passion",
        "rewatching",
        "most attractive",
    ]

    biography_hits = count_terms(
        lower,
        biography_terms,
    )

    if biography_hits:

        if evidence_type == "SERVICE":
            reviews.append(
                "BIOGRAPHY_POLLUTION"
            )

        elif evidence_type == "TEAM_WORKFLOW":
            reviews.append(
                "TEAM_BIOGRAPHY_CONTEXT"
            )
    # ==================================================
    # FINAL GATE
    # ==================================================

    if failures:
        status = "FAIL"

    elif reviews:
        status = "REVIEW"

    else:
        status = "PASS"

    return (
        status,
        failures,
        reviews,
        strengths,
    )


# ==================================================
# LOAD SELECTED v0.6.3 EVIDENCE
# ==================================================

with open(
    INPUT,
    newline="",
    encoding="utf-8",
) as f:

    rows = list(csv.DictReader(f))


selected = [
    r for r in rows
    if r.get("Selected For Brief") == "YES"
]


results = []

for row in selected:

    result = dict(row)

    (
        status,
        failures,
        reviews,
        strengths,
    ) = gate(row)

    result["Gate Status"] = status

    result["Gate Failures"] = (
        ", ".join(failures)
    )

    result["Gate Review Flags"] = (
        ", ".join(reviews)
    )

    result["Gate Strengths"] = (
        ", ".join(strengths)
    )

    result["Human Approval"] = "PENDING"

    result["Approved For Outreach"] = "NO"

    results.append(result)

# ==================================================
# SAVE
# ==================================================

fields = list(results[0].keys())

with open(
    OUTPUT,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(results)


# ==================================================
# REPORT
# ==================================================

print("=" * 72)
print("AU LEAD HUNTER v0.6.4 — EVIDENCE GATE")
print("=" * 72)

total_counts = defaultdict(int)

for row in results:
    total_counts[row["Gate Status"]] += 1

companies = defaultdict(list)

for row in results:
    companies[row["Company"]].append(row)

print("\nOVERALL")

for status in [
    "PASS",
    "REVIEW",
    "FAIL",
]:
    print(
        f"  {status:<8} "
        f"{total_counts[status]}"
    )


for company, records in companies.items():

    print("\n" + "=" * 72)
    print(company)
    print("=" * 72)

    records.sort(
        key=lambda r: int(
            r["Evidence Score"]
        ),
        reverse=True,
    )

    for row in records:

        claim = clean(row["Claim"])

        if len(claim) > 180:
            claim = claim[:180] + "..."

        print(
            f"\n[{row['Gate Status']}] "
            f"[{row['Evidence Score']}] "
            f"{row['Evidence Type']}"
        )

        print(
            f"  {claim}"
        )

        if row["Gate Failures"]:
            print(
                f"  Fail: "
                f"{row['Gate Failures']}"
            )

        if row["Gate Review Flags"]:
            print(
                f"  Review: "
                f"{row['Gate Review Flags']}"
            )

        if row["Gate Strengths"]:
            print(
                f"  Strength: "
                f"{row['Gate Strengths']}"
            )


print(
    f"\nSaved -> {OUTPUT}"
)

print(
    "\nPASS still means machine-approved candidate. "
    "Human approval is required before outreach."
)
