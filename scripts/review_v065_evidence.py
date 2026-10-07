import csv
from pathlib import Path
from datetime import datetime

FILE = Path("sydney_video_ops_v065_approval_queue.csv")

if not FILE.exists():
    raise SystemExit(f"Missing file: {FILE}")

with FILE.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit("Approval queue is empty.")

fieldnames = list(rows[0].keys())


def save():
    with FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def shorten(text, length=650):
    text = " ".join((text or "").split())

    if len(text) <= length:
        return text

    return text[:length] + "..."


pending = [
    row for row in rows
    if row.get("Human Decision", "").strip().upper()
    == "PENDING"
]

print("=" * 72)
print("AU LEAD HUNTER v0.6.5 — HUMAN EVIDENCE REVIEW")
print("=" * 72)

print(f"\nTotal evidence: {len(rows)}")
print(f"Pending review: {len(pending)}")

if not pending:
    print("\nNothing left to review.")
    raise SystemExit(0)


for row in rows:

    if (
        row.get("Human Decision", "")
        .strip()
        .upper()
        != "PENDING"
    ):
        continue

    print("\n" + "=" * 72)

    print(
        f"{row.get('Evidence ID')} | "
        f"{row.get('Company')}"
    )

    print("=" * 72)

    print(
        f"Type: {row.get('Evidence Type')}"
    )

    print(
        f"Score: {row.get('Evidence Score')}"
    )

    print(
        f"Machine gate: {row.get('Gate Status')}"
    )

    strengths = row.get(
        "Gate Strengths",
        ""
    )

    reviews = row.get(
        "Gate Review Flags",
        ""
    )

    if strengths:
        print(f"Strengths: {strengths}")

    if reviews:
        print(f"Review flags: {reviews}")

    print("\nEVIDENCE")
    print("-" * 72)

    print(
        shorten(
            row.get("Raw Claim", "")
        )
    )

    print("\nSOURCE")
    print("-" * 72)

    print(
        row.get("Source URL", "")
    )

    print("\nDECISION")
    print(
        "[A] Approve   "
        "[R] Reject   "
        "[H] Hold   "
        "[S] Skip   "
        "[Q] Quit"
    )

    while True:

        choice = (
            input("> ")
            .strip()
            .upper()
        )

        if choice in {
            "A",
            "R",
            "H",
            "S",
            "Q",
        }:
            break

        print(
            "Enter A, R, H, S or Q."
        )

    if choice == "Q":
        save()
        print("\nProgress saved.")
        break

    if choice == "S":
        continue
    if choice == "A":

        row["Human Decision"] = "APPROVE"

        print(
            "\nWrite a short factual approved claim."
        )

        print(
            "Do not add anything not supported "
            "by the evidence."
        )

        while True:
            claim = input(
                "Approved claim: "
            ).strip()

            blocked_claims = {
                "a",
                "good",
                "ok",
                "okay",
                "yes",
                "approved",
                "looks good",
                "fine",
            }

            if len(claim) < 25:
                print(
                    "Claim is too short. Write a factual claim "
                    "of at least 25 characters."
                )
                continue

            if claim.lower() in blocked_claims:
                print(
                    "This looks like a placeholder, not a factual claim."
                )
                continue

            break

        row["Approved Claim"] = claim

        row[
            "Approved For Outreach"
        ] = "YES"

    elif choice == "R":

        row["Human Decision"] = "REJECT"

        note = input(
            "Reason (optional): "
        ).strip()

        row["Human Notes"] = note

        row[
            "Approved For Outreach"
        ] = "NO"

    elif choice == "H":

        row["Human Decision"] = "HOLD"

        note = input(
            "What needs verification? "
        ).strip()

        row["Human Notes"] = note

        row[
            "Approved For Outreach"
        ] = "NO"

print("\n" + "=" * 72)
print("REVIEW STATUS")
print("=" * 72)

print(f"Approved: {approved}")
print(f"Rejected: {rejected}")
print(f"Hold:     {held}")
print(f"Pending:  {remaining}")
remaining = sum(
    1
    for row in rows
    if row.get(
        "Human Decision",
        ""
    ).strip().upper()
    == "PENDING"
)

approved = sum(
    1
    for row in rows
    if row.get(
        "Human Decision",
        ""
    ).strip().upper()
    == "APPROVE"
)

rejected = sum(
    1
    for row in rows
    if row.get(
        "Human Decision",
        ""
    ).strip().upper()
    == "REJECT"
)

held = sum(
    1
    for row in rows
    if row.get(
        "Human Decision",
        ""
    ).strip().upper()
    == "HOLD"
)
