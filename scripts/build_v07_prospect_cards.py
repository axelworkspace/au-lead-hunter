import csv
from pathlib import Path
from collections import defaultdict

QUAL_FILE = Path("sydney_video_ops_v04_scored.csv")
DECISION_FILE = Path("sydney_video_ops_v05_decision_queue.csv")
OUTREACH_FILE = Path("sydney_video_ops_v06_outreach_queue.csv")
CLAIMS_FILE = Path("sydney_video_ops_v066_validated_claims.csv")

OUTPUT = Path("sydney_video_ops_v07_prospect_cards.csv")


def load_csv(path):
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


qualification = load_csv(QUAL_FILE)
decisions = load_csv(DECISION_FILE)
outreach = load_csv(OUTREACH_FILE)
claims = load_csv(CLAIMS_FILE)


def first_value(row, *names):
    for name in names:
        value = row.get(name)

        if value is not None and str(value).strip():
            return str(value).strip()

    return ""


def company_name(row):
    return first_value(
        row,
        "Company",
        "Business",
        "Name",
    )


qualification_by_company = {
    company_name(row): row
    for row in qualification
    if company_name(row)
}

decision_by_company = {
    company_name(row): row
    for row in decisions
    if company_name(row)
}

outreach_by_company = {
    company_name(row): row
    for row in outreach
    if company_name(row)
}


approved_claims = defaultdict(list)

for row in claims:

    if (
        row.get(
            "Human Decision",
            ""
        ).strip().upper()
        != "APPROVE"
    ):
        continue

    if (
        row.get(
            "Approved For Outreach",
            ""
        ).strip().upper()
        != "YES"
    ):
        continue

    if (
        row.get(
            "Claim Validation Status",
            ""
        ).strip().upper()
        != "VALID"
    ):
        continue

    company = company_name(row)

    claim = row.get(
        "Approved Claim",
        ""
    ).strip()

    if company and claim:
        approved_claims[company].append(claim)

# v0.7 prospect cards should only be generated for companies that
# reached the final v0.6 outreach queue.
companies = sorted(
    company
    for company in outreach_by_company
    if company
)

def determine_service_match(claim_text):
    text = claim_text.lower()

    matches = []

    if any(term in text for term in [
        "client feedback",
        "post-production manager",
        "final delivery",
        "production workflow",
    ]):
        matches.append(
            "Project coordination / client follow-up"
        )

    if any(term in text for term in [
        "editing",
        "post-production",
        "final cut",
        "video production",
    ]):
        matches.append(
            "Video QA / delivery tracking"
        )

    if any(term in text for term in [
        "social media",
        "youtube",
        "linkedin",
        "facebook",
        "instagram",
        "meta",
    ]):
        matches.append(
            "Content operations support"
        )

    if any(term in text for term in [
        "multi-location",
        "team",
        "crew",
        "end-to-end",
    ]):
        matches.append(
            "Operations / production coordination"
        )

    # Remove duplicates while preserving order.
    unique = []

    for item in matches:
        if item not in unique:
            unique.append(item)

    if not unique:
        return "General operations support"

    return " | ".join(unique)


def determine_outreach_angle(
    company,
    decision_maker,
    role,
    claims_text,
):

    text = claims_text.lower()

    if (
        "client feedback" in text
        or
        "post-production manager" in text
    ):
        return (
            "Support the existing production workflow by helping "
            "manage client communication, revision tracking, QA, "
            "and delivery coordination."
        )

    if (
        "end-to-end" in text
        or
        "final delivery" in text
        or
        "final cut" in text
    ):
        return (
            "Offer operations and project coordination support "
            "across the production lifecycle, from active projects "
            "through revisions, QA, and final delivery."
        )

    if (
        "multi-location" in text
        or
        "trusted long-term crew" in text
    ):
        return (
            "Position support around coordinating multiple projects, "
            "crew communication, client follow-ups, and production "
            "admin as workload grows."
        )

    if "editing" in text:
        return (
            "Offer video operations support around editing queues, "
            "revision tracking, QA, client follow-ups, and delivery."
        )

    return (
        "Offer flexible operations and client support designed to "
        "reduce admin workload and keep projects moving."
    )


