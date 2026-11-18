import sys

from config_loader import load_taiwan_config
from history import DEFAULT_MAX_AGE_DAYS, apply_history, load_history, save_history
from main import fetch_all_jobs, filter_jobs, print_summary, save_results
from matching import matches_location
from scrapers.taiwan.talent_taiwan import TalentTaiwanScraper

SCRAPERS = {
    "talent_taiwan": TalentTaiwanScraper,
}

OUTPUT_FILE = "results.taiwan.json"
DOCS_FILE = "docs/results.taiwan.json"
HISTORY_FILE = "history.taiwan.json"


def get_scraper_instances(scraper_names: list[str]) -> list:
    instances = []
    for name in scraper_names:
        if name in SCRAPERS:
            instances.append(SCRAPERS[name]())
        else:
            print(f"WARNING: Unknown scraper '{name}', skipping")
    return instances


def main():
    config = load_taiwan_config()
    filters = config.get("filters", {})

    print("Fetching Taiwan jobs from configured sources...")
    scrapers = get_scraper_instances(config.get("scrapers", ["talent_taiwan"]))
    all_jobs = fetch_all_jobs(scrapers)

    total = len(all_jobs)
    print(f"\nTotal jobs collected: {total}")

    print("Pre-filtering by location (Taipei area)...")
    candidates = [j for j in all_jobs if matches_location(j, filters)[0]]
    print(f"Location candidates: {len(candidates)}")

    print("Filtering for graduate-friendly roles...")
    results, tier_counts = filter_jobs(candidates, config)

    history = load_history(HISTORY_FILE)
    max_age = filters.get("history_max_age_days", DEFAULT_MAX_AGE_DAYS)
    results, history = apply_history(results, history, max_age_days=max_age)
    save_history(history, HISTORY_FILE)
    new_count = sum(1 for r in results if r.get("is_new"))
    print(f"New since last run: {new_count}")

    output = save_results(results, total, OUTPUT_FILE, docs_path=DOCS_FILE)
    print_summary(output, tier_counts, output_file=OUTPUT_FILE)

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
