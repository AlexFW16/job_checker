import copy
import json
from pathlib import Path

CONFIG_FILE = "config.json"
TAIWAN_CONFIG_FILE = "config_taiwan.json"

DEFAULT_CONFIG = {
    "keywords": {
        "junior_level": [
            "junior",
            "graduate",
            "entry level",
            "entry-level",
            "recent graduate",
            "recent graduates",
            "career starter",
            "young professional",
            "trainee",
            "apprentice",
            "lehrling",
            "lehre",
            "intern",
            "internship",
            "co-op",
            "co op",
            "student",
            "students",
            "student:in",
            "studenten",
            "studierende",
            "studierenden",
            "studentische",
            "studentischen",
            "studentischer",
            "stud",
            "werkstudent",
            "werkstudenten",
            "werkstudentin",
            "working student",
            "praktikum",
            "praktikant",
            "praktikanten",
            "praktikantin",
            "ferialpraktikant",
            "ferialpraktikum",
            "sommerpraktikum",
            "thesis",
            "bachelor thesis",
            "master thesis",
            "diplomarbeit",
            "bachelorarbeit",
            "masterarbeit",
            "bachelor",
            "bachelorniveau",
            "bakkalauraat",
            "diplomand",
            "diplomandin",
            "dissertation",
            "phd",
            "doktorat",
            "phd student",
            "berufseinsteiger",
            "berufseinsteigerin",
            "berufseinstieg",
            "absolvent",
            "absolventen",
            "absolventin",
            "hochschulabsolvent",
            "fh-absolvent",
            "htl-absolvent",
            "einsteiger",
            "quereinsteiger"
        ],
        "software_dev": [
            "software",
            "softwareentwickler",
            "softwareentwicklerin",
            "entwickler",
            "entwicklerin",
            "entwicklung",
            "entwicklungen",
            "programmierer",
            "programmiererin",
            "programmier",
            "programming",
            "programmer",
            "applikationsentwickler",
            "application developer",
            "developer",
            "python",
            "java",
            "javascript",
            "typescript",
            "golang",
            "kotlin",
            "swift",
            "rust",
            "php",
            "ruby",
            "scala",
            "c++",
            "c#",
            ".net",
            "full stack",
            "fullstack",
            "frontend",
            "front end",
            "front-end",
            "backend",
            "back end",
            "back-end",
            "web developer",
            "webentwickler",
            "web application",
            "webapplikation",
            "devops",
            "dev ops",
            "sre",
            "site reliability",
            "embedded",
            "firmware",
            "fpga",
            "computer",
            "informatik",
            "informationstechnik",
            "edv",
            "info technik",
            "it",
            "ai",
            "k\u00fcnstliche intelligenz",
            "kuenstliche intelligenz",
            "artificial intelligence",
            "machine learning",
            "maschinelles lernen",
            "ml",
            "data science",
            "data engineer",
            "data scientist",
            "robotics",
            "robotik",
            "automation",
            "automatisierung",
            "computer vision",
            "nlp",
            "natural language processing",
            "sap",
            "abap",
            "software engineer",
            "software engineering",
            "softwarearchitekt",
            "software architect",
            "systems engineer",
            "system engineer",
            "system administrator",
            "sysadmin",
            "it support",
            "it-techniker",
            "it security",
            "cybersecurity",
            "cyber security",
            "developer experience"
        ],
        "mathematics": [
            "mathematik",
            "mathematics",
            "mathematician",
            "mathematiker",
            "statistik",
            "statistics",
            "statistician",
            "statistiker",
            "stochastik",
            "stochastic",
            "numerik",
            "numerical",
            "optimierung",
            "optimization",
            "operations research",
            "data analysis",
            "datenanalyse",
            "data analyst",
            "datenanalyst",
            "analytics",
            "data analytics",
            "quantitativ",
            "quantitative",
            "algorithm",
            "algorithms",
            "algorithmen",
            "algorithmic",
            "algorithmus",
            "algorithmische",
            "machine learning",
            "modeling",
            "modelling",
            "simulation",
            "discrete",
            "combinatorial",
            "combinatorik",
            "algebra",
            "symbolic",
            "constraint",
            "constraints",
            "linear programming",
            "integer programming",
            "graph theory",
            "graphentheorie",
            "probability",
            "probabilistic",
            "scientific computing",
            "computational",
            "mathematical",
            "mathematische"
        ]
    },
    "graduate_filter": {
        "exclude_min_years": 4,
        "seniority_exclude": [
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
            "staff",
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
            "leitenden",
            "gruppenleiter",
            "gruppenleiterin",
            "abteilungsleiter",
            "abteilungsleiterin",
            "teamleiter",
            "teamleiterin",
            "bereichsleitung",
            "bereichsleiter",
            "bereichsleiterin",
            "f\u00fchrungskraft",
            "fuehrungskraft",
            "gesch\u00e4ftsf\u00fchrer",
            "geschaeftsfuehrer",
            "erfahrene",
            "erfahrenen",
            "erfahrener",
            "erfahren",
            "erfahrene:r",
            "experienced",
            "expert",
            "experte",
            "expertin",
            "profi"
        ],
        "seniority_downgrade": [
            "manager",
            "architekt",
            "architect",
            "consultant",
            "berater",
            "beraterin"
        ]
    },
    "filters": {
        "countries": [
            "Austria"
        ],
        "remote_worldwide": True,
        "remote_eu": True,
        "allow_eu_nearby": True,
        "fetch_details": True,
        "max_detail_fetches": 300,
        "rank_weights": {
            "linz_area": 5,
            "vienna_area": 4,
            "remote_eu": 3,
            "austria": 2,
            "remote": 2,
            "remote_worldwide": 1,
            "eu_nearby": 1
        }
    },
    "scrapers": [
        "tgw",
        "scch",
        "risc",
        "sal",
        "ait",
        "avl",
        "keba",
        "infineon",
        "primetals",
        "lam",
        "siemens",
        "synopsys",
        "voestalpine",
        "eures",
        "fabasoft",
        "dynatrace",
        "br",
        "jku",
        "gitlab",
        "a1",
        "frequentis",
        "wien_energie"
    ]
}


