from config_loader import get_default_config
from scrapers.base import Job
from matching import (
    JobClassifier,
    TermMatcher,
    _contains_city,
    analyze_experience,
    detect_entry_signal,
    extract_required_years,
    extract_salary,
    matches_keywords,
    matches_location,
)

BASE_FILTERS = {
    "countries": ["Austria"],
    "remote_worldwide": True,
    "remote_eu": True,
    "allow_eu_nearby": True,
}

CLASSIFIER_CONFIG = {
    "keywords": {
        "junior_level": ["junior", "graduate", "intern", "werkstudent"],
        "software_dev": ["software", "developer", "entwickler"],
        "mathematics": ["data", "mathematik", "optimization"],
    },
    "graduate_filter": {
        "exclude_min_years": 2,
        "seniority_exclude": ["senior", "lead", "head of"],
        "seniority_downgrade": ["manager", "architect"],
    },
}


def make_job(title, location="Linz", country="Austria", category="", experience_level="", description="", url="", source="test"):
    job = Job(
        title=title,
        location=location,
        country=country,
        category=category,
        experience_level=experience_level,
        source=source,
        url=url,
    )
    job.description = description
    return job


class TestExtractRequiredYears:
    def test_numeric_years_of_experience(self):
        assert extract_required_years("We require 5 years of experience")[0] == 5

    def test_minimum_phrasing(self):
        assert extract_required_years("Minimum of 3 years experience required.")[0] == 3

    def test_word_number(self):
        assert extract_required_years("at least two years of professional experience")[0] == 2

    def test_plus_years(self):
        assert extract_required_years("5+ years of relevant experience")[0] == 5

    def test_range_takes_lower_bound(self):
        assert extract_required_years("3-5 years of experience")[0] == 3

    def test_zero_to_n_years(self):
        assert extract_required_years("0-2 years of experience")[0] == 0

    def test_german_numeric(self):
        assert extract_required_years("mindestens 4 Jahre Berufserfahrung")[0] == 4

    def test_german_noun_first(self):
        assert extract_required_years("Berufserfahrung von 3 Jahren")[0] == 3

    def test_vague_mehrjaehrig(self):
        assert extract_required_years("mehrjährige Berufserfahrung")[0] == 3

    def test_vague_many_years(self):
        assert extract_required_years("many years of experience in Python")[0] == 3

    def test_company_growth_is_not_experience(self):
        assert extract_required_years("Over many years we grew into a global team")[0] is None

    def test_german_company_tradition_is_not_experience(self):
        assert extract_required_years("Our company has mehrjährige Tradition")[0] is None

    def test_product_history_is_not_experience(self):
        assert extract_required_years("For several years our products have led the market")[0] is None

    def test_no_requirement(self):
        assert extract_required_years("No prior experience required")[0] is None

    def test_founding_year_is_not_experience(self):
        assert extract_required_years("We have been founded 10 years ago")[0] is None

    def test_company_age_is_not_experience(self):
        assert extract_required_years("The company is 20 years old")[0] is None

    def test_last_n_years_is_not_experience(self):
        assert extract_required_years("Over the last 5 years we grew fast")[0] is None

    def test_tradition_is_not_experience(self):
        assert extract_required_years("40 years of tradition")[0] is None

    def test_study_program_is_not_experience(self):
        assert extract_required_years("10 years university study program")[0] is None

    def test_empty_input(self):
        assert extract_required_years("")[0] is None

    def test_unrealistic_range_ignored(self):
        assert extract_required_years("99 years of experience required")[0] is None


