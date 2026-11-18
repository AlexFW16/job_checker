# AGENTS.md

Guidance for agentic coding tools (and humans) working in this repository.

## Project overview

`job_checker` is a Python 3.12 CLI application that scrapes job postings from
Austrian tech companies' career sites and ATS feeds, filters them by keyword and
location (Linz area / Austria / remote / EU-nearby), ranks them, and writes the
matches to JSON.

- Entry point: `main.py` — orchestrates fetching, filtering, ranking, saving, and
  summary output.
- Matching: `matching.py` — location matching, required-years extraction, and the
  `JobClassifier` (relevance/tier/score). This is the "brain"; keep it separate from
  scraping and I/O.
- Scrapers: one class per company in `scrapers/`, each targeting a specific ATS,
  HTML page, JSON feed, or RSS feed. Shared helpers live in `scrapers/common.py`.
- Config: `config.json` controls keywords, location filters, and which scrapers run.
- Output: `results.json` and `docs/results.json` (the latter is deployed to
  GitHub Pages). `docs/index.html` and `docs/taiwan.html` share
  `docs/dashboard.js` / `docs/dashboard.css`; each supplies a data URL,
  currency, and region-specific filter map via `window.JOB_DASHBOARD_CONFIG`.
- Taiwan variant: `taiwan_main.py` reuses the Austria pipeline but loads
  `config_taiwan.json` (an override layered over `config.json` defaults via
  `load_taiwan_config()`), runs the `scrapers/taiwan/` scrapers, and writes
  `results.taiwan.json` / `docs/results.taiwan.json` / `history.taiwan.json`
  (`docs/taiwan.html` renders it). It runs in the weekly CI as a separate
  `continue-on-error` step.
- Tests: `tests/` (pytest). All logic is tested with local fixtures — tests must
  never hit the network.
- CI: `.github/workflows/job-checker.yml` runs the checker weekly and commits fresh results.

## Commands

All commands run from the repository root.

```bash
pip install -r requirements.txt          # runtime deps (requests, beautifulsoup4)
pip install -r requirements-dev.txt      # + pytest for the test suite
python main.py                           # run the full check; exit 0 if matches, 1 if none
python taiwan_main.py                    # run the Taiwan check (writes results.taiwan.json)
python -m py_compile main.py taiwan_main.py config_loader.py matching.py scrapers/*.py scrapers/taiwan/*.py  # syntax check
python -m pytest                         # run all offline tests
python -m pytest tests/test_matching.py::TestJobClassifier::test_junior_software_is_graduate -v
node tests/dashboard_smoke.js              # offline frontend helper tests (when Node is available)
```

There is no linter or type checker configured (no ruff/mypy/tox config). Tests use
pytest and live in `tests/`. **Never write a test that hits the network** — patch
`fetch_html`/`fetch_json`/`fetch_text` or call the parser methods directly with
inline dummy HTML/JSON/XML fixtures.

## Architecture

- `main.py`
  - `SCRAPERS` dict maps a string key (e.g. `"tgw"`, `"sal"`) to a scraper class.
    When adding a new scraper, register it here and add the key to the
    `"scrapers"` list in `config.json`.
  - `main()` loads config, instantiates scrapers, fetches all jobs, filters,
    ranks, saves results, prints summary, returns 0/1.
  - `normalize_title()` / `dedupe_results()` collapse re-postings across sources.
