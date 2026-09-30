import csv
import re
import time
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests


INPUT_FILE = "sydney_video_ops_v02_crm.csv"
OUTPUT_FILE = "sydney_video_ops_v03_researched.csv"

# For our first research run, only investigate the 31 A-tier leads.
MIN_TIER = {"A"}

REQUEST_TIMEOUT = 12
SLEEP_BETWEEN_SITES = 0.8
MAX_EXTRA_PAGES = 3

USER_AGENT = (
    "AU-Lead-Hunter/0.3 "
    "(local business prospect research)"
)


SERVICE_GROUPS = {
    "commercial_corporate": [
        "commercial video",
        "corporate video",
        "corporate film",
        "brand film",
        "brand video",
        "business video",
    ],
    "real_estate_property": [
        "real estate video",
        "real estate photography",
        "property video",
        "property photography",
        "real estate media",
        "property media",
        "real estate",
    ],
    "wedding_event": [
        "wedding videography",
        "wedding video",
        "event videography",
        "event video",
        "event production",
    ],
    "social_content": [
        "social media content",
        "social media video",
        "content creation",
        "social content",
        "short form video",
        "short-form video",
        "reels",
        "tiktok",
    ],
    "editing_post": [
        "video editing",
        "video editor",
        "post production",
        "post-production",
        "editing",
    ],
    "live_streaming": [
        "live streaming",
        "livestream",
        "live stream",
        "webcast",
    ],
    "drone": [
        "drone",
        "aerial photography",
        "aerial video",
        "aerial cinematography",
    ],
    "photography": [
        "photography",
        "photographer",
    ],
}


OPERATIONS_SIGNALS = {
    "quote": [
        "request a quote",
        "get a quote",
        "quote",
        "quotation",
    ],
    "enquiry": [
        "enquiry",
        "inquiry",
        "enquire",
        "contact us",
        "get in touch",
    ],
    "booking": [
        "book now",
        "booking",
        "book a shoot",
        "schedule",
        "availability",
    ],
    "projects_clients": [
        "our clients",
        "clients",
        "projects",
        "case studies",
        "portfolio",
    ],
    "team": [
        "our team",
        "meet the team",
        "founder",
        "owner",
        "director",
        "producer",
    ],
    "repeat_work": [
        "ongoing",
        "retainer",
        "monthly",
        "recurring",
        "regular clients",
    ],
}


SOCIAL_DOMAINS = {
    "instagram.com": "Instagram",
    "linkedin.com": "LinkedIn",
    "facebook.com": "Facebook",
    "youtube.com": "YouTube",
    "tiktok.com": "TikTok",
}


NICHE_WEIGHTS = {
    "real_estate_property": 10,
    "commercial_corporate": 9,
    "social_content": 9,
    "editing_post": 7,
    "live_streaming": 6,
    "drone": 5,
    "wedding_event": 4,
    "photography": 2,
}


class PageParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.title = []
        self.meta_description = ""
        self.links = []
        self.text_chunks = []

        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):

        attrs_dict = dict(attrs)

        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return

        if tag == "title":
            self._in_title = True

        if tag == "meta":

            name = (
                attrs_dict.get("name") or ""
            ).lower()

            if name == "description":

                self.meta_description = (
                    attrs_dict.get("content") or ""
                ).strip()

        if tag == "a":

            href = attrs_dict.get("href")

            if href:
                self.links.append(href)

    def handle_endtag(self, tag):

        if tag in {"script", "style", "noscript", "svg"}:

            self._skip_depth = max(
                0,
                self._skip_depth - 1
            )

            return

        if tag == "title":
            self._in_title = False

    def handle_data(self, data):

        if self._skip_depth:
            return

        text = re.sub(
            r"\s+",
            " ",
            data
        ).strip()

        if not text:
            return

        self.text_chunks.append(text)

        if self._in_title:
            self.title.append(text)


def clean_text(value):

    value = value or ""

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def fetch_page(url):

    try:

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT
            },
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return None

        content_type = (
            response.headers.get(
                "Content-Type"
            ) or ""
        ).lower()

        if "text/html" not in content_type:
            return None

        parser = PageParser()

        parser.feed(
            response.text
        )

        return {
            "url": response.url,
            "title": clean_text(
                " ".join(parser.title)
            ),
            "description": clean_text(
                parser.meta_description
            ),
            "text": clean_text(
                " ".join(
                    parser.text_chunks
                )
            ),
            "links": parser.links,
        }

    except requests.RequestException:

        return None


def same_domain(a, b):

    a_host = (
        urlparse(a)
        .netloc
        .lower()
        .replace("www.", "")
    )

    b_host = (
        urlparse(b)
        .netloc
        .lower()
        .replace("www.", "")
    )

    return a_host == b_host


