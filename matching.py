import re

from scrapers.base import Job

LINZ_AREA_CITIES = [
    "linz",
    "hagenberg",
    "marchtrenk",
    "wels",
    "steyr",
    "pasching",
    "traun",
    "leonding",
    "ansfelden",
    "eferding",
    "gallneukirchen",
    "enghagen",
    "puchenau",
    "ottensheim",
    "alham",
    "kirchschlag",
    "walding",
    "altheim",
    "neukirchen bei lambach",
    "lambach",
    "bad hall",
    "kremsmünster",
    "sattledt",
    "stadt-paura",
    "gunskirchen",
    "braunau",
    "ried im innkreis",
    "vöcklabruck",
    "gmunden",
    "freistadt",
    "rohrbach",
    "kirchdorf",
    "oberoesterreich",
    "oberösterreich",
]

EU_NEARBY_CITIES = [
    "munich",
    "münchen",
    "passau",
    "salzburg",
    "pocking",
    "burghausen",
    "freilassing",
    "altötting",
    "traunstein",
    "neuburg",
    "ingolstadt",
    "regensburg",
    "nürnberg",
    "nuremberg",
    "prag",
    "prague",
    "bratislava",
    "budapest",
    "ljubljana",
    "zürich",
    "zurich",
    "stuttgart",
]

AUSTRIAN_CITIES = [
    "austria",
    "österreich",
    "oesterreich",
    "wien",
    "vienna",
    "linz",
    "graz",
    "villach",
    "salzburg",
    "klagenfurt",
    "innsbruck",
    "steyr",
    "hagenberg",
    "marchtrenk",
    "wels",
    "leonding",
    "traun",
    "pasching",
    "ansfelden",
    "oberösterreich",
    "oberoesterreich",
    "niederösterreich",
    "steiermark",
    "kärnten",
    "kaernten",
    "tirol",
    "vorarlberg",
    "burgenland",
    "vöcklabruck",
    "voecklabruck",
    "brunn am gebirge",
    "mödling",
    "wiener neustadt",
]

VIENNA_CITIES = [
    "wien",
    "vienna",
]

EUROPEAN_COUNTRIES = {
    "Austria",
    "Germany",
    "Switzerland",
    "Czechia",
    "Slovakia",
    "Hungary",
    "Slovenia",
    "Italy",
    "France",
    "Netherlands",
    "Belgium",
    "Poland",
    "Spain",
    "Portugal",
    "Sweden",
    "Denmark",
    "Finland",
    "Ireland",
    "Romania",
    "Bulgaria",
    "Croatia",
    "United Kingdom",
}

_EUROPEAN_COUNTRY_NAMES = {country.lower() for country in EUROPEAN_COUNTRIES}

TAIPEI_AREA_CITIES = [
    "taipei",
    "taipei city",
    "new taipei",
    "new taipei city",
    "keelung",
    "taoyuan",
    "臺北",
    "台北",
    "臺北市",
    "台北市",
    "新北",
    "新北市",
    "基隆",
    "桃園",
    "桃园",
]

TAIWAN_CITIES = [
    "taiwan",
    "taipei",
    "new taipei",
    "keelung",
    "taoyuan",
    "hsinchu",
    "taichung",
    "tainan",
    "kaohsiung",
    "changhua",
    "chiayi",
    "yunlin",
    "miaoli",
    "nantou",
    "pingtung",
    "yilan",
    "hualien",
    "taitung",
    "penghu",
    "臺灣",
    "台灣",
    "台湾",
    "臺北",
    "台北",
    "新北",
    "基隆",
    "桃園",
    "桃园",
    "新竹",
    "臺中",
    "台中",
    "臺南",
    "台南",
    "高雄",
    "彰化",
    "嘉義",
    "嘉义",
    "雲林",
    "云林",
    "苗栗",
    "南投",
    "屏東",
    "屏东",
    "宜蘭",
    "宜兰",
    "花蓮",
    "花莲",
    "臺東",
    "台東",
    "台东",
    "澎湖",
]

_BOUNDARY_LEFT = r"(?<![0-9a-zA-ZäöüÄÖÜß])"
_BOUNDARY_RIGHT = r"(?![0-9a-zA-ZäöüÄÖÜß])"

_WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "ein": 1,
    "eine": 1,
    "einen": 1,
    "einer": 1,
    "einem": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "fuenf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwölf": 12,
    "zwoelf": 12,
}

_WORD_NUMBER_ALT = "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True))