# Region-specific overrides layered on top of DEFAULT_CONFIG. Kept identical to
# the committed config_taiwan.json by tests/test_config_loader.py.
DEFAULT_TAIWAN_CONFIG = {
    "region": "taiwan",
    "filters": {
        "region": "taiwan",
        "countries": ["Taiwan"],
        "remote_worldwide": False,
        "remote_eu": False,
        "allow_eu_nearby": False,
        "fetch_details": False,
        "max_detail_fetches": 0,
        "rank_weights": {
            "taipei_area": 5,
            "taiwan": 2,
            "remote": 2,
            "remote_worldwide": 1
        }
    },
    "scrapers": ["talent_taiwan"],
    "keywords_extra": {
        "junior_level": [
            "實習",
            "实习生",
            "助理",
            "工讀",
            "工读",
            "應屆畢業",
            "应届毕业",
            "儲備幹部",
            "储备干部",
            "新卒"
        ],
        "software_dev": [
            "軟體",
            "軟件",
            "系統工程師",
            "系统工程师",
            "軟體測試",
            "软件测试",
            "程式",
            "程式設計",
            "軟體開發",
            "軟件開發",
            "程式開發",
            "系統開發",
            "後端開發",
            "前端開發",
            "開發工程師",
            "後端",
            "后端",
            "前端",
            "全端",
            "韌體",
            "韧体",
            "嵌入式",
            "資訊",
            "资讯",
            "資安",
            "资安",
            "網管",
            "网管",
            "維運",
            "运维",
            "資料庫",
            "数据库",
            "android",
            "ios",
            "mobile developer",
            "qa engineer",
            "test engineer",
            "data engineer",
            "security engineer",
            "network engineer",
            "net developer",
            ".net",
            "backend engineer",
            "frontend engineer",
            "full stack engineer",
            "machine learning engineer",
            "ai engineer",
            "devops engineer"
        ],
        "mathematics": [
            "數學",
            "数学",
            "統計",
            "统计",
            "機率",
            "机率",
            "機率工程師",
            "演算法",
            "算法",
            "資料分析",
            "数据分析",
            "數據分析",
            "数据科学",
            "資料科學",
            "數量",
            "quant",
            "quantitative"
        ]
    },
    "seniority_exclude_extra": [
        "資深",
        "资深",
        "高級",
        "高级",
        "主管",
        "主任",
        "總監",
        "总监",
        "負責人",
        "负责人",
        "組長",
        "组长"
    ],
    "seniority_downgrade_extra": [
        "經理",
        "经理",
        "顧問",
        "顾问"
    ]
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _apply_taiwan_overrides(override: dict) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)

    config["region"] = override.get("region", "taiwan")
    config["filters"] = _deep_merge(config.get("filters", {}), override.get("filters", {}))
    config["filters"]["region"] = config["region"]

    if "scrapers" in override:
        config["scrapers"] = list(override["scrapers"])

    for group, terms in override.get("keywords_extra", {}).items():
        existing = config.setdefault("keywords", {}).setdefault(group, [])
        for term in terms:
            if term not in existing:
                existing.append(term)

    graduate = config.setdefault("graduate_filter", {})
    for extra_key, target_key in (
        ("seniority_exclude_extra", "seniority_exclude"),
        ("seniority_downgrade_extra", "seniority_downgrade"),
    ):
        target = graduate.setdefault(target_key, [])
        for term in override.get(extra_key, []):
            if term not in target:
                target.append(term)

    return config


def load_config() -> dict:
    path = Path(CONFIG_FILE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return copy.deepcopy(DEFAULT_CONFIG)


def load_taiwan_config() -> dict:
    """Load the Taiwan region config: DEFAULT_CONFIG + committed overrides."""
    path = Path(TAIWAN_CONFIG_FILE)
    if path.exists():
        override = json.loads(path.read_text(encoding="utf-8"))
    else:
        override = copy.deepcopy(DEFAULT_TAIWAN_CONFIG)
    return _apply_taiwan_overrides(override)


def save_config(config: dict) -> None:
    Path(CONFIG_FILE).write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_default_config() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)


def get_default_taiwan_config() -> dict:
    return copy.deepcopy(DEFAULT_TAIWAN_CONFIG)