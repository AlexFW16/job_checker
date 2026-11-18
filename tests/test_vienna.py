from config_loader import get_default_config
from matching import JobClassifier, matches_location
from scrapers import vienna
from scrapers.vienna import A1Scraper, FrequentisScraper, WienEnergieScraper

A1_PAGE_ONE = {
    "items": [
        {
            "id": "9499",
            "title": "Praktikum IT Audit (w/m/d)",
            "url": "https://jobs.a1.com/de/jobs/job/9499-praktikum-it-audit-wmd",
            "company": "A1 Telekom Austria AG",
            "location": "Wien",
            "type": {
                "category": "Internal Audit &amp; Legal",
                "timeType": "Vollzeit",
                "remoteType": "Teilweise Remote",
            },
        },
        {
            "id": "9500",
            "title": "C++ Backend Developer",
            "url": "https://jobs.a1.com/de/jobs/job/9500-cpp-backend-developer",
            "company": "A1 Group",
            "location": "Linz",
            "type": {"category": "IT", "timeType": "Vollzeit"},
        },
    ],
    "totalItems": 3,
    "maxPages": 2,
    "nextPageUrl": "https://jobs.a1.com/de/wp-json/a1-group/v1/filter-jobs?country=austria&page=2",
}

A1_PAGE_TWO = {
    "items": [
        A1_PAGE_ONE["items"][0],
        {
            "id": "9501",
            "title": "Python Engineer",
            "url": "https://jobs.a1.com/de/jobs/job/9501-python-engineer",
            "company": "A1 Group",
            "location": "Wien",
            "type": {"category": "Software", "timeType": "Vollzeit"},
        },
    ],
    "nextPageUrl": None,
}

WIEN_ENERGIE_HTML = """
<html><head><meta http-equiv="refresh" content="0; url=https://www.wienerstadtwerke.at/jobs"></head>
<body><script type="text/javascript">
var DvinciData = {
  "jobPublications": [
    {
      "id": 28453,
      "position": "Data Engineer (w/m/d)",
      "jobPublicationURL": "https://jobs.wienerstadtwerke.at/de/p/WienEnergie/jobs/28453/data-engineer-wmd",
      "jobOpening": {
        "id": 25909,
        "reference": "2026-1061",
        "location": "Thomas-Klestil-Platz 14",
        "categories": [{"name": "IT Daten & KI"}],
        "targetGroups": [{"name": "Midlevel / mehrjährige Berufserfahrung"}],
        "workingTimes": [{"name": "Vollzeit"}],
        "locations": [{
          "name": "Thomas-KlestilPLATZ_14",
          "country": {"name": "Österreich", "isoA2": "AT"},
          "address": {"zipCode": "1030", "city": "Wien", "country": {"isoA2": "AT"}}
        }],
        "orgUnit": {"name": "Wien Energie"},
        "company": {"name": "Wien Energie"}
      }
    }
  ]
};
</script></body></html>
"""


class TestA1Scraper:
    def test_parse_response(self):
        jobs = A1Scraper()._parse_response(A1_PAGE_ONE)
        assert len(jobs) == 2
        assert jobs[0].title == "Praktikum IT Audit (w/m/d)"
        assert jobs[0].location == "Wien"
        assert jobs[0].country == "Austria"
        assert jobs[0].category == "Internal Audit & Legal"
        assert jobs[0].company == "A1 Telekom Austria AG"
        assert jobs[0].raw["id"] == "9499"

    def test_fetch_jobs_follows_next_page_and_dedupes(self, monkeypatch):
        responses = iter([A1_PAGE_ONE, A1_PAGE_TWO])
        urls = []

        def fake_fetch(url):
            urls.append(url)
            return next(responses)

        monkeypatch.setattr(vienna, "fetch_json", fake_fetch)
        jobs = A1Scraper().fetch_jobs()
        assert len(jobs) == 3
        assert len(urls) == 2
        assert urls[1].endswith("page=2")

    def test_fetch_jobs_keeps_earlier_pages_on_error(self, monkeypatch):
        calls = iter([A1_PAGE_ONE, RuntimeError("next page failed")])

        def fake_fetch(url):
            response = next(calls)
            if isinstance(response, Exception):
                raise response
            return response

        monkeypatch.setattr(vienna, "fetch_json", fake_fetch)
        assert len(A1Scraper().fetch_jobs()) == 2

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(url):
            raise RuntimeError("network down")

        monkeypatch.setattr(vienna, "fetch_json", boom)
        assert A1Scraper().fetch_jobs() == []


