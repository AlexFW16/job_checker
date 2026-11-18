# job_checker

A personal job-hunt assistant. It scrapes public job postings from Linz-area,
Vienna, Austrian, and remote-EU sources, filters them for junior/mid software
and data-science/math roles, ranks them, and publishes the matches to a static
dashboard on GitHub Pages.

- Entry point: `main.py`
- Matching brain: `matching.py` (location, required-years, tiering, relevance)
- Scrapers: one class per company in `scrapers/` (shared helpers in `scrapers/common.py`)
- Config: `config.json` (keywords, seniority rules, location filters, which scrapers run)
- Output: `results.json` and `docs/results.json` (rendered by `docs/index.html`)

A **Taiwan** variant (Taipei area, same matching engine) lives alongside the
Austria pipeline:

- Entry point: `taiwan_main.py`
- Config: `config_taiwan.json` (layered over `config.json` defaults)
- Scrapers: `scrapers/taiwan/` (Talent Taiwan JSON API)
- Output: `results.taiwan.json` and `docs/results.taiwan.json` (rendered by
  `docs/taiwan.html`), history in `history.taiwan.json`

## Commands

```bash
pip install -r requirements-dev.txt     # runtime + test deps
python main.py                          # Austria run; exit 0 if matches, 1 if none
python taiwan_main.py                   # Taiwan run; writes results.taiwan.json (+ docs)
python -m pytest                        # offline test suite (never hits the network)
```

See `AGENTS.md` for architecture and contributor guidance.
See `docs/PLANNING.md` for the roadmap (remote-EU sources, new-job detection,
Taiwan page) and source/legal notes.

## Sources & compliance

This tool is for **personal, low-volume job search**. It only reads publicly
visible job data (title, location, description, salary), stores no personal
data, identifies itself with an honest User-Agent, and links back to the
original posting. Requests use timeouts, bounded job/detail limits, and retry
backoff for transient errors. Source terms and `robots.txt` are reviewed manually;
the crawler does not automatically evaluate robots rules (see `docs/PLANNING.md`).

| Source | Type | Notes |
|---|---|---|
| Company career sites / ATS feeds (TGW, KEBA, AIT, voestalpine, SAL, AVL, RISC, SCCH, Primetals, Synopsys RSS, Fabasoft, Dynatrace, B&R/ABB Workday, GitLab Greenhouse, A1, Frequentis, Wien Energie) | Company | Public postings on the employer's own site or official ATS; lowest risk. |
| JKU Jobbörse (`jobboerse.jku.at`) | University | JKU's public student & alumni job board. |
| EU EURES portal (`europa.eu/eures`) | Public service | EU public employment service; documented search API. Personal use, cite original postings, low volume. |
| Talent Taiwan (`jobs.talent.nat.gov.tw`) | Public service | Official Taiwan government portal for foreign talent; public JSON search API used by the Taiwan page. Aggregates postings from job platforms; links back to originals. |
| AMS "alle jobs" / eJob-Room | Public service | Austrian public employment service. *Not yet used* — its search API is anti-bot protected (per-request signed token); documented as a stretch goal. |
| 台灣就業通 / TaiwanJobs (`job.taiwanjobs.gov.tw`) | Public service | Official job bank, but results load via a session-bound ASP.NET AJAX postback — too fragile; *not used*. |
| ÖBB (`jobs.oebb.at`) | Company | Official CSOD SPA found; its job-search endpoint returned HTTP 401 with the shell-provided anonymous token. *Not used* until a working session/API contract is verified. |

**Removed:** karriere.at. Its terms of use explicitly forbid *"Sämtliche Formen
der automatisierten Auswertung unserer Plattform"* (all forms of automated
extraction), so the scraper was removed. Coverage is being replaced by the
EURES public service.

Aggregators (karriere.at, jobs.at, LinkedIn, Indeed, Xing, 104.com.tw) generally
prohibit automated extraction in their terms; do not add them without an
official API or explicit permission.