class TestExtractSalary:
    def test_euro_prefix_and_brutto(self):
        text, value = extract_salary("Gehalt: EUR 2.800,00 brutto pro Monat")
        assert value == 2800
        assert "2.800" in text

    def test_euro_sign_prefix(self):
        _, value = extract_salary("Wir bieten €3.500 pro Monat")
        assert value == 3500

    def test_annual_brutto(self):
        _, value = extract_salary("ab 45.000 brutto jährlich")
        assert value == 45000

    def test_comma_grouped_salary(self):
        assert extract_salary("Salary: EUR 45,000 per year")[1] == 45000

    def test_large_comma_grouped_salary(self):
        assert extract_salary("Salary: EUR 150,000 per year")[1] == 150000

    def test_decimal_comma_salary(self):
        assert extract_salary("Salary: EUR 150,50 per hour")[1] == 150.5

    def test_no_salary(self):
        assert extract_salary("We offer a friendly team") == ("", None)

    def test_year_without_context_ignored(self):
        assert extract_salary("Founded in 2015 in Linz") == ("", None)

    def test_empty(self):
        assert extract_salary("") == ("", None)


class TestEntrySignal:
    def test_no_experience_required_english(self):
        assert detect_entry_signal("No prior experience required") is True

    def test_no_experience_required_german(self):
        assert detect_entry_signal("keine Berufserfahrung notwendig") is True

    def test_entry_level(self):
        assert detect_entry_signal("Entry level position") is True

    def test_berufseinsteiger(self):
        assert detect_entry_signal("Berufseinsteiger gesucht") is True

    def test_not_entry(self):
        assert detect_entry_signal("5 years of experience") is False

    def test_empty(self):
        assert detect_entry_signal("") is False


class TestAnalyzeExperience:
    def test_combines_title_and_description(self):
        info = analyze_experience("Software Engineer", "mindestens 3 Jahre Erfahrung")
        assert info["required_years"] == 3


class TestTermMatcher:
    def test_word_boundary_prevents_partial(self):
        matcher = TermMatcher(["lead"])
        assert matcher.any("Team lead wanted") is True
        assert matcher.any("Leader of the pack") is False

    def test_multiword_term(self):
        matcher = TermMatcher(["head of"])
        assert matcher.any("Head of Engineering") is True
        assert matcher.any("Headfirst") is False

    def test_returns_matches(self):
        matcher = TermMatcher(["software", "developer"])
        assert matcher.find("Software Developer") == ["software", "developer"]

    def test_empty_text(self):
        matcher = TermMatcher(["software"])
        assert matcher.find("") == []
        assert matcher.any("") is False


