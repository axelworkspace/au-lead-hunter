import csv
from collections import Counter

INPUT_FILE = "sydney_video_ops_v03_researched.csv"
OUTPUT_FILE = "sydney_video_ops_v04_scored.csv"


def value(row, key):
    return (row.get(key) or "").strip()


def has(text, word):
    return word.lower() in (text or "").lower()


def score_icp(row):
    """
    Measures:
    Is this the type of video business we actually want?
    """
    score = 0
    reasons = []

    niche = value(row, "Niche")
    services = value(row, "Service Signals")
    category = value(row, "Category")
    business = value(row, "Business").lower()

    # Strong original business classification
    if category == "videographer":
        score += 25
        reasons.append("videographer category")

    elif category == "video_film_production":
        score += 30
        reasons.append("video/film production category")

    elif category == "audio_visual_production_and_design":
        score += 20
        reasons.append("AV production category")

    # Niche alignment with Mark's services
    niche_points = {
        "commercial_corporate": 25,
        "real_estate_property": 25,
        "social_content": 23,
        "editing_post": 20,
        "live_streaming": 18,
        "drone": 15,
        "wedding_event": 13,
        "general_video": 12,
    }

    if niche in niche_points:
        score += niche_points[niche]
        reasons.append(f"target niche: {niche}")

    # Service breadth
    service_list = [
        x.strip()
        for x in services.split(",")
        if x.strip()
    ]

    if len(service_list) >= 5:
        score += 20
        reasons.append("broad production service mix")
    elif len(service_list) >= 3:
        score += 15
        reasons.append("multiple production services")
    elif len(service_list) >= 1:
        score += 8
        reasons.append("clear production service")

    # Especially useful service signals
    if "commercial_corporate" in services:
        score += 10
        reasons.append("commercial/corporate clients")

    if "real_estate_property" in services:
        score += 10
        reasons.append("property/real-estate workflow")

    if "social_content" in services:
        score += 8
        reasons.append("social-content workflow")

    if "editing_post" in services:
        score += 5
        reasons.append("post-production workflow")

    # Name evidence
    if any(
        word in business
        for word in [
            "video",
            "film",
            "cinemat",
            "production",
        ]
    ):
        score += 5
        reasons.append("strong video business-name signal")

    return min(score, 100), reasons


def score_operations(row):
    """
    Measures:
    Is there observable workflow complexity where remote support
    might plausibly be useful?
    """
    score = 0
    reasons = []

    ops = value(row, "Operations Signals")
    services = value(row, "Service Signals")

    service_count = len([
        x for x in services.split(",")
        if x.strip()
    ])

    if service_count >= 5:
        score += 15
        reasons.append("complex service mix")
    elif service_count >= 3:
        score += 10
        reasons.append("multi-service workflow")
    elif service_count >= 2:
        score += 5
        reasons.append("more than one service")

    if has(ops, "projects_clients"):
        score += 20
        reasons.append("client/project workflow")

    if has(ops, "quote"):
        score += 15
        reasons.append("quote workflow")

    if has(ops, "booking"):
        score += 15
        reasons.append("booking/scheduling workflow")

    if has(ops, "enquiry"):
        score += 12
        reasons.append("customer enquiry workflow")

    if has(ops, "repeat_work"):
        score += 18
        reasons.append("recurring/repeat work")

    if has(ops, "team"):
        score += 10
        reasons.append("team/role complexity")

    return min(score, 100), reasons


def score_outreach(row):
    """
    Measures:
    Can we reasonably research/contact this prospect?

    Social profiles improve researchability, but they do NOT imply
    operational need.
    """
    score = 0
    reasons = []

    if value(row, "Email"):
        score += 30
        reasons.append("email available")

    if value(row, "Phone"):
        score += 10
        reasons.append("phone available")

    if value(row, "Website"):
        score += 10
        reasons.append("website available")

    decision = value(row, "Decision Maker Clue")

    if decision and decision.lower() not in {"none", "unknown"}:
        score += 30
        reasons.append("decision-maker identified")

    socials = value(row, "Social Profiles")

    if "LinkedIn:" in socials:
        score += 10
        reasons.append("LinkedIn available")

    if "Instagram:" in socials:
        score += 5
        reasons.append("Instagram available")

    if "Facebook:" in socials:
        score += 3
        reasons.append("Facebook available")

    if "YouTube:" in socials:
        score += 2
        reasons.append("YouTube available")

    return min(score, 100), reasons


