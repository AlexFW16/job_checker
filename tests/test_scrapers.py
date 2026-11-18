from scrapers import companies, eures, tgw
from scrapers.companies import (
    AITScraper,
    AVLLScraper,
    BRScraper,
    DynatraceScraper,
    FabasoftScraper,
    InfineonScraper,
    JKUScraper,
    KEBAScraper,
    LAMResearchScraper,
    PrimetalsScraper,
    RISCRScraper,
    SALScraper,
    SCCHScraper,
    SiemensScraper,
    SynopsysScraper,
    VoestalpineScraper,
)
from scrapers.eures import EuresScraper
from scrapers.tgw import TGWScraper

TGW_HTML = """
<html><body>
<div class="fadeContainer">
  <div class="countryHeader">Austria</div>
  <div class="jobWrapper">
    <a class="jobItem" href="/en/career/jobs/123">
      <div class="jobListPart">Junior Software Developer (m/w/d)</div>
      <div class="jobListPart">Linz</div>
      <div class="jobListPart">Development</div>
      <div class="jobListPart">Entry level</div>
    </a>
  </div>
  <div class="countryHeader">Germany</div>
  <div class="jobWrapper">
    <a class="jobItem" href="/en/career/jobs/456">
      <div class="jobListPart">Senior Developer (m/w/d)</div>
      <div class="jobListPart">Munich</div>
      <div class="jobListPart">Development</div>
      <div class="jobListPart">Experienced</div>
    </a>
  </div>
</div>
</body></html>
"""

SCCH_HTML = """
<html><body>
<div class="job-list">
  <a href="/karriere/detail/software-engineer">Software Engineer (m/w/d)</a>
  <a href="/karriere/detail/research-assistant">Research Assistant</a>
</div>
</body></html>
"""

RISC_FEATURED_HTML = """
<html><body>
<div class="position">
  <a href="/jobs/embedded-developer">Embedded Developer (m/w/d)</a>
</div>
</body></html>
"""

SAL_HTML = """
<html><body>
<article class="joboffer">
  <a href="software-engineer-j123.html">Software Engineer (m/w/d)</a>
  <div class="job_details_second">Vollzeit</div>
  <div class="job_standort">Linz</div>
  <div class="job_location">Hybrid</div>
</article>
</body></html>
"""

AVL_HTML = """
<html><body><table><tbody>
<tr><td>1</td>
  <td><a href="/careers/job/1">Software Engineer</a></td>
  <td>Graz, Austria</td>
  <td>Engineering</td>
</tr>
<tr><td>2</td>
  <td><a href="/careers/job/2">Sales Manager</a></td>
  <td>Hooglede-Gits, Belgium</td>
  <td>Sales</td>
</tr>
</tbody></table></body></html>
"""

ERECRUITER_HTML = (
    '<script>new JobList(a, b, {"Jobs": ['
    '{"Title": "Software Developer (m/w/d)", "Location": "Linz, Österreich", "Id": 1, "ExternalUrl": "", "JobProfile": "R&D"}'
    "]});</script>"
)

SYNOPSYS_RSS = """<?xml version="1.0"?>
<rss><channel>
  <item><title>Software Engineer - Linz</title><link>https://careers.synopsys.com/job/1</link></item>
  <item><title>Designer - Prague</title><link>https://careers.synopsys.com/job/2</link></item>
</channel></rss>"""

VOESTALPINE_JSON = {
    "SearchResult": {
        "SearchResultItems": [
            {
                "MatchedObjectDescriptor": {
                    "PositionTitle": "Data & AI Engineer",
                    "PositionURI": "https://jobs.voestalpine.com/job/1",
                    "PositionLocation": [{"CountryName": "Österreich", "CityName": "Linz"}],
                    "JobCategory": [{"Name": "IT"}],
                    "CareerLevel": [{"Name": "Mitarbeiter:in"}],
                }
            },
            {
                "MatchedObjectDescriptor": {
                    "PositionTitle": "Sales Manager",
                    "PositionURI": "https://jobs.voestalpine.com/job/2",
                    "PositionLocation": [{"CountryName": "Belgien", "CityName": "Hooglede-Gits"}],
                    "JobCategory": [{"Name": "Sales"}],
                    "CareerLevel": [{"Name": "Mitarbeiter:in"}],
                }
            },
        ]
    }
}


