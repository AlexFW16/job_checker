import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from config_loader import load_config
from history import DEFAULT_MAX_AGE_DAYS, apply_history, load_history, save_history
from matching import JobClassifier, extract_salary, matches_location
from scrapers.base import Job
from scrapers.companies import (
    SCCHScraper,
    RISCRScraper,
    SALScraper,
    AITScraper,
    AVLLScraper,
    BRScraper,
    DynatraceScraper,
    FabasoftScraper,
    InfineonScraper,
    JKUScraper,
    KEBAScraper,
    PrimetalsScraper,
    LAMResearchScraper,
    SiemensScraper,
    SynopsysScraper,
    VoestalpineScraper,
)
from scrapers.common import enrich_descriptions
from scrapers.eures import EuresScraper
from scrapers.greenhouse import GitLabScraper
from scrapers.tgw import TGWScraper
from scrapers.vienna import A1Scraper, FrequentisScraper, WienEnergieScraper

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
    "eures": EuresScraper,
    "fabasoft": FabasoftScraper,
    "dynatrace": DynatraceScraper,
    "br": BRScraper,
    "jku": JKUScraper,
    "gitlab": GitLabScraper,
    "a1": A1Scraper,
    "frequentis": FrequentisScraper,
    "wien_energie": WienEnergieScraper,
}

OUTPUT_FILE = "results.json"

TIER_ORDER = {"graduate": 0, "possible": 1}

DEFAULT_RANK_WEIGHTS = {
    "linz_area": 5,
    "vienna_area": 4,
    "remote_eu": 3,
    "austria": 2,
    "remote": 2,
    "remote_worldwide": 1,
    "eu_nearby": 1,
}


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


