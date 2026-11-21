import re

FOOD_SAFETY_RULES = [
    (
        "Critical",
        1,
        "Severe food safety / contamination hazard detected",
        [
            "insect", "insects", "worm", "worms", "cockroach", "bug", "bugs",
            "fly", "flies", "lizard", "ant", "ants", "rotten", "spoiled",
            "spoilt", "fungus", "mold", "mould", "food poisoning", "vomiting",
            "stomach ache", "glass", "metal", "plastic", "hair", "stale",
        ],
    ),
    (
        "High",
        2,
        "Hygiene violation or unsafe preparation detected",
        [
            "uncooked", "raw", "undercooked", "foul smell", "bad smell",
            "stinking", "sour", "expired", "dirty plate", "dirty plates",
            "unhygienic", "dirty water", "contaminated", "oily", "burnt",
        ],
    ),
    (
        "Medium",
        3,
        "Food serving quality or quantity issue",
        [
            "cold food", "cold", "watery", "salty", "too spicy", "less quantity",
            "insufficient", "late", "delay", "shortage", "tasteless",
        ],
    ),
]


def _has_keyword(keyword: str, text_lower: str) -> bool:
    return re.search(r"\b" + re.escape(keyword.lower()) + r"\b", text_lower) is not None


def analyze_food_complaint(issue_type: str, description: str, has_photo: bool = False) -> dict:
    text_lower = f"{issue_type} {description}".lower().strip()

    # Forced Critical escalation for explicit severe issue categories
    if issue_type in ("Insects / Foreign Object", "Rotten / Spoiled Food"):
        hits = [kw for kw in FOOD_SAFETY_RULES[0][3] if _has_keyword(kw, text_lower)]
        photo_note = " Photo evidence attached." if has_photo else ""
        return {
            "priority": "Critical",
            "priority_rank": 1,
            "triage_reason": f"Immediate mess inspection required ({issue_type}).{photo_note}",
            "matched_keywords": ", ".join(hits) if hits else issue_type,
        }

    for level, rank, reason_label, kw_list in FOOD_SAFETY_RULES:
        hits = [kw for kw in kw_list if _has_keyword(kw, text_lower)]
        if hits:
            photo_note = " Photo evidence attached." if has_photo else ""
            return {
                "priority": level,
                "priority_rank": rank,
                "triage_reason": f"{reason_label} (matched: {', '.join(hits[:3])}).{photo_note}",
                "matched_keywords": ", ".join(hits),
            }

    return {
        "priority": "Low",
        "priority_rank": 4,
        "triage_reason": "Routine mess feedback queued for warden review.",
        "matched_keywords": issue_type,
    }