class TestTGWScraper:
    def test_parse_jobs(self):
        jobs = TGWScraper()._parse_jobs(TGW_HTML)
        assert len(jobs) == 2
        assert jobs[0].title == "Junior Software Developer (m/w/d)"
        assert jobs[0].location == "Linz"
        assert jobs[0].country == "Austria"
        assert jobs[1].country == "Germany"
        assert jobs[0].source == "tgw"

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(tgw, "fetch_html", lambda *a, **k: TGW_HTML)
        assert len(TGWScraper().fetch_jobs()) == 2

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(tgw, "fetch_html", boom)
        assert TGWScraper().fetch_jobs() == []

    def test_missing_container_returns_empty(self):
        assert TGWScraper()._parse_jobs("<html></html>") == []


class TestSCCHScraper:
    def test_parse_jobs(self):
        jobs = SCCHScraper()._parse_jobs(SCCH_HTML)
        assert len(jobs) == 2
        assert jobs[0].title == "Software Engineer (m/w/d)"
        assert jobs[0].country == "Austria"
        assert jobs[0].url == "https://www.scch.at/karriere/detail/software-engineer"

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: SCCH_HTML)
        assert len(SCCHScraper().fetch_jobs()) == 2


class TestRISCRScraper:
    def test_parse_api_jobs(self):
        data = [{"title": {"rendered": "Backend Developer"}, "link": "https://career.risc-software.at/job/1"}]
        jobs = RISCRScraper()._parse_api_jobs(data)
        assert len(jobs) == 1
        assert jobs[0].title == "Backend Developer"
        assert jobs[0].country == "Austria"

    def test_parse_api_jobs_rejects_non_list(self):
        assert RISCRScraper()._parse_api_jobs({"message": "rest_no_route"}) == []

    def test_parse_featured_jobs(self):
        jobs = RISCRScraper()._parse_featured_jobs(RISC_FEATURED_HTML)
        assert len(jobs) == 1
        assert jobs[0].title == "Embedded Developer (m/w/d)"

    def test_fetch_jobs_uses_api_first(self, monkeypatch):
        api_data = [{"title": {"rendered": "Backend Developer"}, "link": "https://career.risc-software.at/job/1"}]
        monkeypatch.setattr(companies, "fetch_json", lambda *a, **k: api_data)
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: RISC_FEATURED_HTML)
        jobs = RISCRScraper().fetch_jobs()
        assert [j.title for j in jobs] == ["Backend Developer"]

    def test_fetch_jobs_falls_back_to_html(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("api down")

        monkeypatch.setattr(companies, "fetch_json", boom)
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: RISC_FEATURED_HTML)
        jobs = RISCRScraper().fetch_jobs()
        assert [j.title for j in jobs] == ["Embedded Developer (m/w/d)"]


class TestSALScraper:
    def test_parse_listing(self):
        jobs = SALScraper()._parse_listing(SAL_HTML)
        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Software Engineer (m/w/d)"
        assert job.experience_level == "Vollzeit"
        assert "Linz" in job.location
        assert "Hybrid" in job.location
        assert job.url == "https://career.silicon-austria-labs.com/software-engineer-j123.html"

    def test_fetch_pages_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: SAL_HTML)
        jobs = SALScraper().fetch_jobs()
        assert len(jobs) == 1

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(companies, "fetch_html", boom)
        assert SALScraper().fetch_jobs() == []


class TestAVLLScraper:
    def test_parse_page_filters_non_austria(self):
        jobs = AVLLScraper()._parse_page(AVL_HTML)
        assert len(jobs) == 1
        assert jobs[0].title == "Software Engineer"
        assert jobs[0].country == "Austria"
        assert jobs[0].category == "Engineering"

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: AVL_HTML)
        jobs = AVLLScraper().fetch_jobs()
        assert len(jobs) == 1


class TestErecruiterScrapers:
    def test_ait(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: ERECRUITER_HTML)
        jobs = AITScraper().fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0].source == "ait"

    def test_keba(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: ERECRUITER_HTML)
        jobs = KEBAScraper().fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0].source == "keba"

    def test_primetals(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: ERECRUITER_HTML)
        jobs = PrimetalsScraper().fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0].source == "primetals"

    def test_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(companies, "fetch_html", boom)
        assert AITScraper().fetch_jobs() == []


class TestSynopsysScraper:
    def test_parse_rss_filters_austria(self):
        jobs = SynopsysScraper()._parse_rss(SYNOPSYS_RSS)
        assert len(jobs) == 1
        assert jobs[0].title == "Software Engineer - Linz"
        assert jobs[0].country == "Austria"

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: SYNOPSYS_RSS)
        assert len(SynopsysScraper().fetch_jobs()) == 1