- `matching.py`
  - `matches_location(job, filters)` -> `(bool, reason)`; reasons are `linz_area`,
    `austria`, `remote`/`remote_worldwide`/`remote_eu`, `eu_nearby`. It
    dispatches on `filters["region"]` (default `"austria"`): region `"taiwan"`
    routes to `matches_location_taiwan()` (reasons `taipei_area`, `taiwan`,
    `remote`/`remote_worldwide`); anything else uses `matches_location_austria()`.
  - `extract_required_years()`, `detect_entry_signal()`, `analyze_experience()` —
    heuristic experience parsing (numbers, word numbers, ranges, EN/DE phrasing,
    plus guards against "founded 10 years ago" / "40 years of tradition").
  - `JobClassifier(config).classify(job)` — the single source of truth for
    relevance and tiering (see "Data flow").
  - `LINZ_AREA_CITIES`, `AUSTRIAN_CITIES`, `EU_NEARBY_CITIES` live here; extend
    them when new towns should count as local/nearby. City matching uses
    word-boundary regex (not substrings), so "Traunstein" does not match "Traun".
  - `TAIPEI_AREA_CITIES` / `TAIWAN_CITIES` are the Taiwan whitelists used by
    `matches_location_taiwan()` (both include the Chinese city names).
- `config_loader.py`
  - `load_config()` reads `config.json`, falling back to `DEFAULT_CONFIG` if the
    file is missing. `DEFAULT_CONFIG` is kept identical to the committed
    `config.json` by `tests/test_config_loader.py`.
  - `load_taiwan_config()` returns `DEFAULT_CONFIG` deep-merged with
    `config_taiwan.json` (or `DEFAULT_TAIWAN_CONFIG`): it sets
    `filters.region = "taiwan"`, replaces `scrapers`, appends `keywords_extra`
    to the keyword lists, and appends `seniority_exclude_extra` /
    `seniority_downgrade_extra`. `DEFAULT_TAIWAN_CONFIG` must equal the
    committed `config_taiwan.json`.
  - `save_config()` / `get_default_config()` / `get_default_taiwan_config()` also exist.
- `taiwan_main.py` — Taiwan runner: mirrors `main.py`, but calls
  `load_taiwan_config()`, instantiates the `scrapers/taiwan/` scrapers, and
  writes `results.taiwan.json` + `docs/results.taiwan.json` +
  `history.taiwan.json`. Reuses `fetch_all_jobs` / `filter_jobs` / `save_results`
  / `print_summary` from `main.py`.
- `scrapers/base.py`
  - `Job` is a `@dataclass`: `title`, `location`, `country`, `category`,
    `experience_level`, `source`, `url` (default `""`), `company` (default `""`),
    `raw` (default dict), `description` (default `""`, filled by
    `enrich_descriptions()`).
  - `BaseScraper(ABC)` requires `fetch_jobs() -> list[Job]` and a `name` property.
- `scrapers/common.py` — shared toolkit used by all scrapers. See "Shared helpers".
- `scrapers/companies.py` and `scrapers/tgw.py` contain the
  concrete scrapers. See "Adding or changing scrapers".

## Shared helpers (`scrapers/common.py`)

- `fetch_html(url, retries=2)` / `fetch_json(url)` — HTTP access with a recognizable
  UA header, `timeout=30`, and retry+backoff on 429/5xx. **Always use these instead
  of raw `requests.get` in new scrapers.**
- `fetch_json_post(url, payload)` — same retry/UA behaviour as `fetch_json`, for
  JSON POST APIs (e.g. EURES search).
- `build_url(base, href)` — `urljoin` wrapper that also handles protocol-relative URLs.
- `is_valid_job_title(title)` — rejects UI chrome that broad class selectors pick up
  ("Reset filters", "Did you mean", "Job Search", "Zur Bewerbung", bare dates, etc.).
  Apply it to every title before building a `Job`.
- `cap_jobs(jobs)` — caps at `MAX_JOBS_PER_SCRAPER` (currently 250).
- `parse_erecruiter_jobs(html, base_url)` — parses the JSON job model that eRecruiter
  sites embed in their pages (see below).
- `parse_rss_items(xml_text)` — returns `ElementTree` `<item>` elements.
- `clean_html_text(html)` / `fetch_text(url)` — readable, boilerplate-stripped page
  text (truncated to `MAX_DESCRIPTION_CHARS`) used to fill `Job.description`.
