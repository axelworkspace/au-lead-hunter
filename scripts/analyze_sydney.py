import csv
from collections import Counter

FILE = "sydney_video_ops_v02_crm.csv"

with open(FILE, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print("=" * 70)
print("AU LEAD HUNTER — SYDNEY QUALITY AUDIT")
print("=" * 70)

print(f"\nTotal rows: {len(rows)}")

tiers = Counter((r.get("Tier") or "").strip() for r in rows)

print("\nTiers:")
for tier in ["A", "B", "C"]:
    print(f"  {tier}: {tiers.get(tier, 0)}")

categories = Counter(
    (r.get("Category") or "UNKNOWN").strip()
    for r in rows
)

print("\nTop 30 categories:")
for category, count in categories.most_common(30):
    print(f"  {count:4}  {category}")

print("\n" + "=" * 70)
print("TOP A LEADS")
print("=" * 70)

a_rows = [r for r in rows if (r.get("Tier") or "").strip() == "A"]

for r in a_rows[:30]:
    print(
        f"\n[{r.get('Score')}] "
        f"{r.get('Business')} | "
        f"{r.get('Category')}"
    )
    print(f"  Website: {r.get('Website')}")
    print(f"  Why: {r.get('Why a Lead')}")

print("\n" + "=" * 70)
print("POSSIBLE FALSE POSITIVES")
print("=" * 70)

bad_words = [
    "camera",
    "printing",
    "photo lab",
    "equipment",
    "retail",
    "school",
    "museum",
    "gallery",
    "club",
    "cinema",
    "theatre",
    "theater",
]

false_positive_rows = []

for r in rows:
    text = " ".join([
        r.get("Business") or "",
        r.get("Category") or "",
        r.get("Why a Lead") or "",
    ]).lower()

    if any(word in text for word in bad_words):
        false_positive_rows.append(r)

for r in false_positive_rows[:50]:
    print(
        f"[{r.get('Score')}] "
        f"{r.get('Business')} | "
        f"{r.get('Category')}"
    )

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(
    f"\nA+B percentage: "
    f"{((tiers.get('A', 0) + tiers.get('B', 0)) / len(rows) * 100):.1f}%"
)

print(
    f"Possible false positives found by keyword test: "
    f"{len(false_positive_rows)}"
)
