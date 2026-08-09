import json
import logging
import re
import time
from urllib.parse import urljoin

import requests

USER_AGENT = "Mozilla/5.0 (compatible; JobChecker/1.0)"
TIMEOUT = 30
MAX_JOBS_PER_SCRAPER = 250

logger = logging.getLogger(__name__)


def build_url(base: str, href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    return urljoin(base, href)


def fetch_html(url: str, retries: int = 2) -> str:
    return _request_text(url, retries=retries)


def fetch_json(url: str, retries: int = 0) -> dict:
    text = _request_text(url, retries=retries, accept="application/json")
    return json.loads(text)


def _request_text(
    url: str,
    retries: int = 2,
    accept: str = "text/html",
) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(
                    f"HTTP {resp.status_code} for {url}", response=resp
                )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(1 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def is_valid_job_title(title: str) -> bool:
    t = title.strip()
    if not t or len(t) < 5:
        return False
    if len(t) > 200:
        return False
    lower = t.lower()
    junk_prefixes = [
        "reset filters",
        "did you mean",
        "job search",
        "zur bewerbung",
        "find vacancies",
        "apply now",
        "unsolicited application",
        "all jobs",
        "navigation",
        "skip to",
        "show more",
        "get notified",
        "select region",
        "select job profile",
    ]
    if lower in junk_prefixes:
        return False
    if re.match(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},\s*\d{4}$", lower):
        return False
    if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
        return False
    if t.isdigit():
        return False
    first_tokens = [w.lower() for w in re.split(r"\s+", t, maxsplit=2)[:2]]
    if first_tokens:
        if re.match(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$", first_tokens[0]):
            return False
    if "{{" in t or "}}" in t or "{id}" in lower:
        return False
    return True


def cap_jobs(jobs, limit: int = MAX_JOBS_PER_SCRAPER):
    return jobs[:limit]


def extract_erecruiter_model(html: str) -> dict | None:
    m = re.search(r"new JobList\(\s*[^,]+,\s*[^,]+,\s*(\{.*?\})\s*\);", html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        logger.warning("Could not parse eRecruiter model JSON")
        return None


def parse_erecruiter_jobs(html: str, base_url: str) -> list:
    from scrapers.base import Job

    model = extract_erecruiter_model(html)
    if not model:
        return []
    jobs = []
    for entry in model.get("Jobs", []):
        title = entry.get("Title", "")
        if not is_valid_job_title(title):
            continue
        location = entry.get("Location", "")
        country = (
            "Austria"
            if re.search(
                r"österreich|austria|vienna|wien|linz|graz|villach|salzburg|klagenfurt|innsbruck|hagenberg|steyr|oberlienz",
                location,
                re.I,
            )
            else ""
        )
        url = entry.get("ExternalUrl") or build_url(base_url, f"/Job/{entry.get('Id')}")
        category = entry.get("JobProfile") or entry.get("SubTitle") or ""
        jobs.append(
            Job(
                title=title,
                location=location,
                country=country,
                category=category,
                experience_level="",
                source="",
                url=url,
                raw=entry,
            )
        )
    return jobs


def parse_rss_items(xml_text: str) -> list:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    return root.findall(".//item")