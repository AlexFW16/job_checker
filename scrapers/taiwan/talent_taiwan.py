from urllib.parse import urlencode

from scrapers.base import BaseScraper, Job
from scrapers.common import cap_jobs, fetch_json, is_valid_job_title

SEARCH_URL = "https://api.jobs.talent.nat.gov.tw/api/jobs/search"
RESULTS_PER_PAGE = 100
MAX_PAGES = 10

# Talent Taiwan only carries the overseas-talent job board; scope the pull to
# the Greater Taipei core (Taipei City + New Taipei City). Region codes match
# the API's `location` facet codes.
TAIPEI_LOCATIONS = ["TPE", "NWT"]

_SALARY_PERIODS = {
    "per_hour": "hour",
    "per_day": "day",
    "per_month": "month",
    "per_year": "year",
}


class TalentTaiwanScraper(BaseScraper):
    """Talent Taiwan overseas-talent job board (unofficial but public JSON API).

    The portal at jobs.talent.nat.gov.tw syncs postings from job platforms
    (CakeResume et al.) and serves them from api.jobs.talent.nat.gov.tw:
    /api/jobs/search?location=TPE&location=NWT&page=N&page_size=100.
    """

    @property
    def name(self) -> str:
        return "talent_taiwan"

    def fetch_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        try:
            for page in range(1, MAX_PAGES + 1):
                try:
                    payload = self._fetch_page(page)
                except Exception:
                    break
                results = payload.get("results", []) if isinstance(payload, dict) else []
                if not results:
                    break
                for item in results:
                    job = self._parse_job(item)
                    if job is None:
                        continue
                    key = job.url or item.get("id") or item.get("source_job_id")
                    if key:
                        if key in seen:
                            continue
                        seen.add(key)
                    jobs.append(job)
                total = payload.get("total", 0)
                if len(jobs) >= total or page * RESULTS_PER_PAGE >= total:
                    break
        except Exception:
            pass
        return cap_jobs(jobs)

    def _fetch_page(self, page: int) -> dict:
        params = [("page", page), ("page_size", RESULTS_PER_PAGE)]
        params.extend(("location", code) for code in TAIPEI_LOCATIONS)
        return fetch_json(f"{SEARCH_URL}?{urlencode(params)}")

    def _parse_job(self, item: dict) -> Job | None:
        if not isinstance(item, dict):
            return None
        title = (item.get("title") or "").strip()
        if not title or not is_valid_job_title(title):
            return None

        location = item.get("location") or {}
        loc_name = location.get("name_en") or location.get("name_zh") or "Taiwan"
        salary_text, salary_min = format_salary(item.get("salary"))

        return Job(
            title=title,
            location=loc_name,
            country="Taiwan",
            category=item.get("category") or "",
            experience_level="",
            source=self.name,
            url=item.get("url") or "",
            company=item.get("company") or "",
            description=item.get("description") or "",
            raw=item,
            salary_text=salary_text,
            salary_min=salary_min,
        )


def format_salary(salary: dict | None) -> tuple[str, int | float | None]:
    """Render a Talent Taiwan salary object as (text, min) for the dashboard."""
    if not isinstance(salary, dict):
        return "", None
    low = salary.get("min")
    high = salary.get("max")
    if low is None and high is None:
        return "", None
    currency = salary.get("currency") or "TWD"
    period = _SALARY_PERIODS.get(salary.get("type", ""), "")
    if low is not None and high is not None and low != high:
        amount = f"{int(low):,}–{int(high):,}"
    else:
        amount = f"{int(low if low is not None else high):,}"
    text = f"{currency} {amount}" + (f" / {period}" if period else "")
    return text, low if low is not None else high