- `enrich_descriptions(jobs, max_fetches=300)` — concurrently fetches detail text for
  jobs missing a description (small worker pool, failures leave it empty).

## Data flow

1. `main.main()` -> `load_config()` -> `get_scraper_instances()`.
2. Each scraper's `fetch_jobs()` returns `list[Job]`. On failure a scraper returns
   `[]` rather than raising — one broken feed must never kill the run.
3. `filter_jobs()` keeps a job only if `matches_location()` AND the classifier
   marks it `is_relevant`, then sorts by `graduate_tier` then `score` descending and
   dedupes by `(normalize_title(title), url host or source)`.
4. Location matching is region-aware (`filters["region"]`, default `"austria"`).
   Austria: `linz_area` (LINZ_AREA_CITIES), `austria` (country in
   `filters.countries`), `remote`/`remote_worldwide`/`remote_eu`
   (`\bremote\b` / home-office in text), and `eu_nearby` (EU_NEARBY_CITIES,
   controlled by `filters.allow_eu_nearby`). Taiwan: `taipei_area`
   (TAIPEI_AREA_CITIES) or `taiwan`. Case-insensitive word-boundary matching.
5. `JobClassifier.classify(job)` is **domain + tier** based:
   - Domain (`is_software_dev` / `is_math_related`) is judged from title + category
     only, to avoid description boilerplate and experience_level ("Entry level",
     "Vollzeit") false positives.
   - `graduate_tier` is one of `graduate` (a junior keyword or entry signal),
     `possible`, or `excluded` (senior title or `required_years >=
     graduate_filter.exclude_min_years`). **Seniority/explicit-years exclusions win**:
     description boilerplate ("bachelor", "no experience required") can no longer
     flip an explicitly senior role back to `graduate`.
   - `is_relevant` is `domain_hit and tier != "excluded"`. `score` rewards graduate
     tier and domain keyword hits. `match_details` carries the three UI booleans
     (`is_junior_level`, `is_software_dev`, `is_math_related`) plus `score`,
     `matched_keywords`, `graduate_tier`, `required_years`, `excluded_reasons`.
6. Ranking: results sort by `graduate_tier` then `score + location_weight`, where
   `location_weight` comes from `filters.rank_weights` (Linz > Vienna > remote-EU >
   Austria > remote > EU-nearby).
7. `extract_salary(description)` fills `salary_text`/`salary_min`; `history.py`
   diffs against the committed `history.json` to set `is_new`/`first_seen`/`last_seen`.
8. Results are saved by `save_results()` to both `results.json` and
   `docs/results.json`; `save_history()` writes `history.json`.

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
- `SALScraper`: moved off Personio to a rexx-systems career site; the listing is
  server-rendered and paginated via `?start=N`, so it parses cleanly.
- `SynopsysScraper`: works via the TalentBrew RSS feed, but that feed currently
  contains no Austrian postings, so it yields `[]`.
- `SCCHScraper`: job list is loaded via JavaScript on the Contao site; the HTML
  scrape yields `[]` unless server-rendered detail links reappear.
- `RISCRScraper`: WordPress REST API returns no published `job` posts; a best-effort
  fallback parses featured `.position` cards (usually 0-2).
- ÖBB (not registered): jobs.oebb.at redirects to a CSOD SPA. The
  `rec-job-search/external/jobs` endpoint returned HTTP 401 with the anonymous
  bearer token from its own shell. Do not add a scraper until a working session
  and response shape have been verified.

Other feeds that DO work:

- `GitLabScraper` (`scrapers/greenhouse.py`, key `gitlab`): official Greenhouse
  JSON board API (`boards-api.greenhouse.io/v1/boards/gitlab/jobs`). The reusable
  `GreenhouseScraper` keeps Austrian roles plus European remote postings, maps
  multi-country locations deterministically, and dedupes by API ID/URL. Reuse the
  base class for other Greenhouse employers only after verifying their board token.