def frequentis_card(job_id, title, location, company="FREQUENTIS AG"):
    return f"""
    <li class="list__item">
      <div class="list__item__text__title">
        <a href="/careers/JobDetail/Example/{job_id}">{title}</a>
      </div>
      <div class="list__item__text__subtitle">Software Development | Austria | {location} | {company}</div>
      <div class="list__item__description">Short teaser only.</div>
    </li>
    """


def frequentis_page(cards, next_offset=None):
    next_link = f'<a href="?jobOffset={next_offset}">Next &gt;&gt;</a>' if next_offset else ""
    return f'<ul class="list list--jobs">{"".join(cards)}</ul>{next_link}'


class TestFrequentisScraper:
    def test_parse_cards_including_company(self):
        page = frequentis_page([
            frequentis_card(1234, "Graduate Software Engineer (all genders)", "Vienna"),
            frequentis_card(1235, "Python Backend Developer", "Linz", "CNS-Solutions &amp; Support GmbH"),
        ])
        jobs = FrequentisScraper()._parse_response(page)
        assert len(jobs) == 2
        assert jobs[0].location == "Vienna"
        assert jobs[0].country == "Austria"
        assert jobs[0].category == "Software Development"
        assert jobs[0].url == "https://jobs.frequentis.com/careers/JobDetail/Example/1234"
        assert jobs[0].description == ""
        assert jobs[1].company == "CNS-Solutions & Support GmbH"

    def test_fetch_jobs_follows_next_links(self, monkeypatch):
        pages = iter([
            frequentis_page([frequentis_card(1234, "Graduate Software Engineer", "Vienna")], 20),
            frequentis_page([frequentis_card(1235, "Python Backend Developer", "Vienna")]),
        ])
        urls = []

        def fake_fetch(url):
            urls.append(url)
            return next(pages)

        monkeypatch.setattr(vienna, "fetch_html", fake_fetch)
        jobs = FrequentisScraper().fetch_jobs()
        assert len(jobs) == 2
        assert len(urls) == 2
        assert urls[1].endswith("jobOffset=20")

    def test_parse_rejects_junk_cards(self):
        page = frequentis_page([frequentis_card(1, "Reset filters", "Vienna")])
        assert FrequentisScraper()._parse_response(page) == []

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(url):
            raise RuntimeError("network down")

        monkeypatch.setattr(vienna, "fetch_html", boom)
        assert FrequentisScraper().fetch_jobs() == []


class TestWienEnergieScraper:
    def test_parse_response(self):
        jobs = WienEnergieScraper()._parse_response(WIEN_ENERGIE_HTML)
        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Data Engineer (w/m/d)"
        assert job.location == "Thomas-Klestil-Platz 14, Wien"
        assert job.country == "Austria"
        assert job.category == "IT Daten & KI"
        assert job.company == "Wien Energie"
        assert job.raw == {"id": 28453, "reference": "2026-1061"}

    def test_parsed_job_matches_vienna_and_early_mid(self):
        job = WienEnergieScraper()._parse_response(WIEN_ENERGIE_HTML)[0]
        assert matches_location(job, {"countries": ["Austria"]}) == (True, "vienna_area")
        result = JobClassifier(get_default_config()).classify(job)
        assert result["required_years"] == 3
        assert result["is_relevant"] is True
        assert result["graduate_tier"] == "possible"

    def test_parse_ignores_browser_redirect(self):
        jobs = WienEnergieScraper()._parse_response(WIEN_ENERGIE_HTML)
        assert jobs[0].url.startswith("https://jobs.wienerstadtwerke.at/")

    def test_parse_returns_empty_without_embedded_json(self):
        assert WienEnergieScraper()._parse_response("<html><body>No jobs</body></html>") == []

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(vienna, "fetch_html", lambda url: WIEN_ENERGIE_HTML)
        assert len(WienEnergieScraper().fetch_jobs()) == 1

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(url):
            raise RuntimeError("network down")

        monkeypatch.setattr(vienna, "fetch_html", boom)
        assert WienEnergieScraper().fetch_jobs() == []
