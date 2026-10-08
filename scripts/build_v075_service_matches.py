import csv
from pathlib import Path

INPUT = Path("sydney_video_ops_v07_prospect_cards.csv")
OUTPUT = Path("sydney_video_ops_v075_service_matches.csv")


def load_csv(path):
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


rows = load_csv(INPUT)


def first_value(row, *names):
    for name in names:
        value = row.get(name, "")
        if str(value).strip():
            return str(value).strip()
    return ""


def build_match(row):
    company = first_value(row, "Company")
    readiness = first_value(row, "Outreach Readiness")
    evidence_count = int(
        first_value(row, "Approved Evidence Count") or 0
    )

    service_text = first_value(
        row,
        "Recommended Service Match",
    ).lower()

    evidence_text = first_value(
        row,
        "Approved Evidence",
    ).lower()

    combined = f"{service_text} {evidence_text}"

    primary = ""
    secondary = ""
    score = 0
    reason = ""
    proof_type = ""
    status = ""
    next_action = ""

    # Hard safety gates first.
    if company == "Ikon Images Video Production":
        primary = "General operations support"
        secondary = ""
        score = 25
        reason = (
            "Prospect has no approved outreach evidence and no "
            "verified decision maker yet."
        )
        proof_type = "Operations / project coordination experience"
        status = "IDENTITY_RESEARCH"
        next_action = (
            "Identify a real decision maker and gather approved "
            "company-specific evidence before personalized outreach."
        )

    elif company == "Mak Video":
        primary = "General operations support"
        secondary = "Video QA / delivery tracking"
        score = 35
        reason = (
            "A founder is identified, but current approved evidence "
            "is unavailable and existing service evidence was held "
            "for freshness verification."
        )
        proof_type = "Video production operations experience"
        status = "EVIDENCE_VERIFY"
        next_action = (
            "Verify current business activity and services before "
            "using personalized claims."
        )

    elif "client feedback" in combined or "revision" in combined:
        primary = "Client communication / revision coordination"
        secondary = "Video QA / delivery tracking"
        score = 95
        reason = (
            "Approved evidence shows an active production workflow "
            "involving client feedback, post-production, or revisions."
        )
        proof_type = (
            "Video production customer success / project coordination"
        )
        status = "STRONG_MATCH"
        next_action = (
            "Use verified workflow evidence in a personalized outreach "
            "message focused on reducing feedback and delivery admin."
        )

    elif (
        "multi-location" in combined
        or "crew" in combined
        or "production coordination" in service_text
    ):
        primary = "Production / project coordination"
        secondary = "Client follow-up / production admin"
        score = 90
        reason = (
            "Approved evidence indicates a team-based production "
            "environment where coordination and client support are relevant."
        )
        proof_type = (
            "Project coordination / client success / video QA experience"
        )
        status = "STRONG_MATCH"
        next_action = (
            "Pitch flexible production coordination and client support "
            "using only the approved evidence."
        )

    elif (
        "editing" in combined
        or "video qa" in service_text
        or "content operations" in service_text
    ):
        primary = "Video QA / editing operations"
        secondary = "Content operations support"
        score = 85
        reason = (
            "Approved evidence shows active editing, production, "
            "repurposing, or content-distribution workflows."
        )
        proof_type = "Video QA / editing / delivery operations experience"
        status = "STRONG_MATCH"
        next_action = (
            "Lead with editing workflow support, QA, revision tracking, "
            "and delivery coordination."
        )

    else:
        primary = "General operations support"
        secondary = ""
        score = 60 if evidence_count > 0 else 30
        reason = (
            "The prospect has some approved evidence, but no stronger "
            "service-specific operations signal was detected."
            if evidence_count > 0
            else
            "There is not enough approved evidence for strong personalization."
        )
        proof_type = "Operations / project coordination experience"
        status = (
            "MODERATE_MATCH"
            if evidence_count > 0
            else "RESEARCH_REQUIRED"
        )
        next_action = (
            "Review approved evidence manually before drafting outreach."
            if evidence_count > 0
            else
            "Gather stronger approved evidence before outreach."
        )

    # Keep upstream verification requirements.
    if readiness == "MANUAL_VERIFY":
        status = "MANUAL_VERIFY"

    safe_angle = first_value(
        row,
        "Recommended Outreach Angle",
    )

    return {
        "Company": company,
        "Qualification": first_value(
            row,
            "Qualification Status",
        ),
        "Decision Maker": first_value(
            row,
            "Decision Maker",
        ),
        "Decision Maker Role": first_value(
            row,
            "Decision Maker Role",
        ),
        "Outreach Readiness": readiness,
        "Approved Evidence Count": evidence_count,
        "Primary Service Match": primary,
        "Secondary Service Match": secondary,
        "Match Score": score,
        "Match Reason": reason,
        "Safe Outreach Angle": safe_angle,
        "Portfolio Proof Type": proof_type,
        "Portfolio Proof URL": "",
        "Service Match Status": status,
        "V075 Next Action": next_action,
    }


matches = [build_match(row) for row in rows]

fieldnames = [
    "Company",
    "Qualification",
    "Decision Maker",
    "Decision Maker Role",
    "Outreach Readiness",
    "Approved Evidence Count",
    "Primary Service Match",
    "Secondary Service Match",
    "Match Score",
    "Match Reason",
    "Safe Outreach Angle",
    "Portfolio Proof Type",
    "Portfolio Proof URL",
    "Service Match Status",
    "V075 Next Action",
]

with OUTPUT.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
    )
    writer.writeheader()
    writer.writerows(matches)


print("=" * 72)
print(
    "AU LEAD HUNTER v0.7.5 "
    "— PORTFOLIO / SERVICE MATCHING"
)
print("=" * 72)

print(f"\nProspects matched: {len(matches)}")

for row in matches:
    print("\n" + "=" * 72)
    print(row["Company"])
    print("=" * 72)

    print(
        f"Qualification: "
        f"{row['Qualification']}"
    )

    print(
        f"Decision Maker: "
        f"{row['Decision Maker']}"
    )

    print(
        f"Readiness: "
        f"{row['Outreach Readiness']}"
    )

    print(
        f"Match Score: "
        f"{row['Match Score']}"
    )

    print(
        f"Service Match Status: "
        f"{row['Service Match Status']}"
    )

    print(
        f"Primary Service: "
        f"{row['Primary Service Match']}"
    )

    if row["Secondary Service Match"]:
        print(
            f"Secondary Service: "
            f"{row['Secondary Service Match']}"
        )

    print("\nMATCH REASON")
    print(row["Match Reason"])

    print("\nPORTFOLIO PROOF TYPE")
    print(row["Portfolio Proof Type"])

    print("\nNEXT ACTION")
    print(row["V075 Next Action"])


print(f"\nSaved -> {OUTPUT}")
