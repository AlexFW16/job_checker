# Planning & roadmap

Working notes and future plans for `job_checker`. Keep this file updated as
features land or are dropped.

## Product goal

A personal job-hunt assistant for a Linz/Vienna-based software & data-science
candidate. Priorities, in order:

1. Surface **new** matching jobs quickly (speed-to-apply matters most).
2. Rank Linz-area, then Vienna, then broader Austria, then remote-EU highest.
3. Only junior/mid roles — no senior/lead positions.
4. Stay legal: public sources only, low volume, no personal data, respect ToS/robots.

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Remove karriere.at (ToS), source registry + this doc | done |
| 1 | Matching precision (tier from title/category/level; English seniority terms; Vienna match reason; ranking weights) | done |
| 2 | New-job detection (`history.json` diff), salary extraction, stale purge | done |
| 3 | Coverage: EURES + Fabasoft, Dynatrace, B&R/ABB, JKU scrapers | done |
| 3b | Further employers (Pro2Future, BMD, Rosenbauer, Vienna corporates) | future |
| 4 | Dashboard upgrade (NEW badge, salary/source filters, search) | done |
| 5 | Taiwan page (Taipei area): `taiwan_main.py`, `scrapers/taiwan/`, `docs/taiwan.html` | done |
| 6 | Recall fixes: Unicode/history identity, early-mid policy, domain recovery, EURES fairness/location, Workday pagination, fresh Pages deployment | done |
| 7a | Vienna / remote-EU coverage: GitLab Greenhouse, A1, Frequentis, Wien Energie | done |
| 7b | Further source expansion (ÖBB, regional employers) | future |
| 8 | Shared Austria/Taiwan dashboard: counts, AND search, reset, first-seen dates, explicit-period annual salary comparison | done |
| 9 | Exclude thesis and internship/practical-placement titles in both regions; keep PhD positions eligible | done |

## New-job detection design (Phase 2)

- Commit a `history.json` next to `results.json` (like the results files, so CI
  can persist it between weekly runs).
- Fingerprint each posting (stable id/url, else hash of normalized title+source).
- On each run: a posting is `is_new` when its fingerprint was not present in the
  previous run. Store `first_seen` / `last_seen` timestamps.
- Purge fingerprints not seen for N consecutive runs (candidate gone / expired).

## EURES design (Phase 3)

- Public EU employment portal; reverse-engineered but documented search API
  (`europa.eu/eures/api`, `POST /jv-searchengine/public/jv-search/search`).
- Query by our config keywords, `locationCodes: ["at", "de"]` (Austria + nearby
  Germany), `requiredExperienceCodes` excluding `more_than_5_years`, and a
  recent `publicationPeriod`. Keep result counts bounded (do **not** pull the
  whole feed — `cap_jobs` is 250/scraper).
- Map NUTS `locationMap` (e.g. `AT31` Linz, `AT13` Vienna, `DE` Bavaria) to
  `Job.location`/`country`.
- Strip any contact email/phone from descriptions (GDPR: no personal data).
- NUTS revision cycle: currently **NUTS 2024**; **NUTS 2027** takes effect
  1 Jan 2027 — re-verify region codes then.

## Linz/Vienna employers (Phase 3 / 3b)

Added (verified live, one-time probe; parsers covered by offline fixtures):

- **Fabasoft** (`fabasoft`) — server-rendered career page; parses `list-group`
  job cards (`<h3>` title + `<span>` location).
- **Dynatrace** (`dynatrace`) — careers site is a client-side Astro app backed by
  a **Coveo** search API (`POST /api/coveo/search/`). Keep Austrian postings plus
  remote European ones. Detail pages carry schema.org `JobPosting` JSON-LD.
- **B&R / ABB** (`br`) — Workday cxs JSON API
  (`abb.wd3.myworkdayjobs.com/wday/cxs/abb/External_Career_Page/jobs`), searched
  for the Eggelsberg HQ. Workday returns HTTP 400 on rapid repeats, so this makes
  a single request and degrades to `[]`.
- **JKU Jobbörse** (`jku`) — server-rendered Drupal board for students & alumni,
  bounded to 20 pages (`?page=N`, 1-indexed, stopping on an empty page). Parses
  `.jcl-job-teaser-*` cards.
- **EURES** (`eures`) — see below.

Not added:

- **Catalysts** — now part of Cloudflight; its SmartRecruiters feed holds a single
  stale 2017 posting in Romania, so there is nothing relevant to scrape.
- **ÖBB** — the official CSOD SPA's job-search endpoint returned HTTP 401 with
  its own anonymous bearer token (probe stopped at the agreed request cap). A
  further source probe needs a working session/API contract before a scraper is
  safe to implement.

