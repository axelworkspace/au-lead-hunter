import csv
from pathlib import Path
from collections import Counter

INPUT = Path("sydney_video_ops_v065_approval_queue.csv")
OUTPUT = Path("sydney_video_ops_v066_validated_claims.csv")

if not INPUT.exists():
    raise SystemExit(f"Missing input file: {INPUT}")

with INPUT.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit("Input file contains no rows.")


BLOCKED = {
    "a",
    "good",
    "ok",
    "okay",
    "yes",
    "approved",
    "looks good",
    "fine",
}

validated = []

for row in rows:
    decision = row.get(
        "Human Decision",
        ""
    ).strip().upper()

    outreach = row.get(
        "Approved For Outreach",
        ""
    ).strip().upper()

    claim = row.get(
        "Approved Claim",
        ""
    ).strip()

    issues = []

    if decision == "APPROVE":

        if outreach != "YES":
            issues.append(
                "APPROVED_BUT_OUTREACH_NOT_YES"
            )

        if not claim:
            issues.append(
                "MISSING_APPROVED_CLAIM"
            )

        elif len(claim) < 25:
            issues.append(
                "CLAIM_TOO_SHORT"
            )

        elif claim.lower() in BLOCKED:
            issues.append(
                "PLACEHOLDER_CLAIM"
            )

        source = row.get(
            "Source URL",
            ""
        ).strip()

        if not source:
            issues.append(
                "MISSING_SOURCE_URL"
            )

    else:

        if outreach == "YES":
            issues.append(
                "NON_APPROVED_MARKED_FOR_OUTREACH"
            )

        if claim:
            issues.append(
                "NON_APPROVED_HAS_APPROVED_CLAIM"
            )

    validation_status = (
        "VALID"
        if not issues
        else "INVALID"
    )

    validated.append({
        **row,
        "Claim Validation Status":
            validation_status,
        "Claim Validation Issues":
            ", ".join(issues),
    })


fieldnames = list(
    validated[0].keys()
)

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
    writer.writerows(validated)


counts = Counter(
    row["Claim Validation Status"]
    for row in validated
)

print("=" * 72)
print(
    "AU LEAD HUNTER v0.6.6 "
    "— APPROVED CLAIM VALIDATION"
)
print("=" * 72)

print(f"\nTotal records: {len(validated)}")

print("\nVALIDATION")
print(
    f"  VALID   {counts.get('VALID', 0)}"
)
print(
    f"  INVALID {counts.get('INVALID', 0)}"
)

print("\nOUTREACH-SAFE CLAIMS")

safe_count = 0

for row in validated:

    if (
        row["Human Decision"] == "APPROVE"
        and
        row[
            "Claim Validation Status"
        ] == "VALID"
        and
        row[
            "Approved For Outreach"
        ] == "YES"
    ):

        safe_count += 1

        print(
            f"  {row['Evidence ID']} | "
            f"{row['Company']}"
        )

        print(
            f"    {row['Approved Claim']}"
        )

print(
    f"\nTotal outreach-safe claims: "
    f"{safe_count}"
)

invalid_rows = [
    row
    for row in validated
    if row[
        "Claim Validation Status"
    ] == "INVALID"
]

if invalid_rows:

    print("\nINVALID RECORDS")

    for row in invalid_rows:

        print(
            f"  {row['Evidence ID']} | "
            f"{row['Company']}"
        )

        print(
            "    "
            + row[
                "Claim Validation Issues"
            ]
        )

print(
    f"\nSaved -> {OUTPUT}"
)