def recommended_service(row):
    niche = value(row, "Niche")
    ops = value(row, "Operations Signals")

    recommendations = []

    if has(ops, "projects_clients"):
        recommendations.append("project/client coordination")

    if has(ops, "enquiry"):
        recommendations.append("client follow-ups")

    if has(ops, "quote"):
        recommendations.append("CRM + quote follow-up")

    if has(ops, "booking"):
        recommendations.append("booking/scheduling support")

    if has(ops, "repeat_work"):
        recommendations.append("recurring client administration")

    if has(ops, "team"):
        recommendations.append("operations coordination")

    if niche in {
        "commercial_corporate",
        "real_estate_property",
        "editing_post",
        "social_content",
    }:
        recommendations.append("video QA / delivery tracking")

    # dedupe while preserving order
    recommendations = list(dict.fromkeys(recommendations))

    if not recommendations:
        return "manual research required"

    return ", ".join(recommendations[:4])


def main():
    with open(
        INPUT_FILE,
        newline="",
        encoding="utf-8",
    ) as f:
        rows = list(csv.DictReader(f))

    results = []

    for row in rows:
        research_status = value(row, "Research Status")

        icp, icp_reasons = score_icp(row)
        ops, ops_reasons = score_operations(row)
        outreach, outreach_reasons = score_outreach(row)

        # Do NOT pretend missing research = bad business.
        if research_status != "RESEARCHED":
            overall = ""
            status = "NEEDS_REVIEW"

        else:
            # Operations need is deliberately the largest component.
            overall = round(
                (icp * 0.40)
                + (ops * 0.45)
                + (outreach * 0.15)
            )

            # A high overall score alone is not enough.
            # Require actual operations evidence for Priority.
            if overall >= 70 and ops >= 50 and icp >= 55:
                status = "PRIORITY"

            elif overall >= 55 and ops >= 30 and icp >= 45:
                status = "QUALIFIED"

            elif overall >= 40:
                status = "RESEARCH"

            else:
                status = "LOW_FIT"

        row["ICP Fit Score"] = icp
        row["ICP Evidence"] = "; ".join(icp_reasons)

        row["Operations Need Score"] = ops
        row["Operations Evidence"] = "; ".join(ops_reasons)

        row["Outreach Readiness Score"] = outreach
        row["Outreach Evidence"] = "; ".join(outreach_reasons)

        row["V04 Overall Score"] = overall
        row["V04 Status"] = status

        row["Recommended Service"] = recommended_service(row)

        if status == "NEEDS_REVIEW":
            row["Next Action"] = (
                "Manually inspect website/social profiles; "
                "automated website research was unavailable."
            )

        elif not value(row, "Decision Maker Clue"):
            row["Next Action"] = (
                "Identify founder/owner/director on LinkedIn or company site."
            )

        elif status in {"PRIORITY", "QUALIFIED"}:
            row["Next Action"] = (
                "Review recent work and prepare personalized outreach."
            )

        else:
            row["Next Action"] = (
                "Keep in research queue; do not prioritize outreach yet."
            )

        results.append(row)

    results.sort(
        key=lambda r: (
            r["V04 Status"] == "NEEDS_REVIEW",
            -(int(r["V04 Overall Score"] or 0)),
        )
    )

    fieldnames = list(results[0].keys())

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(results)

    counts = Counter(
        row["V04 Status"]
        for row in results
    )

    print("=" * 72)
    print("AU LEAD HUNTER v0.4 — QUALIFICATION")
    print("=" * 72)

    print(f"\nTotal: {len(results)}")

    print("\nSTATUS")
    for status in [
        "PRIORITY",
        "QUALIFIED",
        "RESEARCH",
        "LOW_FIT",
        "NEEDS_REVIEW",
    ]:
        print(
            f"  {status}: "
            f"{counts.get(status, 0)}"
        )

    print("\nTOP RESEARCHED PROSPECTS")

    ranked = [
        r for r in results
        if r["V04 Status"] != "NEEDS_REVIEW"
    ]

    for r in ranked[:15]:
        print(
            f"\n[{r['V04 Overall Score']}] "
            f"{r['V04 Status']} — "
            f"{r.get('Business')}"
        )
        print(
            f"  ICP: {r['ICP Fit Score']} | "
            f"Ops: {r['Operations Need Score']} | "
            f"Outreach: {r['Outreach Readiness Score']}"
        )
        print(
            f"  Recommended: "
            f"{r['Recommended Service']}"
        )
        print(
            f"  Next: {r['Next Action']}"
        )

    print(f"\nSaved -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
