import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest
from urllib.parse import urljoin

import requests

USER_AGENT = "Mozilla/5.0 (compatible; JobChecker/1.0)"
TIMEOUT = 30
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_JOBS_PER_SCRAPER = 250
MAX_DESCRIPTION_CHARS = 20000

logger = logging.getLogger(__name__)


def build_url(base: str, href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    return urljoin(base, href)


def fetch_html(url: str, retries: int = 2, timeout: int = TIMEOUT) -> str:
    return _request_text(url, retries=retries, timeout=timeout)


def fetch_json(url: str, retries: int = 1, timeout: int = TIMEOUT) -> dict:
    text = _request_text(url, retries=retries, accept="application/json", timeout=timeout)
    return json.loads(text)


def fetch_json_post(
    url: str, payload: dict, retries: int = 1, timeout: int = TIMEOUT
) -> dict:
    text = _request_text(
        url,
        retries=retries,
        accept="application/json",
        timeout=timeout,
        method="POST",
        json_body=payload,
    )
    return json.loads(text)


def _request_text(
    url: str,
    retries: int = 2,
    accept: str = "text/html",
    timeout: int = TIMEOUT,
    method: str = "GET",
    json_body: dict | None = None,
) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if method == "POST":
                resp = requests.post(url, headers=headers, json=json_body, timeout=timeout)
            else:
                resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code in RETRYABLE_STATUS_CODES:
                raise requests.HTTPError(
                    f"HTTP {resp.status_code} for {url}", response=resp
                )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_error = e
            response = getattr(e, "response", None)
            status = getattr(response, "status_code", None)
            if status is not None and status not in RETRYABLE_STATUS_CODES:
                break
            if attempt < retries:
                time.sleep(1 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def is_valid_job_title(title: str) -> bool:
    t = title.strip()
    has_cjk = bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", t))
    if not t or len(t) < (2 if has_cjk else 5):
        return False
    if len(t) > 200:
        return False
    lower = t.lower()
    junk_prefixes = [
        "reset filters",
        "did you mean",
        "job search",
        "zur bewerbung",
        "zur position",
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
    # Exact match for single-word UI chrome ("Navigation") so real titles like
    # "Navigation Engineer" survive; prefix match only for multi-word phrases.
    if any(
        lower == junk or (" " in junk and lower.startswith(junk + " "))
        for junk in junk_prefixes
    ):
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
    m = re.search(r"new\s+JobList\(.*?,\s*(\{.*?\})\s*\)\s*;", html, re.S)
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


def clean_html_text(html: str, max_chars: int = MAX_DESCRIPTION_CHARS) -> str:
    """Strip boilerplate and return readable text, truncated to max_chars."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(
        ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "iframe"]
    ):
        tag.decompose()
    container = soup.find("main") or soup.body or soup
    text = container.get_text(" ", strip=True) if container else ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"(?:https?|ftp)://[^\s\"'<>]+", " ", text)
    text = re.sub(r"\b(?:www)\.[^\s\"'<>]+\.[^\s\"'<>]+", " ", text)
    text = re.sub(r"\S+\.php\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def fetch_text(url: str, retries: int = 1, max_chars: int = MAX_DESCRIPTION_CHARS) -> str:
    html = fetch_html(url, retries=retries, timeout=20)
    return clean_html_text(html, max_chars=max_chars)


def enrich_descriptions(jobs: list, max_fetches: int = 300, max_workers: int = 6) -> int:
    """Fetch detail-page text for jobs without a description yet.

    Runs concurrent detail fetches (politely, small worker pool). Job objects are
    mutated in place; failures leave ``description`` empty. Returns jobs fetched.
    """
    todo = [j for j in jobs if j.url.startswith("http") and not j.description]
    if not todo:
        return 0
    by_source = {}
    for job in todo:
        by_source.setdefault(job.source, []).append(job)
    todo = [
        job
        for group in zip_longest(*by_source.values())
        for job in group
        if job is not None
    ][:max_fetches]

    def load(job) -> None:
        try:
            job.description = fetch_text(job.url)
        except Exception:
            job.description = ""

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(load, todo))
    return len(todo)