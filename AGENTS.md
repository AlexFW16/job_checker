# AGENTS.md

Guidance for agentic coding tools (and humans) working in this repository.

## Project overview

`job_checker` is a Python 3.12 CLI application that scrapes job postings from
Austrian tech companies' career sites and ATS feeds, filters them by keyword and
location (Linz area / Austria / remote / EU-nearby), ranks them, and writes the
matches to JSON.

- Entry point: `main.py` — orchestrates fetching, filtering, ranking, saving, and
  summary output.
- Scrapers: one class per company in `scrapers/`, each targeting a specific ATS,
  HTML page, JSON feed, or RSS feed. Shared helpers live in `scrapers/common.py`.
- Config: `config.json` controls keywords, location filters, and which scrapers run.
- Output: `results.json` and `docs/results.json` (the latter is deployed to
  GitHub Pages). `docs/index.html` renders the results.
- CI: `.github/workflows/job-checker.yml` runs the checker weekly and commits fresh results.

## Commands

All commands run from the repository root.

```bash
pip install -r requirements.txt   # install deps (requests, beautifulsoup4)
python main.py                    # run the full check; exit 0 if matches, 1 if none
python -m py_compile main.py config_loader.py scrapers/*.py  # syntax check without running
```

There is **no** test suite, linter, or type checker configured in this repo
(no pytest config, pyproject.toml, mypy, ruff, or tox). Do not assume one exists.

If you add pytest tests (recommended layout: `tests/` at repo root), run a single
test with:

```bash
python -m pytest tests/<file>.py::<TestClass>::<test_name> -v
```

and all tests with `python -m pytest`.

## Architecture

- `main.py`
  - `SCRAPERS` dict maps a string key (e.g. `"tgw"`, `"sal"`) to a scraper class.
    When adding a new scraper, register it here and add the key to the
    `"scrapers"` list in `config.json`.
  - `main()` loads config, instantiates scrapers, fetches all jobs, filters,
    ranks, saves results, prints summary, returns 0/1.
  - `LINZ_AREA_CITIES` and `EU_NEARBY_CITIES` are the location whitelists used by
    `matches_location()`; extend them when new towns should count as local/nearby.
- `config_loader.py`
  - `load_config()` reads `config.json`, falling back to `DEFAULT_CONFIG` if the
    file is missing.
  - `save_config()` / `get_default_config()` also exist.
- `scrapers/base.py`
  - `Job` is a `@dataclass`: `title`, `location`, `country`, `category`,
    `experience_level`, `source`, `url` (default `""`), `raw` (default dict).
  - `BaseScraper(ABC)` requires `fetch_jobs() -> list[Job]` and a `name` property.
- `scrapers/common.py` — shared toolkit used by all scrapers. See "Shared helpers".
- `scrapers/companies.py`, `scrapers/karriere_at.py`, `scrapers/tgw.py` contain the
  concrete scrapers. See "Adding or changing scrapers".

## Shared helpers (`scrapers/common.py`)

- `fetch_html(url, retries=2)` / `fetch_json(url)` — HTTP access with a recognizable
  UA header, `timeout=30`, and retry+backoff on 429/5xx. **Always use these instead
  of raw `requests.get` in new scrapers.**
- `build_url(base, href)` — `urljoin` wrapper that also handles protocol-relative URLs.
- `is_valid_job_title(title)` — rejects UI chrome that broad class selectors pick up
  ("Reset filters", "Did you mean", "Job Search", "Zur Bewerbung", bare dates, etc.).
  Apply it to every title before building a `Job`.
- `cap_jobs(jobs)` — caps at `MAX_JOBS_PER_SCRAPER` (currently 250).
- `parse_erecruiter_jobs(html, base_url)` — parses the JSON job model that eRecruiter
  sites embed in their pages (see below).

## Data flow