def normalize_title(title: str) -> str:
    t = title.casefold()
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"\bm/w/d\b|\bm/f/d\b|\bw/m/d\b|\bw/m\b|\bm/w\b|\ball genders\b|\ballgender\b", " ", t)
    t = "".join(char if char.isalnum() or char.isspace() else " " for char in t)
    t = re.sub(r"\b[a-z*]\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def dedupe_results(results: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in results:
        title = normalize_title(item["title"])
        # An empty key must not merge unrelated non-Latin or symbol-only titles.
        if not title:
            unique.append(item)
            continue
        host = urlparse(item["url"]).netloc if item["url"].startswith("http") else item["source"]
        key = (title, host)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def build_result(job: Job, match_info: dict, location_reason: str, location_weight: int = 0) -> dict:
    if job.salary_text or job.salary_min is not None:
        salary_text, salary_min = job.salary_text, job.salary_min
    else:
        salary_text, salary_min = extract_salary(job.description)
    return {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "country": job.country,
        "category": job.category,
        "experience_level": job.experience_level,
        "source": job.source,
        "url": job.url,
        "match_details": match_info,
        "location_match": location_reason,
        "location_weight": location_weight,
        "salary_text": salary_text,
        "salary_min": salary_min,
    }


def domain_candidates(jobs: list[Job], config: dict) -> list[Job]:
    classifier = JobClassifier(config)
    candidates = []
    for job in jobs:
        match_info = classifier.classify(job)
        if match_info["is_software_dev"] or match_info["is_math_related"]:
            candidates.append(job)
    return candidates


def filter_jobs(jobs: list[Job], config: dict) -> tuple[list[dict], dict]:
    filters = config.get("filters", {})
    weights = filters.get("rank_weights", DEFAULT_RANK_WEIGHTS)
    classifier = JobClassifier(config)
    results = []

    for job in jobs:
        location_match, location_reason = matches_location(job, filters)
        if not location_match:
            continue

        match_info = classifier.classify(job)
        if not match_info["is_relevant"]:
            continue

        results.append(
            build_result(job, match_info, location_reason, weights.get(location_reason, 0))
        )

    tier_counts = {"graduate": 0, "possible": 0, "excluded": 0}
    for job in jobs:
        if not matches_location(job, filters)[0]:
            continue
        tier = classifier.classify(job)["graduate_tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    results.sort(
        key=lambda r: (
            TIER_ORDER.get(r["match_details"]["graduate_tier"], 9),
            -(r["match_details"]["score"] + r["location_weight"]),
        ),
    )
    return dedupe_results(results), tier_counts


def save_results(
    results: list[dict],
    total: int,
    output_path: str,
    docs_path: str = "docs/results.json",
) -> dict:
    output = {
        "check_date": datetime.now(timezone.utc).isoformat(),
        "total_jobs_found": total,
        "matching_jobs": len(results),
        "results": results,
    }
    Path(output_path).write_text(json.dumps(output, indent=2), encoding="utf-8")

    docs_file = Path(docs_path)
    docs_file.parent.mkdir(parents=True, exist_ok=True)
    docs_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    return output


def print_summary(output: dict, tier_counts: dict | None = None, output_file: str | None = None):
    print()
    print("=" * 60)
    print("Job Checker Results")
    print("=" * 60)
    print(f"Check date: {output['check_date']}")
    print(f"Total jobs found: {output['total_jobs_found']}")
    print(f"Matching jobs: {output['matching_jobs']}")
    new_count = sum(1 for r in output["results"] if r.get("is_new"))
    print(f"  new since last run: {new_count}")
    if tier_counts:
        print(
            f"  tiers: {tier_counts['graduate']} graduate-ready, "
            f"{tier_counts['possible']} possible, {tier_counts['excluded']} excluded (senior/strict-years)"
        )
    print()

    if output["results"]:
        print("MATCHING POSITIONS:")
        print("-" * 60)
        for i, job in enumerate(output["results"], 1):
            marker = " [NEW]" if job.get("is_new") else ""
            print(f"\n{i}. [{job['match_details']['graduate_tier']}]{marker} {job['title']}")
            loc = job["location"]
            country = job["country"]
            if loc.endswith(f", {country}"):
                loc = loc[: -(len(country) + 2)]
            print(f"   Location: {loc}, {country}")
            print(f"   Category: {job['category']}")
            print(f"   Experience: {job['experience_level']}")
            print(f"   Source: {job['source']}")
            print(f"   Location match: {job['location_match']}")
            if job["match_details"].get("required_years") is not None:
                print(f"   Requires: ~{job['match_details']['required_years']} years")
            if job.get("salary_text"):
                print(f"   Salary: {job['salary_text']}")
            details = job["match_details"]
            reasons = []
            if details["is_junior_level"]:
                reasons.append("junior/graduate signal")
            if details["is_software_dev"]:
                reasons.append("software/IT")
            if details["is_math_related"]:
                reasons.append("math/data")
            print(f"   Match: {', '.join(reasons)}")
    else:
        print("No matching positions found this check.")

    print()
    print(f"Results saved to: {output_file or OUTPUT_FILE}")
    print("=" * 60)


def main():
    config = load_config()
    filters = config.get("filters", {})

    print("Fetching jobs from configured sources...")
    scrapers = get_scraper_instances(config.get("scrapers", ["tgw"]))
    all_jobs = fetch_all_jobs(scrapers)

    total = len(all_jobs)
    print(f"\nTotal jobs collected: {total}")

    print("Pre-filtering by location...")
    candidates = [j for j in all_jobs if matches_location(j, filters)[0]]
    print(f"Location candidates: {len(candidates)}")

    if filters.get("fetch_details", True):
        detail_candidates = domain_candidates(candidates, config)
        print(f"Fetching job descriptions for {len(detail_candidates)} domain candidates...")
        fetched = enrich_descriptions(detail_candidates, max_fetches=filters.get("max_detail_fetches", 300))
        print(f"  Fetched descriptions for {fetched} roles")
    else:
        print("Skipping detail fetching (filters.fetch_details=false)")

    print("Filtering for graduate-friendly roles...")
    results, tier_counts = filter_jobs(candidates, config)

    history = load_history()
    max_age = filters.get("history_max_age_days", DEFAULT_MAX_AGE_DAYS)
    results, history = apply_history(results, history, max_age_days=max_age)
    save_history(history)
    new_count = sum(1 for r in results if r.get("is_new"))
    print(f"New since last run: {new_count}")

    output = save_results(results, total, OUTPUT_FILE)
    print_summary(output, tier_counts)

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())