_EXPERIENCE_NOUN = r"(?:experience|berufserfahrung|erfahrung|praxiserfahrung|branchenerfahrung)"

_STRICT_YEAR_PATTERNS = [
    re.compile(
        r"(?:at\s+least|minimum(?:\s+of)?|min\.?|mindestens|mind\.?)\s*"
        r"(?P<num>\d{1,2})\s*\+?\s*(?:years?|jahre?n?)",
        re.I,
    ),
    re.compile(
        r"(?P<num>\d{1,2})\s*\+?\s*(?:years?|jahre?n?)\s*[^.\n]{0,30}?" + _EXPERIENCE_NOUN,
        re.I,
    ),
    re.compile(
        _EXPERIENCE_NOUN + r"[^.\n]{0,30}?(?P<num>\d{1,2})\s*\+?\s*(?:years?|jahre?n?)",
        re.I,
    ),
    re.compile(
        r"(?:at\s+least|minimum(?:\s+of)?|min\.?|mindestens|mind\.?)\s*"
        r"(?P<word>" + _WORD_NUMBER_ALT + r")\s*(?:years?|jahre?n?)",
        re.I,
    ),
    re.compile(
        r"(?P<word>" + _WORD_NUMBER_ALT + r")\s*(?:years?|jahre?n?)\s*[^.\n]{0,30}?"
        + _EXPERIENCE_NOUN,
        re.I,
    ),
    re.compile(
        r"(?P<num>\d{1,2})\s*\+?\s*(?:years?|jahre?n?)\s+(?:of\s+)?(?:relevant\s+|practical\s+|"
        r"professional\s+|industry\s+|hands-?on\s+|developing|designing|building|creating|"
        r"working|programming|coding|implementing|entwicklungs?|berufs?\w*)\b",
        re.I,
    ),
]

_RANGE_YEAR_PATTERN = re.compile(
    r"(?P<lo>\d{1,2})\s*(?:-|–|—|to|bis)\s*(?P<hi>\d{1,2})\s*\+?\s*(?:years?|jahre?n?)",
    re.I,
)

_VAGUE_YEARS_PATTERNS = [
    re.compile(r"mehrj(?:ä|ae)hrige", re.I),
    re.compile(r"langj(?:ä|ae)hrige", re.I),
    re.compile(r"(?:many|zahlreiche|zahlreichen|mehrere|einige|couple\s+of|few|several)\s+(?:jahre?n?|years?)", re.I),
    re.compile(r"(?:mehrere|einige|several|multiple|many)\s+jahre?\s+" + _EXPERIENCE_NOUN, re.I),
]

_ENTRY_PATTERNS = [
    re.compile(r"keine\s+(?:berufs)?erfahrung", re.I),
    re.compile(r"no\s+(?:prior\s+|professional\s+|work\s+)?experience\s+(?:required|necessary|needed)", re.I),
    re.compile(r"erste\s+(?:berufs)?erfahrung", re.I),
    re.compile(r"first\s+(?:professional\s+)?experience", re.I),
    re.compile(r"(?:0|null)\s*(?:-|–|bis)\s*\d{1,2}\s*(?:jahre?n?|years?)", re.I),
    re.compile(r"(?:entry[\s-]?level|berufseinstieg|berufseinsteiger|career\s+starter)", re.I),
]

_PRE_YEAR_EXCLUSIONS = re.compile(
    r"(?:seit|vor|über|ueber|in\s+den\s+letzten|within\s+the\s+last|in\s+the\s+last|"
    r"during\s+the\s+last|over\s+the\s+(?:last|past)|last|past|"
    r"seit\s+mehr\s+als|seit\s+über|gegr(?:ü|ue)ndet|founded|tradition|"
    r"besteht\s+seit|am\s+markt|geschichte|history)\s*$",
    re.I,
)

_POST_YEAR_EXCLUSIONS = re.compile(
    r"^\s*(?:alt|old|tradition|gesch(?:ä|ae)ft|business|kalender|calendar|schul|"
    r"lebens|ausbildungs|college|university|study|program|programme|studium)",
    re.I,
)

_SENIORITY_EXCLUDE_DEFAULT = [
    "senior",
    "sr",
    "sr.",
    "lead",
    "teamlead",
    "team lead",
    "team-lead",
    "tech lead",
    "head of",
    "principal",
    "staff engineer",
    "chief",
    "director",
    "vice president",
    "vp",
    "leitung",
    "leiter",
    "leiterin",
    "leitend",
    "leitende",
    "leitender",
    "gruppenleiter",
    "gruppenleiterin",
    "abteilungsleiter",
    "abteilungsleiterin",
    "führungskraft",
    "fuehrungskraft",
    "geschäftsführer",
    "geschaeftsfuehrer",
    "erfahrener",
    "erfahrene",
    "erfahrener",
    "erfahrenen",
    "erfahren",
    "erfahrene:r",
    "experienced",
    "profi",
    "expert",
    "experte",
    "expertin",
    "spezialist",
    "spezialistin",
    "teamleiter",
    "teamleiterin",
]

