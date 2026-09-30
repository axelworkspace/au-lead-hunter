import csv
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

INPUT = "sydney_video_ops_v05_targets.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Safari/537.36"
    )
}

PAGES = [
    "",
    "/about",
    "/about-us",
    "/team",
    "/our-team",
    "/contact",
    "/contact-us",
]


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def domain(url):
    return urlparse(url).netloc.replace("www.", "")


def fetch(url):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=12,
            allow_redirects=True,
        )

        if r.status_code >= 400:
            return None

        if "text/html" not in r.headers.get(
            "Content-Type", ""
        ).lower():
            return None

        return r

    except requests.RequestException:
        return None


with open(INPUT, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))


print("=" * 72)
print("AU LEAD HUNTER v0.5 — WEBSITE IDENTITY DIAGNOSTIC")
print("=" * 72)


for row in rows:

    business = row["Business"]
    website = row["Website"]

    print("\n" + "=" * 72)
    print(business)
    print("=" * 72)

    if not website.startswith(("http://", "https://")):
        website = "https://" + website

    parsed = urlparse(website)

    base = f"{parsed.scheme}://{parsed.netloc}"

    urls = []

    # Original URL first
    urls.append(website)

    for path in PAGES:
        candidate = urljoin(base, path)

        if candidate not in urls:
            urls.append(candidate)

    found_any = False

    for url in urls:

        response = fetch(url)

        if not response:
            continue

        found_any = True

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        for tag in soup([
            "script",
            "style",
            "noscript",
            "svg",
        ]):
            tag.decompose()

        text = clean(
            soup.get_text(" ", strip=True)
        )

        # Search for useful identity/role terms
        keywords = [
            "founder",
            "co-founder",
            "owner",
            "director",
            "managing director",
            "creative director",
            "producer",
            "executive producer",
            "studio manager",
            "production manager",
            "operations",
        ]

        matches = []

        lower = text.lower()

        for keyword in keywords:

            start = 0

            while True:

                pos = lower.find(keyword, start)

                if pos == -1:
                    break

                left = max(0, pos - 120)
                right = min(
                    len(text),
                    pos + len(keyword) + 180
                )

                snippet = text[left:right]

                matches.append(
                    (keyword, snippet)
                )

                start = pos + len(keyword)

        if matches:

            print(f"\nPAGE: {response.url}")

            shown = set()

            for keyword, snippet in matches:

                fingerprint = snippet.lower()

                if fingerprint in shown:
                    continue

                shown.add(fingerprint)

                print(
                    f"\n  [{keyword.upper()}]"
                )

                print(
                    " ",
                    snippet[:350]
                )

                if len(shown) >= 8:
                    break

        # Also report personal LinkedIn links
        linkedin = []

        for a in soup.find_all(
            "a",
            href=True,
        ):

            href = urljoin(
                response.url,
                a["href"],
            )

            if (
                "linkedin.com/in/" in href.lower()
                and href not in linkedin
            ):
                linkedin.append(href)

        if linkedin:

            print(
                "\n  PERSONAL LINKEDIN:"
            )

            for link in linkedin[:10]:
                print(
                    "   ",
                    link
                )

    if not found_any:
        print("\n  No accessible pages found.")