def discover_extra_pages(home):

    base_url = home["url"]

    candidates = []

    preferred_words = [
        "about",
        "services",
        "service",
        "team",
        "contact",
        "portfolio",
        "work",
        "production",
    ]

    for link in home["links"]:

        if not link:
            continue

        absolute = urljoin(
            base_url,
            link
        )

        if not absolute.startswith(
            ("http://", "https://")
        ):
            continue

        if not same_domain(
            base_url,
            absolute
        ):
            continue

        low = absolute.lower()

        if any(
            word in low
            for word in preferred_words
        ):
            candidates.append(
                absolute
            )

    seen = set()
    result = []

    for url in candidates:

        if url in seen:
            continue

        seen.add(url)
        result.append(url)

    return result[:MAX_EXTRA_PAGES]


def find_signals(text, groups):

    lower = text.lower()

    found = {}

    for group, phrases in groups.items():

        matches = []

        for phrase in phrases:

            if phrase in lower:
                matches.append(phrase)

        if matches:

            found[group] = matches[:5]

    return found


def find_socials(links):

    found = {}

    for link in links:

        host = (
            urlparse(link)
            .netloc
            .lower()
            .replace("www.", "")
        )

        for domain, label in SOCIAL_DOMAINS.items():

            if (
                host == domain
                or host.endswith("." + domain)
            ):

                found[label] = link

    return found


def classify_niche(service_signals):

    if not service_signals:
        return "general_video"

    return max(
        service_signals,
        key=lambda x:
        NICHE_WEIGHTS.get(x, 0)
    )


def calculate_ops_score(
    service_signals,
    operations_signals,
    social_links,
    pages_count,
):

    score = 0
    reasons = []

    service_count = len(
        service_signals
    )

    if service_count >= 4:

        score += 20

        reasons.append(
            f"broad service mix "
            f"({service_count} groups)"
        )

    elif service_count >= 2:

        score += 14

        reasons.append(
            f"multiple service groups "
            f"({service_count})"
        )

    elif service_count == 1:

        score += 7

        reasons.append(
            "one clear service group"
        )

    if "quote" in operations_signals:

        score += 8
        reasons.append(
            "quote workflow"
        )

    if "enquiry" in operations_signals:

        score += 7
        reasons.append(
            "customer enquiry workflow"
        )

    if "booking" in operations_signals:

        score += 8
        reasons.append(
            "booking/scheduling workflow"
        )

    if "projects_clients" in operations_signals:

        score += 8
        reasons.append(
            "client/project workflow"
        )

    if "team" in operations_signals:

        score += 6
        reasons.append(
            "team/role signals"
        )

    if "repeat_work" in operations_signals:

        score += 8
        reasons.append(
            "recurring-work signal"
        )

    if social_links:

        score += 6

        reasons.append(
            "social presence: "
            + ", ".join(
                sorted(social_links)
            )
        )

    if pages_count >= 3:

        score += 4

        reasons.append(
            "multi-page business site"
        )

    return (
        min(score, 100),
        reasons,
    )


def classify_priority(
    base_score,
    ops_score,
    niche,
):

    combined = round(
        (base_score * 0.45)
        +
        (ops_score * 0.55)
    )

    combined += (
        NICHE_WEIGHTS.get(
            niche,
            0
        ) // 2
    )

    combined = min(
        combined,
        100
    )

    if combined >= 75:

        tier = "PRIORITY"

    elif combined >= 60:

        tier = "QUALIFIED"

    elif combined >= 45:

        tier = "RESEARCH"

    else:

        tier = "LOW_FIT"

    return combined, tier


def build_pitch_angle(
    niche,
    operations_signals,
):

    if niche == "real_estate_property":

        base = (
            "Real-estate/property video workflow "
            "may benefit from client follow-up, "
            "project coordination and QA."
        )

    elif niche == "commercial_corporate":

        base = (
            "Commercial/corporate production "
            "may benefit from client coordination, "
            "CRM/admin and QA."
        )

    elif niche == "social_content":

        base = (
            "Content-heavy workflow may benefit "
            "from client follow-up, project tracking "
            "and social operations."
        )

    elif niche == "wedding_event":

        base = (
            "Event/wedding workflow may benefit "
            "from client communication, tracking "
            "and delivery coordination."
        )

    else:

        base = (
            "Video-production workflow may benefit "
            "from client follow-up, CRM/admin, "
            "project coordination and QA."
        )

    if "booking" in operations_signals:

        base += (
            " Booking/scheduling is visible "
            "on the site."
        )

    if "quote" in operations_signals:

        base += (
            " Quote/enquiry workflow "
            "is visible."
        )

    return base