_SENIORITY_DOWNGRADE_DEFAULT = [
    "manager",
    "architekt",
    "architect",
    "consultant",
    "berater",
]

MAX_PLAUSIBLE_REQUIRED_YEARS = 25


def _term_pattern(term: str) -> re.Pattern:
    escaped = re.escape(term.strip()).replace(r"\ ", r"\s+")
    return re.compile(_BOUNDARY_LEFT + escaped + _BOUNDARY_RIGHT, re.I)


_CITY_PATTERN_CACHE: dict[tuple[str, ...], list[re.Pattern]] = {}


def _contains_city(text: str, cities: list[str]) -> bool:
    """Word-boundary city match so "traun" no longer matches "Traunstein"."""
    key = tuple(cities)
    patterns = _CITY_PATTERN_CACHE.get(key)
    if patterns is None:
        patterns = [_term_pattern(city) for city in cities]
        _CITY_PATTERN_CACHE[key] = patterns
    return any(pattern.search(text) for pattern in patterns)


class TermMatcher:
    def __init__(self, terms: list[str]):
        self.pairs = [(t, _term_pattern(t)) for t in terms if t and t.strip()]

    def find(self, text: str) -> list[str]:
        if not text:
            return []
        return [term for term, pattern in self.pairs if pattern.search(text)]

    def any(self, text: str) -> bool:
        if not text:
            return False
        return any(pattern.search(text) for _, pattern in self.pairs)


def _guard_pre_context(text: str, start: int) -> bool:
    window = text[max(0, start - 40) : start]
    return bool(_PRE_YEAR_EXCLUSIONS.search(window))


def _guard_post_context(text: str, end: int) -> bool:
    window = text[end : end + 30]
    return bool(_POST_YEAR_EXCLUSIONS.search(window))


def _plausible_years(value: int) -> bool:
    return 0 <= value <= MAX_PLAUSIBLE_REQUIRED_YEARS


def extract_required_years(text: str) -> tuple[int | None, list[str]]:
    if not text:
        return None, []
    text = re.sub(
        r"\b(" + _WORD_NUMBER_ALT + r")\s*\(\s*\d{1,2}\s*\)",
        r"\1",
        text,
        flags=re.I,
    )
    notes: list[str] = []
    candidates: list[int] = []

    for pattern in _STRICT_YEAR_PATTERNS:
        for m in pattern.finditer(text):
            num = m.groupdict().get("num")
            word = m.groupdict().get("word")
            if num is not None:
                value = int(num)
            elif word is not None:
                value = _WORD_NUMBERS.get(word.lower())
            else:
                continue
            if value is None or not _plausible_years(value):
                continue
            if _guard_pre_context(text, m.start()) or _guard_post_context(text, m.end()):
                continue
            candidates.append(value)
            notes.append(f"requires ~{value} years ({m.group(0).strip()[:60]})")

    for m in _RANGE_YEAR_PATTERN.finditer(text):
        lo = int(m.group("lo"))
        if not _plausible_years(lo):
            continue
        if _guard_pre_context(text, m.start()) or _guard_post_context(text, m.end()):
            continue
        context = text[max(0, m.start() - 40) : m.end() + 40]
        if re.search(_EXPERIENCE_NOUN, context):
            candidates.append(lo)
            notes.append(f"requires {m.group(0).strip()} years")

    for pattern in _VAGUE_YEARS_PATTERNS:
        for m in pattern.finditer(text):
            if _guard_pre_context(text, m.start()) or _guard_post_context(text, m.end()):
                continue
            context = text[max(0, m.start() - 40) : m.end() + 40]
            if not re.search(_EXPERIENCE_NOUN, context, re.I):
                continue
            value = 5 if re.search(r"langj", m.group(0), re.I) else 3
            candidates.append(value)
            notes.append(f"vague experience requirement ({m.group(0).strip()[:40]}) -> ~{value} years")

    if not candidates:
        return None, notes
    return min(candidates), notes


def detect_entry_signal(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in _ENTRY_PATTERNS)


