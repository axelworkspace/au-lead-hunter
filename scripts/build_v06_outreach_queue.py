import csv
from datetime import datetime

INPUT_FILE = "sydney_video_ops_v05_decision_queue.csv"
OUTPUT_FILE = "sydney_video_ops_v06_outreach_queue.csv"


def val(row, key):
    return (row.get(key) or "").strip()


def split_items(text):
    return [
        x.strip()
        for x in (text or "").split(",")
        if x.strip()
    ]


def build_support_opportunity(row):
    """
    Convert observed signals into services we can credibly offer.

    Important:
    These are opportunities, NOT claims that the prospect has
    operational problems.
    """

    ops = val(row, "Operations Signals")
    niche = val(row, "Niche")

    opportunities = []

    if "projects_clients" in ops:
        opportunities.append("project/client coordination")

    if "enquiry" in ops:
        opportunities.append("client enquiry follow-up")

    if "quote" in ops:
        opportunities.append("CRM and quote follow-up")

    if "booking" in ops:
        opportunities.append("booking/scheduling support")

    if "repeat_work" in ops:
        opportunities.append("recurring client administration")

    if "team" in ops:
        opportunities.append("production operations coordination")

    if niche in {
        "commercial_corporate",
        "real_estate_property",
        "editing_post",
        "social_content",
    }:
        opportunities.append("video QA and delivery tracking")

    opportunities = list(dict.fromkeys(opportunities))

    return ", ".join(opportunities[:5])


def build_observed_signals(row):
    signals = []

    services = split_items(
        val(row, "Service Signals")
    )

    ops = val(row, "Operations Signals")

    socials = val(row, "Social Profiles")

    if services:
        signals.append(
            f"{len(services)} detected service group(s)"
        )

    if "projects_clients" in ops:
        signals.append("client/project workflow")

    if "quote" in ops:
        signals.append("quote workflow")

    if "booking" in ops:
        signals.append("booking/scheduling workflow")

    if "enquiry" in ops:
        signals.append("customer enquiry workflow")

    if "repeat_work" in ops:
        signals.append("recurring-work signal")

    if "team" in ops:
        signals.append("team/role signals")

    social_names = []

    for platform in [
        "LinkedIn",
        "Instagram",
        "Facebook",
        "YouTube",
        "TikTok",
    ]:
        if f"{platform}:" in socials:
            social_names.append(platform)

    if social_names:
        signals.append(
            "public social presence: "
            + ", ".join(social_names)
        )

    return "; ".join(signals)


def determine_readiness(row):
    identity_status = val(
        row,
        "Identity Status",
    )

    confidence = val(
        row,
        "Decision Maker Confidence",
    )

    status = val(
        row,
        "V04 Status",
    )

    if identity_status != "IDENTIFIED":
        return "IDENTITY_RESEARCH"

    if confidence == "LOW":
        return "VERIFY_IDENTITY"

    if confidence == "MEDIUM":
        return "MANUAL_VERIFY"

    if (
        confidence == "HIGH"
        and status in {"PRIORITY", "QUALIFIED"}
    ):
        return "READY_FOR_REVIEW"

    return "RESEARCH"


def determine_channel(row):
    linkedin = val(
        row,
        "Decision Maker LinkedIn",
    )

    email = val(
        row,
        "Email",
    )

    socials = val(
        row,
        "Social Profiles",
    )

    if linkedin:
        return "LinkedIn"

    if email:
        return "Email"

    if "Instagram:" in socials:
        return "Instagram"

    if val(row, "Phone"):
        return "Phone / manual research"

    return "Website contact form"


def build_next_action(row, readiness):
    person = val(row, "Decision Maker")

    if readiness == "READY_FOR_REVIEW":
        return (
            f"Verify {person}'s current role and review "
            "recent company activity before drafting outreach."
        )

    if readiness == "MANUAL_VERIFY":
        return (
            f"Confirm {person}'s decision-making role "
            "before outreach."
        )

    if readiness == "VERIFY_IDENTITY":
        return (
            "Cross-check person, role and company relationship."
        )

    if readiness == "IDENTITY_RESEARCH":
        return (
            "Identify an owner, founder, director, producer "
            "or operations contact before outreach."
        )

    return "Keep in research queue."


def main():

    with open(
        INPUT_FILE,
        newline="",
        encoding="utf-8",
    ) as f:
        rows = list(csv.DictReader(f))

    output = []

    for row in rows:

        result = dict(row)

        readiness = determine_readiness(row)

        result["Observed Business Signals"] = (
            build_observed_signals(row)
        )

        result["Support Opportunity"] = (
            build_support_opportunity(row)
        )

        result["Outreach Readiness"] = readiness

        result["Recommended Outreach Channel"] = (
            determine_channel(row)
        )

        # Fields intentionally left for human review.
        result["Human Verified"] = "NO"
        result["Recent Activity Checked"] = "NO"
        result["Personalization Hook"] = ""
        result["Portfolio URL"] = ""
        result["Outreach Draft"] = ""
        result["Outreach Approved"] = "NO"

        # CRM tracking
        result["Contacted"] = "NO"
        result["Date Contacted"] = ""
        result["Follow Up Date"] = ""
        result["Response Status"] = "NOT_CONTACTED"
        result["Pipeline Status"] = readiness
        result["CRM Notes"] = ""

        result["V06 Next Action"] = (
            build_next_action(
                row,
                readiness,
            )
        )

        result["V06 Generated At"] = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        output.append(result)

    # Strongest opportunities first.
    priority = {
        "READY_FOR_REVIEW": 0,
        "MANUAL_VERIFY": 1,
        "VERIFY_IDENTITY": 2,
        "IDENTITY_RESEARCH": 3,
        "RESEARCH": 4,
    }

    output.sort(
        key=lambda r: (
            priority.get(
                r["Outreach Readiness"],
                99,
            ),
            -int(
                r.get("V04 Overall Score")
                or 0
            ),
        )
    )

    fieldnames = list(output[0].keys())

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
        writer.writerows(output)

    print("=" * 72)
    print("AU LEAD HUNTER v0.6 — OUTREACH READINESS")
    print("=" * 72)

    print(
        f"\nProspects: {len(output)}"
    )

    for row in output:

        print(
            f"\n[{row.get('V04 Overall Score')}] "
            f"{row['Business']}"
        )

        print(
            f"  Person: "
            f"{row.get('Decision Maker') or 'NOT IDENTIFIED'}"
        )

        print(
            f"  Role: "
            f"{row.get('Decision Maker Role') or 'UNKNOWN'}"
        )

        print(
            f"  Identity confidence: "
            f"{row.get('Decision Maker Confidence')}"
        )

        print(
            f"  Readiness: "
            f"{row['Outreach Readiness']}"
        )

        print(
            f"  Channel: "
            f"{row['Recommended Outreach Channel']}"
        )

        print(
            f"  Observed: "
            f"{row['Observed Business Signals']}"
        )

        print(
            f"  Opportunity: "
            f"{row['Support Opportunity']}"
        )

        print(
            f"  Next: "
            f"{row['V06 Next Action']}"
        )

    print(
        f"\nSaved -> {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
