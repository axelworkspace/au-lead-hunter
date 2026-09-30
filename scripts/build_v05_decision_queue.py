import csv

INPUT = "sydney_video_ops_v05_targets.csv"
OUTPUT = "sydney_video_ops_v05_decision_queue.csv"

NEW_COLUMNS = [
    "Decision Maker",
    "Decision Maker Role",
    "Decision Maker LinkedIn",
    "Decision Maker Source",
    "Decision Maker Confidence",
    "Decision Maker Evidence",
    "Identity Status",
    "Preferred Outreach Channel",
    "V05 Next Action",
]


with open(INPUT, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))


results = []
VERIFIED_IDENTITIES = {
    "We Make Online Videos Sydney": {
        "name": "Garth Stone",
        "role": "Managing Director & Founder",
        "linkedin": "https://au.linkedin.com/in/garth-stone",
        "source": "Company crew page + public LinkedIn",
        "confidence": "HIGH",
        "evidence": (
            "WeMOV's company crew page explicitly identifies "
            "Garth Stone as Managing Director & Founder."
        ),
    },

    "Exposed Wolf Photography & Video Production": {
        "name": "Gareth Carr",
        "role": "Founder & Director",
        "linkedin": "https://www.linkedin.com/in/exposedwolf/",
        "source": "Company About page",
        "confidence": "HIGH",
        "evidence": (
            "Exposed Wolf's company About page explicitly identifies "
            "Gareth Carr as Founder & Director."
        ),
    },
    "Aeon Films": {
        "name": "Lindsey Veasey",
        "role": "Filmmaker / Video Producer",
        "linkedin": "https://au.linkedin.com/in/lindsey-veasey-343009b4",
        "source": "Aeon Films website + public LinkedIn",
        "confidence": "MEDIUM",
        "evidence": (
            "Aeon Films' website repeatedly identifies Lindsey Veasey "
            "as filming and editing Aeon Films projects and refers to "
            "Lindsey and his team. His public LinkedIn lists Aeon Films. "
            "No reliable source was found explicitly identifying him "
            "as founder, owner, or director."
        ),
    },
    "All Angles Video": {
        "name": "Danny Vandine",
        "role": "Director / Videographer",
        "linkedin": "https://au.linkedin.com/in/dannyvandine",
        "source": "Related company team page + public LinkedIn",
        "confidence": "HIGH",
        "evidence": (
            "Public company sources identify Danny Vandine as running "
            "the All Angles Video team and as a Director at All Angles Video."
        ),
    },

    "Mak Video": {
        "name": "Dragan Dimitrovski",
        "role": "Founder",
        "linkedin": "",
        "source": "Company About page",
        "confidence": "HIGH",
        "evidence": (
            "Mak Video's company About page states that Makvideo "
            "was founded by Dragan Dimitrovski in 1998."
        ),
    },
}
for row in rows:

    result = dict(row)

    for column in NEW_COLUMNS:
        result[column] = ""

    business = (row.get("Business") or "").strip()

    # --------------------------------------------------
    # VERIFIED WEBSITE RESULT
    # --------------------------------------------------
    identity = VERIFIED_IDENTITIES.get(business)

    if identity:

        result["Decision Maker"] = identity["name"]
        result["Decision Maker Role"] = identity["role"]
        result["Decision Maker LinkedIn"] = identity["linkedin"]
        result["Decision Maker Source"] = identity["source"]
        result["Decision Maker Confidence"] = identity["confidence"]
        result["Decision Maker Evidence"] = identity["evidence"]

        result["Identity Status"] = "IDENTIFIED"

        if identity["linkedin"]:
            result["Preferred Outreach Channel"] = "LinkedIn"

        elif (row.get("Email") or "").strip():
            result["Preferred Outreach Channel"] = "Email"

        elif "Instagram:" in (row.get("Social Profiles") or ""):
            result["Preferred Outreach Channel"] = "Instagram"

        else:
            result["Preferred Outreach Channel"] = "Website/phone"

        result["V05 Next Action"] = (
            "Manually verify current role and review recent company "
            "activity before preparing personalized outreach."
        )

    # --------------------------------------------------
    # ALL OTHER TARGETS
    # --------------------------------------------------

    else:

        result["Decision Maker Confidence"] = "NONE"

        result["Identity Status"] = (
            "WEB_RESEARCH_REQUIRED"
        )

        # Existing named company email is still useful,
        # but is NOT proof of identity/role.

        email = (
            row.get("Email") or ""
        ).strip()

        socials = (
            row.get("Social Profiles") or ""
        )

        if email:
            result["Preferred Outreach Channel"] = (
                "Email pending identity verification"
            )

        elif "LinkedIn:" in socials:
            result["Preferred Outreach Channel"] = (
                "LinkedIn/company page pending identity research"
            )

        elif "Instagram:" in socials:
            result["Preferred Outreach Channel"] = (
                "Instagram pending identity research"
            )

        else:
            result["Preferred Outreach Channel"] = (
                "Website/phone pending identity research"
            )

        result["V05 Next Action"] = (
            "Run public-web decision-maker research "
            "and cross-check person + role + company."
        )

    results.append(result)


fieldnames = list(results[0].keys())


with open(
    OUTPUT,
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


print("=" * 72)
print("AU LEAD HUNTER v0.5 — DECISION QUEUE")
print("=" * 72)

print(f"\nTargets: {len(results)}")

for row in results:

    print(
        f"\n{row['Business']}"
    )

    print(
        f"  V04: "
        f"{row.get('V04 Status')} "
        f"({row.get('V04 Overall Score')})"
    )

    print(
        f"  Person: "
        f"{row['Decision Maker'] or 'NOT IDENTIFIED'}"
    )

    print(
        f"  Role: "
        f"{row['Decision Maker Role'] or 'UNKNOWN'}"
    )

    print(
        f"  Confidence: "
        f"{row['Decision Maker Confidence']}"
    )

    print(
        f"  Identity status: "
        f"{row['Identity Status']}"
    )

    print(
        f"  Channel: "
        f"{row['Preferred Outreach Channel']}"
    )


print(
    f"\nSaved -> {OUTPUT}"
)
