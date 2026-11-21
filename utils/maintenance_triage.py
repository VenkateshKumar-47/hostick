import re

CATEGORY_RULES = {
    "Electrical": {
        "team": "Electrical Maintenance Team",
        "keywords": [
            "spark", "sparking", "short circuit", "electric shock", "shock",
            "burning smell", "smoke", "fire", "wire", "live wire", "exposed wire",
            "switchboard", "switch", "socket", "plug", "fan", "regulator",
            "light", "tube light", "bulb", "power", "power cut", "trip", "tripping",
            "mcb", "inverter", "geyser", "heater", "ac", "air conditioner",
        ],
    },
    "Plumbing": {
        "team": "Plumbing & Water Team",
        "keywords": [
            "leak", "leaking", "leakage", "pipe", "pipe burst", "burst",
            "flood", "flooding", "tap", "flush", "toilet", "bathroom", "sink",
            "basin", "drain", "drainage", "clog", "clogged", "blocked",
            "overflow", "water", "no water", "shower", "sewage",
        ],
    },
    "Carpentry & Furniture": {
        "team": "Carpentry & Civil Team",
        "keywords": [
            "door", "lock", "broken lock", "latch", "bolt", "hinge", "window",
            "glass", "broken glass", "shattered", "bed", "cot", "chair", "table",
            "desk", "cupboard", "wardrobe", "almirah", "shelf", "drawer",
            "mirror", "ceiling", "plaster", "crack", "wall",
        ],
    },
    "Housekeeping & Sanitation": {
        "team": "Housekeeping & Sanitation Team",
        "keywords": [
            "dirty", "dust", "dusty", "clean", "cleaning", "sweep", "mop",
            "trash", "garbage", "bin", "smell", "foul smell", "stain",
            "pest", "cockroach", "rat", "mosquito", "bedbug", "corridor",
        ],
    },
    "Internet & IT": {
        "team": "IT & Network Support Team",
        "keywords": [
            "wifi", "wi-fi", "internet", "lan", "ethernet", "router",
            "network", "no signal", "slow connection", "port",
        ],
    },
}

# Ordered by severity: first matching rule wins (deterministic safety hierarchy)
SAFETY_PRIORITY_RULES = [
    (
        "Critical",
        1,
        "Immediate safety/hazard risk detected",
        [
            "spark", "sparking", "short circuit", "electric shock", "shock",
            "fire", "smoke", "burning smell", "exposed wire", "live wire",
            "pipe burst", "burst", "flood", "flooding", "broken glass",
            "shattered", "ceiling", "broken lock", "sewage",
        ],
    ),
    (
        "High",
        2,
        "Essential utility or urgent habitability disruption",
        [
            "switchboard", "no power", "power cut", "tripping", "mcb",
            "no water", "overflow", "clogged", "blocked", "geyser",
            "fan not working", "broken fan", "no light", "bed", "cot",
            "door", "lock", "rat", "bedbug", "pest",
        ],
    ),
    (
        "Medium",
        3,
        "Standard repair required for daily comfort",
        [
            "leak", "leaking", "leakage", "tap", "flush", "fan", "light",
            "bulb", "tube light", "socket", "switch", "chair", "table",
            "cupboard", "window", "wifi", "wi-fi", "internet", "lan",
            "router", "cockroach", "mosquito", "drain",
        ],
    ),
    (
        "Low",
        4,
        "Routine upkeep or minor housekeeping request",
        [
            "dirty", "dust", "dusty", "clean", "cleaning", "sweep", "mop",
            "garbage", "trash", "stain", "smell", "slow", "squeaky",
        ],
    ),
]


def _keyword_in_text(keyword: str, text_lower: str) -> bool:
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return re.search(pattern, text_lower) is not None


def analyze_complaint(description: str) -> dict:
    """
    Deterministically parses a student maintenance complaint:
    - Extracts matched keywords
    - Determines Category & Assigned Maintenance Team
    - Sets Priority (Critical/High/Medium/Low) via safety rules
    """
    text_lower = description.lower().strip()

    # 1. Score categories by keyword matches
    category_scores = {}
    category_matches = {}

    for cat, cfg in CATEGORY_RULES.items():
        hits = [kw for kw in cfg["keywords"] if _keyword_in_text(kw, text_lower)]
        if hits:
            category_scores[cat] = len(hits)
            category_matches[cat] = hits

    if category_scores:
        best_category = max(category_scores, key=lambda c: category_scores[c])
        assigned_team = CATEGORY_RULES[best_category]["team"]
        matched_keywords = list(dict.fromkeys(category_matches[best_category]))
    else:
        best_category = "General Maintenance"
        assigned_team = "General Facility Team"
        matched_keywords = []

    # 2. Evaluate safety priority rules (highest severity wins)
    priority = "Low"
    priority_rank = 4
    rule_reason = "No hazard keywords found; queued as routine maintenance."
    priority_hits = []

    for level, rank, reason_label, kw_list in SAFETY_PRIORITY_RULES:
        hits = [kw for kw in kw_list if _keyword_in_text(kw, text_lower)]
        if hits:
            priority = level
            priority_rank = rank
            priority_hits = hits
            rule_reason = f"{reason_label} (matched: {', '.join(hits[:3])})."
            break

    # Combine all unique matched keywords for transparency
    all_keywords = list(dict.fromkeys(priority_hits + matched_keywords))

    return {
        "category": best_category,
        "assigned_team": assigned_team,
        "priority": priority,
        "priority_rank": priority_rank,
        "matched_keywords": ", ".join(all_keywords) if all_keywords else "General report",
        "triage_reason": rule_reason,
    }