def research_row(row):

    website = (
        row.get("Website") or ""
    ).strip()

    result = {
        **row,

        "Research Status":
            "NO WEBSITE",

        "Website Title":
            "",

        "Website Description":
            "",

        "Service Signals":
            "",

        "Operations Signals":
            "",

        "Social Profiles":
            "",

        "Niche":
            "unknown",

        "Operations Score":
            0,

        "Prospect Score":
            0,

        "Prospect Tier":
            "LOW_FIT",

        "Prospecting Reason":
            "",

        "Pitch Angle":
            "",
    }

    if not website:
        return result

    if not website.startswith(
        ("http://", "https://")
    ):

        website = (
            "https://" + website
        )

    home = fetch_page(
        website
    )

    if not home:

        result[
            "Research Status"
        ] = "SITE UNREACHABLE"

        result[
            "Prospect Score"
        ] = int(
            row.get("Score") or 0
        )

        result[
            "Prospect Tier"
        ] = "RESEARCH"

        return result

    pages = [home]

    extra_urls = (
        discover_extra_pages(home)
    )

    for url in extra_urls:

        time.sleep(0.4)

        page = fetch_page(url)

        if page:
            pages.append(page)

    combined_text = "\n".join(
        [
            page["title"]
            + "\n"
            + page["description"]
            + "\n"
            + page["text"]

            for page in pages
        ]
    )

    combined_links = []

    for page in pages:

        combined_links.extend(
            page["links"]
        )

    service_signals = find_signals(
        combined_text,
        SERVICE_GROUPS,
    )

    operation_signals = find_signals(
        combined_text,
        OPERATIONS_SIGNALS,
    )

    socials = find_socials(
        combined_links
    )

    service_groups = sorted(
        service_signals.keys()
    )

    operation_groups = sorted(
        operation_signals.keys()
    )

    niche = classify_niche(
        service_signals
    )

    ops_score, reasons = (
        calculate_ops_score(
            service_signals,
            operation_signals,
            socials,
            len(pages),
        )
    )

    base_score = int(
        row.get("Score") or 0
    )

    (
        prospect_score,
        prospect_tier,
    ) = classify_priority(
        base_score,
        ops_score,
        niche,
    )

    pitch_angle = (
        build_pitch_angle(
            niche,
            operation_signals,
        )
    )

    result.update(
        {
            "Research Status":
                "RESEARCHED",

            "Website Title":
                home["title"],

            "Website Description":
                home["description"],

            "Service Signals":
                ", ".join(
                    service_groups
                ),

            "Operations Signals":
                ", ".join(
                    operation_groups
                ),

            "Social Profiles":
                ", ".join(
                    f"{name}: {url}"
                    for name, url
                    in sorted(
                        socials.items()
                    )
                ),

            "Niche":
                niche,

            "Operations Score":
                ops_score,

            "Prospect Score":
                prospect_score,

            "Prospect Tier":
                prospect_tier,

            "Prospecting Reason":
                "; ".join(
                    reasons
                ),

            "Pitch Angle":
                pitch_angle,
        }
    )

    return result


def main():

    with open(
        INPUT_FILE,
        newline="",
        encoding="utf-8-sig",
    ) as f:

        rows = list(
            csv.DictReader(f)
        )

    rows = [
        row
        for row in rows
        if (
            row.get("Tier") or ""
        ).strip() in MIN_TIER
    ]

    print("=" * 70)
    print(
        "AU LEAD HUNTER v0.3"
    )
    print(
        "Website + Operations Research"
    )
    print("=" * 70)

    print(
        f"\nA-tier candidates "
        f"to research: {len(rows)}"
    )

    results = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        business = (
            row.get("Business")
            or "Unknown"
        )

        print(
            f"[{index}/{len(rows)}] "
            f"{business}"
        )

        results.append(
            research_row(row)
        )

        if index < len(rows):

            time.sleep(
                SLEEP_BETWEEN_SITES
            )

    if not results:

        print(
            "\nNo candidates found."
        )

        return

    fieldnames = list(
        results[0].keys()
    )

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

    tiers = Counter(
        row["Prospect Tier"]
        for row in results
    )

    niches = Counter(
        row["Niche"]
        for row in results
    )

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)

    print(
        f"\nOutput: {OUTPUT_FILE}"
    )

    print("\nProspect tiers:")

    for tier in [
        "PRIORITY",
        "QUALIFIED",
        "RESEARCH",
        "LOW_FIT",
    ]:

        print(
            f"  {tier}: "
            f"{tiers.get(tier, 0)}"
        )

    print("\nNiches:")

    for niche, count in (
        niches.most_common()
    ):

        print(
            f"  {niche}: {count}"
        )

    print("\nTop prospects:")

    top = sorted(
        results,
        key=lambda x: int(
            x.get(
                "Prospect Score"
            ) or 0
        ),
        reverse=True,
    )

    for row in top[:15]:

        print(
            f"\n"
            f"[{row['Prospect Score']}] "
            f"{row['Prospect Tier']} — "
            f"{row['Business']}"
        )

        print(
            f"  Niche: "
            f"{row['Niche']}"
        )

        print(
            f"  Ops score: "
            f"{row['Operations Score']}"
        )

        print(
            f"  Services: "
            f"{row['Service Signals']}"
        )

        print(
            f"  Operations: "
            f"{row['Operations Signals']}"
        )

        print(
            f"  Socials: "
            f"{row['Social Profiles']}"
        )

        print(
            f"  Reason: "
            f"{row['Prospecting Reason']}"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