class TestVoestalpineScraper:
    def test_parse_results_filters_austria(self):
        jobs = VoestalpineScraper()._parse_results(VOESTALPINE_JSON)
        assert len(jobs) == 1
        assert jobs[0].title == "Data & AI Engineer"
        assert "Linz" in jobs[0].location
        assert jobs[0].country == "Austria"

    def test_first_name_variants(self):
        assert VoestalpineScraper._first_name([{"Name": "IT"}]) == "IT"
        assert VoestalpineScraper._first_name({"Name": "IT"}) == "IT"
        assert VoestalpineScraper._first_name("IT") == "IT"
        assert VoestalpineScraper._first_name(None) == ""

    def test_search_url_encodes_payload(self):
        url = VoestalpineScraper()._search_url()
        assert url.startswith(VoestalpineScraper.SEARCH_URL + "?data=")
        assert "CountItem" in url

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_json", lambda *a, **k: VOESTALPINE_JSON)
        assert len(VoestalpineScraper().fetch_jobs()) == 1


EURES_JSON = {
    "numberRecords": 2,
    "jvs": [
        {
            "title": "Junior Software Developer",
            "id": "abc123",
            "description": "<p>Join our team in Linz. Remote possible.</p>",
            "locationMap": {"AT": ["AT31"]},
            "employer": {"name": "ACME GmbH"},
        },
        {
            "title": "Data Scientist",
            "id": "def456",
            "description": "<p>Based in Munich.</p>",
            "locationMap": {"DE": ["DE21"]},
            "employer": {"name": "Beta AG"},
        },
    ],
}


class TestEuresScraper:
    def test_payload_shape(self):
        payload = EuresScraper()._build_payload("software developer", page=2)
        assert payload["page"] == 2
        assert payload["keywords"] == [
            {"keyword": "software developer", "specificSearchCode": "EVERYWHERE"}
        ]
        assert payload["locationCodes"] == ["at", "de"]
        assert "more_than_5_years" not in payload["requiredExperienceCodes"]

    def test_parse_response(self):
        jobs = EuresScraper()._parse_response(EURES_JSON)
        assert len(jobs) == 2
        linz = jobs[0]
        assert linz.title == "Junior Software Developer"
        assert "Oberösterreich" in linz.location
        assert linz.country == "Austria"
        assert linz.company == "ACME GmbH"
        assert linz.url == "https://europa.eu/eures/portal/jv-se/jv-details/abc123"
        assert "Linz" in linz.description
        assert jobs[1].location == "Munich"
        assert jobs[1].country == "Germany"

    def test_remote_marker_added(self):
        jobs = EuresScraper()._parse_response(EURES_JSON)
        assert "Remote" in jobs[0].location

    def test_remote_teams_and_partial_home_office_are_not_remote(self):
        location, _ = EuresScraper()._resolve_location(
            {"DE": ["DE21"]},
            "Data Scientist",
            "Collaborate with remote teams. One home-office day per week.",
        )
        assert "Remote" not in location

    def test_parse_non_dict_returns_empty(self):
        assert EuresScraper()._parse_response([]) == []
        assert EuresScraper()._parse_response({"jvs": []}) == []

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(eures, "fetch_json_post", lambda *a, **k: EURES_JSON)
        jobs = EuresScraper().fetch_jobs()
        assert len(jobs) == 2

    def test_duplicate_page_does_not_stop_next_page(self, monkeypatch):
        monkeypatch.setattr(eures, "SEARCH_TERMS", ["software", "data"])
        calls = []

        def entry(job_id):
            return {
                "title": "Junior Software Developer",
                "id": job_id,
                "description": "Join our team in Linz.",
                "locationMap": {"AT": ["AT31"]},
                "employer": {"name": "ACME GmbH"},
            }

        shared = [entry(f"shared-{index}") for index in range(50)]

        def fake_fetch(url, payload):
            term = payload["keywords"][0]["keyword"]
            page = payload["page"]
            calls.append((term, page))
            results = shared if page == 1 else [entry(f"{term}-unique")]
            return {"numberRecords": 51, "jvs": results}

        monkeypatch.setattr(eures, "fetch_json_post", fake_fetch)
        jobs = EuresScraper().fetch_jobs()
        assert len(jobs) == 52
        assert {call[1] for call in calls} == {1, 2}
        assert any("software-unique" in job.url for job in jobs)
        assert any("data-unique" in job.url for job in jobs)

    def test_cap_is_shared_fairly_across_terms(self, monkeypatch):
        monkeypatch.setattr(eures, "SEARCH_TERMS", ["software", "data"])
        monkeypatch.setattr(eures, "cap_jobs", lambda jobs: jobs[:2])

        def fake_fetch(url, payload):
            term = payload["keywords"][0]["keyword"]
            results = [
                {
                    "title": f"{term} Engineer {index}",
                    "id": f"{term}-{index}",
                    "description": "Join our team in Linz.",
                    "locationMap": {"AT": ["AT31"]},
                }
                for index in range(2)
            ]
            return {"numberRecords": 2, "jvs": results}

        monkeypatch.setattr(eures, "fetch_json_post", fake_fetch)
        urls = [job.url for job in EuresScraper().fetch_jobs()]
        assert any("software-0" in url for url in urls)
        assert any("data-0" in url for url in urls)

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(eures, "fetch_json_post", boom)
        assert EuresScraper().fetch_jobs() == []