_SALARY_CONTEXT = re.compile(
    r"€|\beur\b|euro|brutto|netto|gehalt|einkommen|salary|entgelt|verg(?:ü|ue)tung|"
    r"jahresbrutto|monatsbrutto|mindestgehalt|lohn",
    re.I,
)

_SALARY_AMOUNT = re.compile(
    r"(?:\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?"
    r"|\d+,\d{1,2}|\d{3,7})(?![\d.,])"
)


def _parse_euro_amount(raw: str) -> float | None:
    raw = raw.replace(" ", "").replace("\u00a0", "")
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?", raw):
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            return None
    if "," in raw:
        int_part, _, dec = raw.partition(",")
        if not dec.isdigit():
            return None
        try:
            return float(f"{int_part.replace('.', '')}.{dec}")
        except ValueError:
            return None
    if "." in raw:
        parts = raw.split(".")
        if len(parts[-1]) == 3:
            try:
                return float("".join(parts))
            except ValueError:
                return None
    try:
        return float(raw)
    except ValueError:
        return None


def extract_salary(text: str) -> tuple[str, int | float | None]:
    """Pull the first plausible EUR amount near a salary marker.

    Returns the surrounding snippet and the numeric value (EUR). Kept
    deliberately conservative: monthly/annual framing is left in the snippet
    for the reader rather than guessed.
    """
    if not text:
        return "", None
    for match in _SALARY_AMOUNT.finditer(text):
        window = text[max(0, match.start() - 25) : match.end() + 25]
        if not _SALARY_CONTEXT.search(window):
            continue
        value = _parse_euro_amount(match.group(0))
        if value is None or value < 100 or value > 1_000_000:
            continue
        snippet = re.sub(r"\s+", " ", text[max(0, match.start() - 30) : match.end() + 15]).strip()
        return snippet, int(value) if value == int(value) else value
    return "", None


def analyze_experience(title: str, description: str, experience_level: str = "") -> dict:
    full_text = " ".join(part for part in (title, experience_level, description) if part)
    required_years, notes = extract_required_years(full_text)
    entry = detect_entry_signal(full_text)
    return {
        "required_years": required_years,
        "entry_signal": entry,
        "notes": notes,
    }


class JobClassifier:
    def __init__(self, config: dict):
        keywords = config.get("keywords", {})
        graduate = config.get("graduate_filter", {})

        self.junior = TermMatcher(keywords.get("junior_level", []))
        self.software = TermMatcher(keywords.get("software_dev", []))
        self.mathematics = TermMatcher(keywords.get("mathematics", []))

        self.exclude_min_years = int(graduate.get("exclude_min_years", 4))
        self.seniority_exclude = TermMatcher(
            graduate.get("seniority_exclude", _SENIORITY_EXCLUDE_DEFAULT)
        )
        self.seniority_downgrade = TermMatcher(
            graduate.get("seniority_downgrade", _SENIORITY_DOWNGRADE_DEFAULT)
        )

    def classify(self, job: Job) -> dict:
        description = getattr(job, "description", "") or ""
        title_text = " ".join(
            part for part in (job.title, job.category, job.experience_level) if part
        )
        # Domain is judged from title/category only: descriptions contain cross-job
        # boilerplate (apply links, related jobs) and experience_level holds values
        # like "Entry level" / "Vollzeit" / "Recent Graduates", none of which are
        # domain signals. Descriptions still drive experience/entry analysis.
        domain_text = " ".join(part for part in (job.title, job.category) if part)

        software_matches = self.software.find(domain_text)
        math_matches = self.mathematics.find(domain_text)

        title_junior_matches = self.junior.find(title_text)
        description_junior_matches = self.junior.find(description)
        junior_matches = list(
            dict.fromkeys(title_junior_matches + description_junior_matches)
        )
        senior_title_matches = self.seniority_exclude.find(job.title)
        downgrade_matches = self.seniority_downgrade.find(job.title)

        experience = analyze_experience(job.title, description, job.experience_level)
        required_years = experience["required_years"]

        strict_years = required_years is not None and required_years >= self.exclude_min_years
        seniority_excluded = bool(senior_title_matches) or strict_years

        # Seniority and explicit-years exclusions are authoritative: generic
        # description boilerplate ("bachelor", "no experience required") must not
        # flip an explicitly senior role back to the graduate tier.
        if seniority_excluded:
            tier = "excluded"
        elif junior_matches or experience["entry_signal"]:
            tier = "graduate"
        else:
            tier = "possible"

        domain_hit = bool(software_matches or math_matches)

        matched_keywords = list(
            dict.fromkeys(
                software_matches + math_matches + junior_matches + senior_title_matches
            )
        )

        score = len(software_matches) + len(math_matches)
        if tier == "graduate":
            score += 3
        if tier == "possible":
            score += 1
        if downgrade_matches and tier == "graduate":
            score -= 1

        return {
            "is_junior_level": bool(junior_matches or experience["entry_signal"]),
            "is_software_dev": bool(software_matches),
            "is_math_related": bool(math_matches),
            "matched_keywords": matched_keywords,
            "score": score,
            "is_relevant": domain_hit and tier != "excluded",
            "graduate_tier": tier,
            "required_years": required_years,
            "experience_notes": experience["notes"],
            "excluded_reasons": (
                (["seniority: " + ", ".join(senior_title_matches)] if senior_title_matches else [])
                + (["requires >= " + str(self.exclude_min_years) + " years"] if strict_years else [])
            ),
        }