- `FrequentisScraper` (`scrapers/vienna.py`, key `frequentis`): server-rendered
  Avature job cards at `jobs.frequentis.com/careers/SearchJobs/`. Follow the
  rendered Next link (`jobOffset`, 20/page, defensive 15-page cap). Parse
  `.list__item__text__title a` and pipe-separated subtitle fields: category,
  country, city, then company. Leave description empty so enrichment fetches the
  full detail page rather than stopping at the teaser.
- `A1Scraper` (`scrapers/vienna.py`, key `a1`): official WordPress JSON API at
  `jobs.a1.com/de/wp-json/a1-group/v1/filter-jobs?country=austria`. Follow the
  absolute `nextPageUrl` (six jobs/page, defensive 50-page cap), unescape HTML
  entities, and set country Austria because of the query scope. Duplicate IDs/URLs
  are ignored; a later page failure preserves earlier pages.
- `WienEnergieScraper` (`scrapers/vienna.py`, key `wien_energie`): official d.vinci
  page at `jobs.wienerstadtwerke.at/de/p/WienEnergie/jobs`. Parse `DvinciData`
  from the inline script (do not follow the browser meta refresh): title/URL,
  categories/target groups, company, and nested locations. Append
  `locations[].address.city` so Vienna roles rank correctly.
- `VoestalpineScraper`: uses the beeSITE Global JobBoard (GJB) JSON API. The
  `/search/` endpoint only returns a default page (10 jobs) unless you send the
  frontend's search payload as a GET `?data=<json>` param with
  `SearchParameters.CountItem` (use `10000` to pull the whole feed), a `Sort`
  array and `MatchedObjectDescriptor` field list. Keep the json+urlencode payload
  format; the API ignores `page`/`offset`-style params.
- `EuresScraper` (`scrapers/eures.py`): EU public employment portal. JSON POST
  search at `europa.eu/eures/api/jv-searchengine/public/jv-search/search`; a small
  set of keyword queries plus `locationCodes`/`requiredExperienceCodes` keeps results
  bounded. Fetching is capped overall, but jobs are interleaved across query terms
  so broad early queries cannot consume the entire cap. The search response already
  contains the description (no detail fetch). Location comes from NUTS codes
  (`AT31` → Oberösterreich), plus explicit nearby-city names in the posting.
  Unofficial but documented
  (github `rorar/EURES-API-Documentation`); NUTS codes change with revisions — the API
  uses NUTS 2024 until NUTS 2027 takes effect on 1 Jan 2027.
- `FabasoftScraper`: server-rendered career page (`fabasoft.com/en/career/jobs`);
  each job is a `li.list-group-item > a[href*="/career/jobs/"]` with an `<h3>`
  title and a location `<span>`. Match both `/career/` and `/karriere/` hrefs.
- `DynatraceScraper`: the careers site is a client-side Astro/React app; the data
  comes from a **Coveo** search API (`POST dynatrace.com/api/coveo/search/` with
  `fieldsToInclude`). Keep Austrian postings plus remote European ones; detail
  pages carry schema.org `JobPosting` JSON-LD.
- `BRScraper` (B&R / ABB): Workday cxs JSON API
  (`abb.wd3.myworkdayjobs.com/wday/cxs/abb/External_Career_Page/jobs`), POST
  `{"appliedFacets":{},"limit":50,"offset":N,"searchText":"Eggelsberg"}`. The
  `locationCountry` facet is rejected (HTTP 400) and rapid repeats are throttled,
  so pagination is bounded (250 jobs), uses `retries=0`, follows the reported
  `total`, and keeps earlier pages when a later request fails.
- `JKUScraper`: JKU Jobbörse (`jobboerse.jku.at/jobs`), a server-rendered Drupal
  board for students & alumni. Pages are 1-indexed (`?page=N`, bounded to 20,
  stopping on an empty page). Parse
  `.jcl-job-teaser-content` cards: title `.jcl-job-teaser-title a`, company
  `.jcl-job-teaser-company a`, location `.jcl-job-teaser-location` (drop the
  icon `<svg>` before reading text).