cards = []

for company in companies:

    qual = qualification_by_company.get(
        company,
        {},
    )

    decision = decision_by_company.get(
        company,
        {},
    )

    outreach_row = outreach_by_company.get(
        company,
        {},
    )

    company_claims = approved_claims.get(
        company,
        [],
    )

    claims_text = " ".join(company_claims)

    decision_maker = first_value(
        decision,
        "Decision Maker",
        "Decision Maker Name",
        "Name",
    )

    role = first_value(
        decision,
        "Role",
        "Decision Maker Role",
        "Title",
    )

    confidence = first_value(
        decision,
        "Confidence",
        "Identity Confidence",
        "Decision Maker Confidence",
    )

    recommended_channel = first_value(
        outreach_row,
        "Recommended Outreach Channel",
        "Preferred Outreach Channel",
    )

    website = first_value(
        qual,
        "Website",
        "website",
        "URL",
    )

    score = first_value(
        qual,
        "V04 Overall Score",
        "Score",
        "Prospect Score",
    )

    status = first_value(
        qual,
        "V04 Status",
        "Prospect Tier",
        "Tier",
    )

    readiness = first_value(
        outreach_row,
        "Outreach Readiness",
        "Status",
        "Readiness",
    )

    service_match = determine_service_match(
        claims_text
    )

    outreach_angle = determine_outreach_angle(
        company,
        decision_maker,
        role,
        claims_text,
    )

    cards.append({
        "Company": company,
        "Lead Score": score,
        "Qualification Status": status,
        "Website": website,
        "Decision Maker": decision_maker,
        "Decision Maker Role": role,
        "Decision Maker Confidence": confidence,
        "Recommended Channel": recommended_channel,
        "Outreach Readiness": readiness,
        "Approved Evidence Count": len(
            company_claims
        ),
        "Approved Evidence": " || ".join(
            company_claims
        ),
        "Recommended Service Match":
            service_match,
        "Recommended Outreach Angle":
            outreach_angle,
    })


fieldnames = [
    "Company",
    "Lead Score",
    "Qualification Status",
    "Website",
    "Decision Maker",
    "Decision Maker Role",
    "Decision Maker Confidence",
    "Recommended Channel",
    "Outreach Readiness",
    "Approved Evidence Count",
    "Approved Evidence",
    "Recommended Service Match",
    "Recommended Outreach Angle",
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
    writer.writerows(cards)


print("=" * 72)
print(
    "AU LEAD HUNTER v0.7 "
    "— PROSPECT INTELLIGENCE CARDS"
)
print("=" * 72)

print(
    f"\nProspect cards generated: "
    f"{len(cards)}"
)

for card in cards:

    print(
        "\n"
        + "=" * 72
    )

    print(
        card["Company"]
    )

    print(
        "=" * 72
    )

    print(
        f"Lead Score: "
        f"{card['Lead Score']}"
    )

    print(
        f"Qualification: "
        f"{card['Qualification Status']}"
    )

    print(
        f"Decision Maker: "
        f"{card['Decision Maker']}"
    )

    print(
        f"Role: "
        f"{card['Decision Maker Role']}"
    )

    print(
        f"Confidence: "
        f"{card['Decision Maker Confidence']}"
    )

    print(
        f"Outreach Readiness: "
        f"{card['Outreach Readiness']}"
    )

    print(
        f"Approved Evidence: "
        f"{card['Approved Evidence Count']}"
    )

    print(
        "\nSERVICE MATCH"
    )

    print(
        card[
            "Recommended Service Match"
        ]
    )

    print(
        "\nOUTREACH ANGLE"
    )

    print(
        card[
            "Recommended Outreach Angle"
        ]
    )

    if card["Approved Evidence"]:

        print(
            "\nAPPROVED EVIDENCE"
        )

        for claim in card[
            "Approved Evidence"
        ].split(" || "):

            print(
                f"  • {claim}"
            )


print(
    f"\nSaved -> {OUTPUT}"
)
