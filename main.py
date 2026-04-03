import json
import re
import sys
from datetime import datetime
from pathlib import Path

from config_loader import load_config
from scrapers.base import Job
from scrapers.tgw import TGWScraper
from scrapers.companies import (
    SCCHScraper,
    RISCRScraper,
    SALScraper,
    AITScraper,
    AVLLScraper,
    KEBAScraper,
    InfineonScraper,
    PrimetalsScraper,
    LAMResearchScraper,
    SiemensScraper,
    SynopsysScraper,
    VoestalpineScraper,
)
from scrapers.karriere_at import KarriereAtScraper

SCRAPERS = {
    "tgw": TGWScraper,
    "scch": SCCHScraper,
    "risc": RISCRScraper,
    "sal": SALScraper,
    "ait": AITScraper,
    "avl": AVLLScraper,
    "keba": KEBAScraper,
    "infineon": InfineonScraper,
    "primetals": PrimetalsScraper,
    "lam": LAMResearchScraper,
    "siemens": SiemensScraper,
    "synopsys": SynopsysScraper,
    "voestalpine": VoestalpineScraper,
    "karriere_at": KarriereAtScraper,
}

OUTPUT_FILE = "results.json"

LINZ_AREA_CITIES = [
    "linz", "hagenberg", "marchtrenk", "wels", "steyr",
    "pasching", "traun", "leonding", "ansfelden", "eferding",
    "gallneukirchen", "enghagen", "puchenau", "ottensheim",
    "alham", "kirchschlag", "walding", "altheim",
    "oberoesterreich", "oberösterreich",
]


def get_scraper_instances(scraper_names: list[str]) -> list:
    instances = []
    for name in scraper_names:
        if name in SCRAPERS:
            instances.append(SCRAPERS[name]())
        else:
            print(f"WARNING: Unknown scraper '{name}', skipping")
    return instances


def fetch_all_jobs(scrapers: list) -> list[Job]:
    all_jobs = []
    for scraper in scrapers:
        print(f"  Fetching from {scraper.name}...")
        try:
            jobs = scraper.fetch_jobs()
            print(f"    Found {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"    ERROR: {e}")
    return all_jobs


def matches_keywords(job: Job, config: dict) -> dict:
    keywords = config["keywords"]
    text = f"{job.title} {job.category} {job.experience_level}".lower()

    matches = {
        "is_junior_level": any(kw in text for kw in keywords["junior_level"]),
        "is_software_dev": any(kw in text for kw in keywords["software_dev"]),
        "is_math_related": any(kw in text for kw in keywords["mathematics"]),
    }

    matches["is_relevant"] = (
        matches["is_software_dev"]
        and (matches["is_junior_level"] or matches["is_math_related"])
    ) or (
        matches["is_math_related"] and matches["is_junior_level"]
    )

    return matches


def matches_location(job: Job, filters: dict) -> tuple[bool, str]:
    location_text = f"{job.location} {job.country}".lower()

    allow_remote_worldwide = filters.get("remote_worldwide", False)
    allow_remote_eu = filters.get("remote_eu", False)
    allowed_countries = [c.lower() for c in filters.get("countries", [])]

    if allow_remote_worldwide and re.search(r"\bremote\b", location_text):
        if re.search(r"(worldwide|global|anywhere|taiwan|asia)", location_text):
            return True, "remote_worldwide"
        return True, "remote"

    if allow_remote_eu and re.search(r"\bremote\b", location_text):
        return True, "remote_eu"

    if job.country.lower() in allowed_countries:
        if any(city in location_text for city in LINZ_AREA_CITIES):
            return True, "linz_area"
        return True, "austria"

    return False, ""


def filter_jobs(jobs: list[Job], config: dict) -> list[dict]:
    filters = config.get("filters", {})
    results = []

    for job in jobs:
        location_match, location_reason = matches_location(job, filters)
        if not location_match:
            continue

        match_info = matches_keywords(job, config)
        if match_info["is_relevant"]:
            results.append(
                {
                    "title": job.title,
                    "location": job.location,
                    "country": job.country,
                    "category": job.category,
                    "experience_level": job.experience_level,
                    "source": job.source,
                    "url": job.url,
                    "match_details": match_info,
                    "location_match": location_reason,
                }
            )

    return results


def save_results(results: list[dict], total: int, output_path: str) -> dict:
    output = {
        "check_date": datetime.now().isoformat(),
        "total_jobs_found": total,
        "matching_jobs": len(results),
        "results": results,
    }
    Path(output_path).write_text(json.dumps(output, indent=2), encoding="utf-8")

    docs_path = Path("docs/results.json")
    docs_path.parent.mkdir(exist_ok=True)
    docs_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    return output


def print_summary(output: dict):
    print()
    print("=" * 60)
    print("Job Checker Results")
    print("=" * 60)
    print(f"Check date: {output['check_date']}")
    print(f"Total jobs found: {output['total_jobs_found']}")
    print(f"Matching jobs: {output['matching_jobs']}")
    print()

    if output["results"]:
        print("MATCHING POSITIONS:")
        print("-" * 60)
        for i, job in enumerate(output["results"], 1):
            print(f"\n{i}. {job['title']}")
            loc = job["location"]
            country = job["country"]
            if loc.endswith(f", {country}"):
                loc = loc[: -(len(country) + 2)]
            print(f"   Location: {loc}, {country}")
            print(f"   Category: {job['category']}")
            print(f"   Experience: {job['experience_level']}")
            print(f"   Source: {job['source']}")
            print(f"   Location match: {job['location_match']}")
            details = job["match_details"]
            reasons = []
            if details["is_junior_level"]:
                reasons.append("junior-level")
            if details["is_software_dev"]:
                reasons.append("software/IT")
            if details["is_math_related"]:
                reasons.append("math/data")
            print(f"   Match: {', '.join(reasons)}")
    else:
        print("No matching positions found this check.")

    print()
    print(f"Results saved to: {OUTPUT_FILE}")
    print("=" * 60)


def main():
    config = load_config()

    print("Fetching jobs from configured sources...")
    scrapers = get_scraper_instances(config.get("scrapers", ["tgw"]))
    all_jobs = fetch_all_jobs(scrapers)

    total = len(all_jobs)
    print(f"\nTotal jobs collected: {total}")

    print("Filtering by location and keywords...")
    results = filter_jobs(all_jobs, config)

    output = save_results(results, total, OUTPUT_FILE)
    print_summary(output)

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