FABASOFT_HTML = """
<html><body>
<ul>
  <li class="list-group-item">
    <a href="/en/career/jobs/software-engineer">
      <h3>Software Engineer (f/m/d)</h3>
      <span>
          Linz
      </span>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/en/karriere/jobs/berlin-role">
      <h3>Software Developer &ndash; Tools (f/m/d)</h3>
      <span>Berlin, Erfurt, Munich</span>
    </a>
  </li>
</ul>
</body></html>
"""


class TestFabasoftScraper:
    def test_parse_jobs(self):
        jobs = FabasoftScraper()._parse_jobs(FABASOFT_HTML)
        assert len(jobs) == 2
        linz = jobs[0]
        assert linz.title == "Software Engineer (f/m/d)"
        assert linz.location == "Linz"
        assert linz.country == "Austria"
        assert linz.url == "https://www.fabasoft.com/en/career/jobs/software-engineer"
        assert jobs[1].country == ""

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: FABASOFT_HTML)
        assert len(FabasoftScraper().fetch_jobs()) == 2

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(companies, "fetch_html", boom)
        assert FabasoftScraper().fetch_jobs() == []


DYNATRACE_JSON = {
    "results": [
        {
            "title": "Software Engineer - Early Career (m/f/x)",
            "uri": "https://www.dynatrace.com/careers/jobs/1/",
            "raw": {
                "country": ["Austria"],
                "office_locations": ["Linz"],
                "flex_option": ["Hybrid"],
                "team": ["Engineering"],
                "seniority": ["Early Careers"],
            },
        },
        {
            "title": "Remote Platform Engineer",
            "uri": "https://www.dynatrace.com/careers/jobs/2/",
            "raw": {
                "country": ["Germany"],
                "office_locations": ["Munich"],
                "flex_option": ["Remote"],
                "team": ["Engineering"],
                "seniority": ["Experienced and Senior"],
            },
        },
        {
            "title": "Onsite Engineer",
            "uri": "https://www.dynatrace.com/careers/jobs/3/",
            "raw": {
                "country": ["United States"],
                "office_locations": ["Boston"],
                "flex_option": ["Hybrid"],
                "team": ["Engineering"],
            },
        },
    ]
}


class TestDynatraceScraper:
    def test_parse_keeps_austria_and_remote_europe(self):
        jobs = DynatraceScraper()._parse_results(DYNATRACE_JSON)
        assert len(jobs) == 2
        linz, remote = jobs
        assert linz.country == "Austria"
        assert linz.location == "Linz"
        assert linz.experience_level == "Early Careers"
        assert remote.country == "Germany"
        assert "Remote" in remote.location

    def test_parse_skips_non_europe_onsite(self):
        jobs = DynatraceScraper()._parse_results(DYNATRACE_JSON)
        assert all("Boston" not in job.location for job in jobs)

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_json_post", lambda *a, **k: DYNATRACE_JSON)
        assert len(DynatraceScraper().fetch_jobs()) == 2

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(companies, "fetch_json_post", boom)
        assert DynatraceScraper().fetch_jobs() == []


ABB_JSON = {
    "total": 3,
    "jobPostings": [
        {
            "title": "Automation Software Engineer (f/m/d)",
            "externalPath": "/job/Eggelsberg-Oberosterreich-Austria/Automation--JR1",
            "locationsText": "Eggelsberg, Oberosterreich, Austria",
        },
        {
            "title": "Process & Toolchain Expert (f/m/d)",
            "externalPath": "/job/Eggelsberg-Oberosterreich-Austria/Process--JR3",
            "locationsText": "2 Locations",
        },
        {
            "title": "Software Engineer",
            "externalPath": "/job/Pune-India/Software--JR2",
            "locationsText": "Pune, Maharashtra, India",
        },
    ],
}