1. `main.main()` -> `load_config()` -> `get_scraper_instances()`.
2. Each scraper's `fetch_jobs()` returns `list[Job]`. On failure a scraper returns
   `[]` rather than raising — one broken feed must never kill the run.
3. `filter_jobs()` keeps a job only if `matches_location()` AND `matches_keywords()`
   both pass, then sorts by `match_details.score` descending and dedupes by
   `(title.lower(), url or source)`.
4. Location matching: `linz_area` (LINZ_AREA_CITIES), `austria` (country in
   `filters.countries`), `remote`/`remote_worldwide`/`remote_eu`
   (`\bremote\b` in text), and `eu_nearby` (EU_NEARBY_CITIES, controlled by
   `filters.allow_eu_nearby`). Matching is case-insensitive substring matching on
   lowercased text.
5. Keyword matching is **score-based**: `matches_keywords()` returns the three
   boolean signals (`is_junior_level`, `is_software_dev`, `is_math_related`), a
   `matched_keywords` list, and a `score` (count of distinct matched keywords).
   A job is relevant when `score >= min_score` (`min_score` defaults to 1 in code,
   e.g. "any signal"). Output is ranked by score desc.
6. Results are saved by `save_results()` to both `results.json` and
   `docs/results.json`.

## Guidelines for adding / editing code

### New scrapers

- Subclass `BaseScraper`, implement `fetch_jobs()` and the `name` property
  (the key used in `config.json`).
- Prefer a structured feed (JSON API, RSS, server-rendered HTML table, or the
  eRecruiter embedded model) over scraping a JS-rendered SPA. Verify each feed is
  live before writing the parser.
- Use `fetch_html()`/`fetch_json()` from `scrapers/common.py` (retries, UA, timeout).
- Parse HTML with BeautifulSoup (`from bs4 import BeautifulSoup`). Match elements
  with `class_=re.compile(r"...", re.I)` where class names are unstable, and use
  `build_url(base, href)` to absolutize relative links.
- A scraper must **never** crash the run: catch exceptions in `fetch_jobs()` and
  return `[]` on failure.
- Run every title through `is_valid_job_title()`; skip junk.
- Store `country="Austria"` only where the posting is actually in Austria; match
  against city/country substrings via `AUSTRIAN_CITIES` (in `scrapers/companies.py`).
- Keep the docstring identifying the ATS/feed in use (e.g. "uses eRecruiter ATS").

### The eRecruiter cluster (KEBA, AIT, Primetals)

These sites render the job list client-side but embed the full JSON model in the
page as `new JobList(<placeholder>, <template>, {model})`. Do **not** call their
`/api/v1/vacancies` endpoints — those are dead. Instead fetch the listing page and
use `parse_erecruiter_jobs(html, base_url)`, which extracts `Jobs[]` entries
(`Title`, `Location`, `Id`, `ExternalUrl`, ...) and builds `Job` objects.
voestalpine uses a different feed (see below).

### SPA / bot-walled sources (current status)

Scrapers that currently return `[]` intentionally (documented in their docstrings):

- `InfineonScraper` (Workday), `LAMResearchScraper` (Phenom), `SiemensScraper`
  (AvaPortal): render jobs client-side with no public JSON/RSS feed found. Keep as
  no-ops until a feed is confirmed.
- `SALScraper` (Personio): the Personio jobsite is behind a Vercel Security
  Checkpoint (HTTP 429) for non-browser clients; the scraper retries and returns `[]`.
- `SynopsysScraper`: works via the TalentBrew RSS feed, but that feed currently
  contains no Austrian postings, so it yields `[]`.
- `SCCHScraper`: job list is loaded via JavaScript on the Contao site; the HTML
  scrape yields `[]` unless server-rendered detail links reappear.
- `RISCRScraper`: WordPress REST API returns no published `job` posts; a best-effort
  fallback parses featured `.position` cards (usually 0-2).

Other feeds that DO work:

- `VoestalpineScraper`: uses the beeSITE Global JobBoard (GJB) JSON API. The
  `/search/` endpoint only returns a default page (10 jobs) unless you send the
  frontend's search payload as a GET `?data=<json>` param with
  `SearchParameters.CountItem` (use `10000` to pull the whole feed), a `Sort`
  array and `MatchedObjectDescriptor` field list. Keep the json+urlencode payload
  format; the API ignores `page`/`offset`-style params.

### Registering a scraper

1. Define the class in `scrapers/companies.py` (or a new module under `scrapers/`).
2. Import it in `main.py` and add to the `SCRAPERS` dict.
3. Add its key to `config.json`'s `"scrapers"` array if it should run by default.

### Formatting / conventions

- Python 3.12; use modern typing: `list[str]`, `dict`, `tuple[bool, str]`,
  `list | dict`, `-> None`, generics from builtins — no `typing.List`/`typing.Dict`.
- Modules are scripts + classes, no `if __name__ == "__main__"` in scrapers;
  `main.py` uses it to call `sys.exit(main())`.
- Imports: stdlib first (`json`, `re`, ...), then third-party (`requests`,
  `bs4`), then local (`scrapers.base ...`), each group separated by a blank line.
  Sort imports alphabetically within a group.
- Strings: use double quotes. Use f-strings for interpolation.
- Method/function separation: two blank lines around classes and top-level
  functions; class methods stay one per line.
- The existing code does not add comments explaining "what"; prefer short
  comments (a line or two) that explain a non-obvious "why".
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, a
  duplicate-suffix `Scraper` on scraper classes, `UPPER_SNAKE_CASE` for module
  constants (`TGW_URL`, `SEARCH_URL`, `LINZ_AREA_CITIES`, `AUSTRIAN_CITIES`).
- Internal/private methods use a leading underscore (`_parse_jobs`, `_guess_category`).
- Error handling: catch broadly in `fetch_jobs()` and return `[]`; do not swallow
  errors without returning a defined value.
- Do not introduce new third-party dependencies without updating
  `requirements.txt` (and the CI pip install).

## Data / config notes

- `config.json` controls behavior at runtime: keyword lists in `keywords`
  (`junior_level`, `software_dev`, `mathematics`), location filters in `filters`
  (`countries`, `remote_worldwide`, `remote_eu`, `allow_eu_nearby`), optional
  `min_score`, and the `scrapers` list.
- Keyword matching uses simple `in` substring checks on
  `f"{title} {category} {experience_level}".lower()` — keep keyword entries
  lowercase and un-padded (e.g. `" it"` / `"it "`) deliberately.
- `LINZ_AREA_CITIES` / `EU_NEARBY_CITIES` in `main.py` are the whitelists for the
  `linz_area` / `eu_nearby` match reasons; extend them when new towns should be
  treated as local/nearby.
- Never commit secrets (`.env` is gitignored); keep API-ish credentials out of
  `config.json` and code.

## Output contract

- `save_results()` writes a dict with keys `check_date` (ISO via
  `datetime.now().isoformat()`), `total_jobs_found`, `matching_jobs`, and
  `results` (each item has `title`, `location`, `country`, `category`,
  `experience_level`, `source`, `url`, `match_details`, `location_match`).
  `match_details` keeps the three boolean signals (used by `docs/index.html`) plus
  `score` and `matched_keywords`.
- `results.json` and `docs/results.json` are committed by the CI workflow; don't
  remove the docs copy.

## CI / deployment

- `.github/workflows/job-checker.yml` runs `pip install -r requirements.txt` then
  `python main.py` (with `continue-on-error: true`) on Python 3.12, commits the
  two result files, and deploys `docs/` to GitHub Pages.
- Dockerfile installs opencode for agent use; it is unrelated to the app logic.
- Commit message style from history: lowercase prefix `add:` / `fix:` / `update:`
  followed by a short description, plus automatic `Update job check results (YYYY-MM-DD)`.