class TestJobClassifier:
    def test_junior_software_is_graduate(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(make_job("Junior Software Developer"))
        assert info["graduate_tier"] == "graduate"
        assert info["is_relevant"] is True
        assert info["is_junior_level"] is True
        assert info["is_software_dev"] is True

    def test_plain_software_is_possible(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(make_job("Software Developer"))
        assert info["graduate_tier"] == "possible"
        assert info["is_relevant"] is True

    def test_senior_title_excluded(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(make_job("Senior Software Developer"))
        assert info["graduate_tier"] == "excluded"
        assert info["is_relevant"] is False
        assert info["excluded_reasons"]

    def test_years_requirement_excluded(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(
            make_job("Software Developer", description="You need 5 years of experience.")
        )
        assert info["graduate_tier"] == "excluded"
        assert info["is_relevant"] is False

    def test_entry_signal_overrides_years(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(
            make_job("Software Engineer", description="Entry level, no experience required.")
        )
        assert info["graduate_tier"] == "graduate"
        assert info["is_relevant"] is True
        assert info["is_junior_level"] is True

    def test_unrelated_domain_not_relevant(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(make_job("Lagerlogistiker"))
        assert info["is_relevant"] is False

    def test_domain_only_from_title_not_description(self):
        # Description boilerplate must not inject a software/IT hit.
        info = JobClassifier(CLASSIFIER_CONFIG).classify(
            make_job("Sales Representative", description="Work closely with our software team.")
        )
        assert info["is_software_dev"] is False
        assert info["is_relevant"] is False

    def test_experience_level_does_not_inject_domain(self):
        # experience_level holds "Entry level"/"Vollzeit"/"Recent Graduates", not domain.
        info = JobClassifier(CLASSIFIER_CONFIG).classify(
            make_job("Control Technician", experience_level="Software Development - Recent Graduates")
        )
        assert info["is_software_dev"] is False
        assert info["is_relevant"] is False

    def test_graduate_beats_possible_in_score(self):
        classifier = JobClassifier(CLASSIFIER_CONFIG)
        graduate = classifier.classify(make_job("Junior Software Developer"))
        possible = classifier.classify(make_job("Software Developer"))
        assert graduate["score"] > possible["score"]

    def test_downgrade_reduces_score(self):
        classifier = JobClassifier(CLASSIFIER_CONFIG)
        plain = classifier.classify(make_job("Junior Software Developer"))
        downgraded = classifier.classify(make_job("Junior Software Architect"))
        assert downgraded["score"] < plain["score"]

    def test_matched_keywords_are_deduplicated(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(make_job("Junior Software Developer"))
        assert len(info["matched_keywords"]) == len(set(info["matched_keywords"]))

    def test_matches_keywords_wrapper(self):
        info = matches_keywords(make_job("Junior Software Developer"), CLASSIFIER_CONFIG)
        assert info["graduate_tier"] == "graduate"

    def test_senior_title_not_overridden_by_description_entry_boilerplate(self):
        # Real bug: "Senior Software Developer" was flipped to graduate because the
        # description mentioned "bachelor" + entry wording. Seniority must win.
        info = JobClassifier(CLASSIFIER_CONFIG).classify(
            make_job(
                "Senior Software Developer SAP",
                experience_level="Experienced Professionals",
                description="Bachelor degree, no prior experience required. Entry level welcome.",
            )
        )
        assert info["graduate_tier"] == "excluded"
        assert info["is_relevant"] is False
        assert info["excluded_reasons"]

    def test_explicit_years_not_overridden_by_description_entry_boilerplate(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(
            make_job(
                "Software Developer",
                description="You bring 5 years of experience. Graduate applications also welcome.",
            )
        )
        assert info["graduate_tier"] == "excluded"

    def test_description_junior_keyword_upgrades_possible(self):
        info = JobClassifier(CLASSIFIER_CONFIG).classify(
            make_job("Software Developer", description="We are looking for a graduate to join us.")
        )
        assert info["graduate_tier"] == "graduate"
        assert info["is_relevant"] is True

    def test_experienced_english_is_excluded(self):
        config = {
            "keywords": {"junior_level": ["junior"], "software_dev": ["software"], "mathematics": []},
            "graduate_filter": {
                "exclude_min_years": 2,
                "seniority_exclude": ["senior", "experienced"],
                "seniority_downgrade": [],
            },
        }
        info = JobClassifier(config).classify(make_job("Experienced Software Engineer"))
        assert info["graduate_tier"] == "excluded"


class TestMatchesLocation:
    def test_linz_area_city(self):
        ok, reason = matches_location(make_job("Dev", location="Hagenberg"), BASE_FILTERS)
        assert ok is True
        assert reason == "linz_area"

    def test_austrian_country(self):
        ok, reason = matches_location(make_job("Dev", location="Graz", country="Austria"), BASE_FILTERS)
        assert ok is True
        assert reason == "austria"

    def test_vienna_area(self):
        ok, reason = matches_location(make_job("Dev", location="Vienna", country="Austria"), BASE_FILTERS)
        assert ok is True
        assert reason == "vienna_area"

    def test_wien_is_vienna_area(self):
        ok, reason = matches_location(make_job("Dev", location="Wien", country="Austria"), BASE_FILTERS)
        assert ok is True
        assert reason == "vienna_area"

    def test_foreign_country_excluded(self):
        ok, _ = matches_location(make_job("Dev", location="Berlin", country="Germany"), BASE_FILTERS)
        assert ok is False

    def test_traunstein_does_not_match_traun(self):
        ok, reason = matches_location(make_job("Dev", location="Traunstein", country="Germany"), BASE_FILTERS)
        assert ok is True
        assert reason == "eu_nearby"

    def test_traun_is_linz_area(self):
        ok, reason = matches_location(make_job("Dev", location="Traun", country="Austria"), BASE_FILTERS)
        assert ok is True
        assert reason == "linz_area"

    def test_remote_worldwide(self):
        ok, reason = matches_location(make_job("Dev", location="Remote (worldwide)", country=""), BASE_FILTERS)
        assert ok is True
        assert reason == "remote_worldwide"

    def test_remote_eu_has_specific_reason_with_both_flags(self):
        ok, reason = matches_location(make_job("Dev", location="Remote EU", country=""), BASE_FILTERS)
        assert ok is True
        assert reason == "remote_eu"

    def test_remote_europe_has_specific_reason(self):
        ok, reason = matches_location(make_job("Dev", location="Remote - Europe", country=""), BASE_FILTERS)
        assert ok is True
        assert reason == "remote_eu"

    def test_remote_eu_from_country(self):
        ok, reason = matches_location(
            make_job("Dev", location="Remote, Germany", country="Germany"), BASE_FILTERS
        )
        assert ok is True
        assert reason == "remote_eu"

    def test_remote_generic(self):
        ok, reason = matches_location(make_job("Dev", location="Remote", country=""), BASE_FILTERS)
        assert ok is True
        assert reason == "remote"

    def test_home_office(self):
        ok, reason = matches_location(make_job("Dev", location="Home Office", country=""), BASE_FILTERS)
        assert ok is True
        assert reason == "remote"

    def test_hybrid_linz_job_keeps_local_reason(self):
        ok, reason = matches_location(
            make_job("Dev", location="Linz, Remote possible", country="Austria"), BASE_FILTERS
        )
        assert ok is True
        assert reason == "linz_area"

    def test_remote_linz_without_country_stays_local(self):
        ok, reason = matches_location(
            make_job("Dev", location="Linz / Remote", country=""), BASE_FILTERS
        )
        assert ok is True
        assert reason == "linz_area"

    def test_remote_disabled_falls_through(self):
        filters = dict(BASE_FILTERS, remote_worldwide=False, remote_eu=False, allow_eu_nearby=False)
        ok, _ = matches_location(make_job("Dev", location="Remote", country=""), filters)
        assert ok is False

    def test_eu_nearby(self):
        ok, reason = matches_location(make_job("Dev", location="Munich", country="Germany"), BASE_FILTERS)
        assert ok is True
        assert reason == "eu_nearby"

    def test_eu_nearby_disabled(self):
        filters = dict(BASE_FILTERS, allow_eu_nearby=False)
        ok, _ = matches_location(make_job("Dev", location="Munich", country="Germany"), filters)
        assert ok is False


class TestContainsCity:
    def test_word_boundary(self):
        assert _contains_city("traun, austria", ["traun"]) is True
        assert _contains_city("traunstein, germany", ["traun"]) is False

    def test_multiword(self):
        assert _contains_city("bad hall, austria", ["bad hall"]) is True


class TestDefaultDomainMatching:
    def test_python_engineer_is_software(self):
        result = JobClassifier(get_default_config()).classify(make_job("Python Engineer"))
        assert result["is_software_dev"] is True
        assert result["is_relevant"] is True

    def test_java_engineer_is_software(self):
        result = JobClassifier(get_default_config()).classify(make_job("Java Engineer"))
        assert result["is_software_dev"] is True
        assert result["is_relevant"] is True

    def test_retail_manager_is_not_software(self):
        result = JobClassifier(get_default_config()).classify(make_job("Retail Manager"))
        assert result["is_relevant"] is False

    def test_staff_backend_engineer_is_excluded(self):
        result = JobClassifier(get_default_config()).classify(make_job("Staff Backend Engineer"))
        assert result["graduate_tier"] == "excluded"
        assert result["is_relevant"] is False


class TestDefaultExperiencePolicy:
    def test_allows_up_to_three_years(self):
        classifier = JobClassifier(get_default_config())
        result = classifier.classify(
            make_job("Software Engineer", description="3 years of experience in Python")
        )
        assert result["required_years"] == 3
        assert result["is_relevant"] is True

    def test_excludes_four_or_more_years(self):
        classifier = JobClassifier(get_default_config())
        result = classifier.classify(
            make_job("Software Engineer", description="4 years of experience in Python")
        )
        assert result["required_years"] == 4
        assert result["graduate_tier"] == "excluded"
