import csv
from pathlib import Path
from collections import Counter

INPUT = Path("sydney_video_ops_v064_gated_evidence.csv")
OUTPUT = Path("sydney_video_ops_v065_approval_queue.csv")

if not INPUT.exists():
    raise SystemExit(f"Missing input file: {INPUT}")

with INPUT.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit("Input CSV contains no rows.")

# Inspect available columns so the script tolerates minor naming differences.
fieldnames = rows[0].keys()


def first_value(row, *names):
    """Return the first populated field matching one of the supplied names."""
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


approval_rows = []

for index, row in enumerate(rows, start=1):

    gate_status = first_value(
        row,
        "Gate Status",
        "GateStatus",
        "Validation Status",
        "Status",
    ).upper()

    # FAIL evidence stays in the evidence ledger but does not enter
    # the normal human approval queue.
    if gate_status == "FAIL":
        continue

    company = first_value(
        row,
        "Business",
        "Company",
    )

    evidence_type = first_value(
        row,
        "Evidence Type",
        "Type",
    )

    evidence_score = first_value(
        row,
        "Evidence Score",
        "Rank Score",
        "Score",
    )

    claim = first_value(
        row,
        "Claim",
        "Evidence",
        "Evidence Text",
        "Text",
    )

    source_url = first_value(
        row,
        "Source URL",
        "Source",
        "URL",
    )

    strengths = first_value(
        row,
        "Gate Strengths",
        "Strengths",
        "Strength",
    )

    review_flags = first_value(
        row,
        "Gate Review Flags",
        "Review Flags",
        "Review",
    )

    failures = first_value(
        row,
        "Gate Failures",
        "Failures",
        "Fail",
    )

    evidence_id = f"E{index:04d}"

    approval_rows.append({
        "Evidence ID": evidence_id,
        "Company": company,
        "Evidence Type": evidence_type,
        "Evidence Score": evidence_score,
        "Raw Claim": claim,
        "Source URL": source_url,
        "Gate Status": gate_status,
        "Gate Strengths": strengths,
        "Gate Review Flags": review_flags,
        "Gate Failures": failures,

        # Human-controlled fields.
        "Human Decision": "PENDING",
        "Human Notes": "",
        "Approved Claim": "",
        "Approved For Outreach": "NO",
        "Reviewed At": "",
    })


output_fields = [
    "Evidence ID",
    "Company",
    "Evidence Type",
    "Evidence Score",
    "Raw Claim",
    "Source URL",
    "Gate Status",
    "Gate Strengths",
    "Gate Review Flags",
    "Gate Failures",
    "Human Decision",
    "Human Notes",
    "Approved Claim",
    "Approved For Outreach",
    "Reviewed At",
]

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=output_fields)
    writer.writeheader()
    writer.writerows(approval_rows)


print("=" * 72)
print("AU LEAD HUNTER v0.6.5 — HUMAN EVIDENCE APPROVAL QUEUE")
print("=" * 72)

print(f"\nInput evidence: {len(rows)}")
print(f"Approval queue: {len(approval_rows)}")
print(f"Excluded FAIL: {len(rows) - len(approval_rows)}")

status_counts = Counter(
    row["Gate Status"]
    for row in approval_rows
)

print("\nGATE STATUS")

for status, count in sorted(status_counts.items()):
    print(f"  {status:<10} {count}")

company_counts = Counter(
    row["Company"]
    for row in approval_rows
)

print("\nEVIDENCE FOR HUMAN REVIEW")

for company, count in sorted(company_counts.items()):
    print(f"  {count:>3}  {company}")

print("\nHUMAN DECISION OPTIONS")
print("  APPROVE  = evidence is factual and useful")
print("  REJECT   = evidence should not be used")
print("  HOLD     = requires more research")
print("  PENDING  = not reviewed yet")

print("\nIMPORTANT")
print("Machine PASS does not equal human approval.")
print("Approved For Outreach must remain NO until manually reviewed.")

print(f"\nSaved -> {OUTPUT}")