def matches_keywords(job: Job, config: dict) -> dict:
    return JobClassifier(config).classify(job)


def matches_location(job: Job, filters: dict) -> tuple[bool, str]:
    """Region-aware location match.

    ``filters["region"]`` selects the city whitelists; it defaults to
    ``"austria"`` so existing configs keep working unchanged.
    """
    if filters.get("region", "austria") == "taiwan":
        return matches_location_taiwan(job, filters)
    return matches_location_austria(job, filters)


def matches_location_austria(job: Job, filters: dict) -> tuple[bool, str]:
    location_text = f"{job.location} {job.country} {job.title}".lower()

    allow_remote_worldwide = filters.get("remote_worldwide", False)
    allow_remote_eu = filters.get("remote_eu", False)
    allow_eu_nearby = filters.get("allow_eu_nearby", True)
    allowed_countries = [c.lower() for c in filters.get("countries", [])]

    is_remote = bool(re.search(r"\bremote\b|\bhome[\s-]?office\b", location_text))
    country = (job.country or "").lower()

    # A local hybrid role should keep its local reason/ranking instead of being
    # swallowed by a generic "remote possible" note in its description.
    if country in allowed_countries or not country:
        if _contains_city(location_text, LINZ_AREA_CITIES):
            return True, "linz_area"
        if _contains_city(location_text, VIENNA_CITIES):
            return True, "vienna_area"

    if is_remote:
        if allow_remote_worldwide and re.search(r"\b(worldwide|global|anywhere)\b", location_text):
            return True, "remote_worldwide"
        if allow_remote_eu and (
            re.search(r"\b(eu|europe|european|eea|emea)\b", location_text)
            or country in _EUROPEAN_COUNTRY_NAMES
        ):
            return True, "remote_eu"
        if allow_remote_worldwide:
            return True, "remote"
        if allow_remote_eu:
            return True, "remote_eu"

    if country in allowed_countries:
        if _contains_city(location_text, LINZ_AREA_CITIES):
            return True, "linz_area"
        if _contains_city(location_text, VIENNA_CITIES):
            return True, "vienna_area"
        return True, "austria"

    if _contains_city(location_text, LINZ_AREA_CITIES):
        return True, "linz_area"

    if _contains_city(location_text, VIENNA_CITIES):
        return True, "vienna_area"

    if _contains_city(location_text, AUSTRIAN_CITIES):
        return True, "austria"

    if allow_eu_nearby and _contains_city(location_text, EU_NEARBY_CITIES):
        return True, "eu_nearby"

    return False, ""


def matches_location_taiwan(job: Job, filters: dict) -> tuple[bool, str]:
    location_text = f"{job.location} {job.country} {job.title}".lower()

    allow_remote_worldwide = filters.get("remote_worldwide", False)
    allowed_countries = [c.lower() for c in filters.get("countries", [])]

    is_remote = bool(re.search(r"\bremote\b|\bhome[\s-]?office\b", location_text))
    if is_remote and allow_remote_worldwide:
        if re.search(r"\b(worldwide|global|anywhere)\b", location_text):
            return True, "remote_worldwide"
        return True, "remote"

    country = (job.country or "").lower()
    if country == "taiwan" or country in allowed_countries:
        if _contains_city(location_text, TAIPEI_AREA_CITIES):
            return True, "taipei_area"
        return True, "taiwan"

    if _contains_city(location_text, TAIPEI_AREA_CITIES):
        return True, "taipei_area"

    if _contains_city(location_text, TAIWAN_CITIES):
        return True, "taiwan"

    return False, ""