class TestBRScraper:
    def test_parse_keeps_austria_only(self):
        jobs = BRScraper()._parse_results(ABB_JSON)
        assert len(jobs) == 2
        job = jobs[0]
        assert job.country == "Austria"
        assert job.location == "Eggelsberg, Oberosterreich, Austria"
        assert job.url.endswith("/job/Eggelsberg-Oberosterreich-Austria/Automation--JR1")

    def test_parse_keeps_multi_location_via_path(self):
        jobs = BRScraper()._parse_results(ABB_JSON)
        multi = [job for job in jobs if "Toolchain" in job.title]
        assert len(multi) == 1
        assert multi[0].country == "Austria"
        assert multi[0].location == "Eggelsberg, Austria"

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_json_post", lambda *a, **k: ABB_JSON)
        assert len(BRScraper().fetch_jobs()) == 2

    def test_fetch_jobs_paginates(self, monkeypatch):
        postings = [
            {
                "title": f"Software Engineer {index}",
                "externalPath": f"/job/Eggelsberg-Oberosterreich-Austria/Software--JR{index}",
                "locationsText": "Eggelsberg, Austria",
            }
            for index in range(51)
        ]
        calls = []

        def fake_fetch(url, payload, **kwargs):
            calls.append((payload["offset"], kwargs.get("retries")))
            start = payload["offset"]
            return {"total": 51, "jobPostings": postings[start : start + 50]}

        monkeypatch.setattr(companies, "fetch_json_post", fake_fetch)
        assert len(BRScraper().fetch_jobs()) == 51
        assert calls == [(0, 0), (50, 0)]

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(companies, "fetch_json_post", boom)
        assert BRScraper().fetch_jobs() == []


JKU_HTML = """
<html><body>
<div class="jcl-job-teaser-content">
  <div class="jcl-job-teaser-title">
    <a data-avoid-redirect="true" href="/job/administrative-it-assistant-mwd-6015">Administrative &amp; IT Assistant (m/w/d)</a>
  </div>
  <div class="jcl-job-teaser-info">
    <div class="jcl-job-teaser-company"><a href="/organization/powerlink">Powerlink H2 GmbH</a></div>
    <div class="jcl-job-teaser-location">
      <svg><title>location</title></svg> Linz, &Ouml;sterreich
    </div>
  </div>
</div>
</body></html>
"""


class TestJKUScraper:
    def test_parse_jobs(self):
        jobs = JKUScraper()._parse_jobs(JKU_HTML, set())
        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Administrative & IT Assistant (m/w/d)"
        assert job.company == "Powerlink H2 GmbH"
        assert job.location == "Linz, Österreich"
        assert job.country == "Austria"
        assert job.url == "https://jobboerse.jku.at/job/administrative-it-assistant-mwd-6015"

    def test_parse_dedupes_seen(self):
        seen = set()
        assert len(JKUScraper()._parse_jobs(JKU_HTML, seen)) == 1
        assert JKUScraper()._parse_jobs(JKU_HTML, seen) == []

    def test_fetch_jobs_stops_when_no_new(self, monkeypatch):
        monkeypatch.setattr(companies, "fetch_html", lambda *a, **k: JKU_HTML)
        assert len(JKUScraper().fetch_jobs()) == 1

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(companies, "fetch_html", boom)
        assert JKUScraper().fetch_jobs() == []


class TestCompanyHelpers:
    def test_retail_is_not_an_ai_category(self):
        assert companies._guess_category("Retail Manager") == "Other"

    def test_ai_engineer_gets_software_category(self):
        assert companies._guess_category("AI Engineer") == "Development / Software / IT"

    def test_mechanical_engineer_is_not_a_software_category(self):
        assert companies._guess_category("Mechanical Engineer") == "Other"

    def test_traunstein_is_not_traun_austria(self):
        import re

        assert re.search(companies.AUSTRIAN_CITIES, "Traunstein, Germany", re.I) is None
        assert re.search(companies.AUSTRIAN_CITIES, "Traun, Austria", re.I) is not None


class TestNoOpScrapers:
    def test_infineon_returns_empty(self):
        assert InfineonScraper().fetch_jobs() == []

    def test_lam_returns_empty(self):
        assert LAMResearchScraper().fetch_jobs() == []

    def test_siemens_returns_empty(self):
        assert SiemensScraper().fetch_jobs() == []