Remote-EU and Vienna sources added (live feed verified once; offline fixtures):

- **GitLab** (`gitlab`) — public Greenhouse board API, filtered to Austrian or
  European-remote roles. The scraper preserves API IDs and distinguishes multiple
  country locations. The live board sample produced 8 relevant European-remote
  engineering roles under the current filters.
- **A1** (`a1`) — official paginated WordPress jobs API, scoped to Austria; the
  first live response reported 62 postings across 11 pages.
- **Wien Energie** (`wien_energie`) — official d.vinci `DvinciData` JSON model,
  with structured company, category, target-group, and Viennese location fields.
- **Frequentis** (`frequentis`) — official server-rendered Avature cards with
  category/country/city/company fields and offset pagination. The Vienna-filtered
  listing had 15 postings at feed-verification time; the scraper uses the
  unfiltered listing so Linz and remote postings are not excluded prematurely.

Future candidates (each still needs a live feed check first): Pro2Future,
Softwarepark Hagenberg cluster, BMD (Steyr), Fill (Gurten), BMW Motoren (Steyr),
Rosenbauer (Leonding), Trumpf (Pasching), FH Oberösterreich.

## AMS ("alle jobs") — feasibility note

Austria's public employment service, ~100k vacancies and the widest national
coverage. **No public read API:** the search backend requires a per-request
signed token computed by AMS's own Angular frontend, so integration would need a
headless browser (fragile). The documented `AMS-HR-API` is employer-side only
(submitting vacancies). Since Austrian vacancies also flow into EURES, AMS is
deferred; revisit only if EURES coverage proves insufficient.

## Taiwan page (Phase 5)

**Goal:** a separate, self-contained section of the dashboard listing jobs in
the **Taipei area** suited to a JKU alumnus.

**Why JKU matters:** Johannes Kepler University Linz is ranked inside the global
top 1000. That standing is relevant for a Taiwan work permit / Employment Gold
Card points and for academic-recognition routes. *Still to verify:* which
ranking (QS/THE) is referenced, and whether the Ministry of Education recognizes
the degree for the specific permit category.

**Implementation**
- Runner: `taiwan_main.py` (mirrors `main.py` but uses `load_taiwan_config()`
  and reuses `fetch_all_jobs` / `filter_jobs` / `save_results` / `print_summary`).
- Data: `results.taiwan.json` (+ `docs/results.taiwan.json`), history in
  `history.taiwan.json`. Page: `docs/taiwan.html` (linked from `docs/index.html`).
- Scraper: `scrapers/taiwan/talent_taiwan.py`.
- Config: `config_taiwan.json` (committed) = `DEFAULT_TAIWAN_CONFIG`; it is a
  small **override** merged over `DEFAULT_CONFIG` (`load_taiwan_config()`), so
  the Austria keyword lists stay the single source of truth. Taiwan adds Chinese
  keywords (`工程師`, `軟體`, `資深`, …) via `keywords_extra` /
  `seniority_*_extra` and sets `filters.region = "taiwan"`.
- Matching: `matching.matches_location()` dispatches on `filters["region"]`;
  `matches_location_taiwan()` uses `TAIPEI_AREA_CITIES` / `TAIWAN_CITIES`.
- CI: wired into the weekly workflow as a second step (`continue-on-error: true`),
  committing `results.taiwan.json` / `docs/results.taiwan.json` /
  `history.taiwan.json` alongside the Austria outputs.

**Source used (live-verified once)**
- **Talent Taiwan** (`api.jobs.talent.nat.gov.tw`) — official government portal
  for foreign talent; a clean JSON search API
  (`/api/jobs/search?location=TPE&location=NWT&page=N&page_size=100`). It
  aggregates postings (CakeResume et al.) and returns title/company/location/
  salary/URL/description. We pull the Greater Taipei core (`TPE` + `NWT`).

**Not used**
- **台灣就業通 / TaiwanJobs** (`job.taiwanjobs.gov.tw`) — official job bank, but
  results are loaded through a session-bound ASP.NET AJAX postback; too fragile.
- **104.com.tw — International Talents** (`go.104.com.tw/expats`) — largest
  board, but 104 is a commercial aggregator: **check ToS before scraping**;
  treat as opt-in.
- Academic routes: university HR pages, Ministry of Education, NSTC.

## Compliance re-check cadence

  `DvinciData` extraction and A1's absolute `nextPageUrl` pagination should also
  be re-checked whenever those frontends change.
- Per source: re-read the terms of use / `robots.txt` at least **quarterly**,
  and whenever a scraper is added. Record the outcome in README's table.
- Never store recruiter names, emails, or phone numbers.
- Keep request volume polite (rate limit + retry/backoff already in `common.py`).