- `TalentTaiwanScraper` (`scrapers/taiwan/talent_taiwan.py`, key
  `talent_taiwan`): official Taiwan portal for foreign talent. Clean JSON API at
  `api.jobs.talent.nat.gov.tw/api/jobs/search` with repeated `location` codes
  (`TPE` Taipei City, `NWT` New Taipei City), `page`/`page_size` (max 100). The
  response holds `results[]` with title/company/`location.name_en`/`salary`
  (`{min,max,currency,type}`)/`url`/`description`. Structured salary is written
  onto `Job.salary_text`/`salary_min` (see `scrapers/base.py`); `build_result()`
  prefers those over `extract_salary()`. TaiwanJobs (`job.taiwanjobs.gov.tw`) was
  probed but uses a session-bound ASP.NET AJAX postback, so it is **not** used.

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
- When changing matching/parsing logic, extend the pytest suite (`tests/`) with an
  offline fixture; verify with `python -m pytest`.

## Data / config notes

- `config.json` controls behavior at runtime: keyword lists in `keywords`
  (`junior_level`, `software_dev`, `mathematics`), seniority rules in
  `graduate_filter` (`exclude_min_years`, `seniority_exclude`,
  `seniority_downgrade`), location filters in `filters` (`countries`,
  `remote_worldwide`, `remote_eu`, `allow_eu_nearby`, `fetch_details`,
  `max_detail_fetches`), and the `scrapers` list.
- Keyword/seniority matching uses case-insensitive **word-boundary** regex via
  `TermMatcher` (not substring `in` checks), so short keywords like `"it"`/`"ai"`
  do not match inside `"digital"`/`"maintenance"`. Keep entries lowercase.
- `LINZ_AREA_CITIES` / `AUSTRIAN_CITIES` / `EU_NEARBY_CITIES` in `matching.py` are
  the whitelists for the `linz_area` / `austria` / `eu_nearby` match reasons;
  extend them when new towns should be treated as local/nearby.
- Never commit secrets (`.env` is gitignored); keep API-ish credentials out of
  `config.json` and code.

## Output contract

- `save_results()` writes a dict with keys `check_date` (timezone-aware UTC ISO
  via `datetime.now(timezone.utc).isoformat()`), `total_jobs_found`, `matching_jobs`, and
  `results` (each item has `title`, `company`, `location`, `country`, `category`,
  `experience_level`, `source`, `url`, `match_details`, `location_match`,
  `location_weight`, `salary_text`, `salary_min`, `is_new`, `first_seen`,
  `last_seen`). `match_details` keeps the three boolean signals (used by
  `docs/index.html`) plus `score` and `matched_keywords`.
- `results.json`, `docs/results.json`, and `history.json` are committed by the CI
  workflow; don't remove the docs copy.
- Taiwan reuses `save_results()` with `docs_path="docs/results.taiwan.json"`;
  its committed artifacts (`results.taiwan.json`, `docs/results.taiwan.json`,
  `history.taiwan.json`) are produced by `python taiwan_main.py`.

## CI / deployment

- `.github/workflows/job-checker.yml` installs `requirements-dev.txt`, runs the
  offline pytest suite, then `python main.py` and `python taiwan_main.py` (both
  `continue-on-error: true`) on Python 3.12, commits the result files +
  `history.json` (+ the `.taiwan` counterparts), uploads the updated `docs/`
  workspace as the Pages artifact, and deploys that artifact. The deploy job does
  not check out the workflow's original SHA (which would be one update behind).
- Dockerfile installs opencode for agent use; it is unrelated to the app logic.
- Commit message style from history: lowercase prefix `add:` / `fix:` / `update:`
  followed by a short description, plus automatic `Update job check results (YYYY-MM-DD)`.