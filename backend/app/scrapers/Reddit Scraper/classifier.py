RULES = [
    ("geopolitics", [
        "war", "conflict", "military", "nato", "sanctions", "troops",
        "invasion", "missile", "coup", "diplomat", "ceasefire", "territorial",
    ]),
    ("trade_supply_chain", [
        "trade", "tariff", "supply chain", "export", "import", "wto",
        "semiconductor", "shipping", "logistics", "manufacturing",
    ]),
    ("energy_commodities", [
        "oil", "gas", "opec", "lng", "coal", "renewable", "solar", "wind",
        "pipeline", "barrel", "refinery", "nuclear",
    ]),
    ("financial_markets", [
        "market", "gdp", "inflation", "recession", "fed", "interest rate",
        "stock", "currency", "debt", "bond", "banking", "earnings",
    ]),
    ("climate_disasters", [
        "climate", "flood", "earthquake", "hurricane", "wildfire", "drought",
        "tsunami", "disaster", "emissions", "tornado", "typhoon",
    ]),
    ("policy_regulation", [
        "law", "regulation", "policy", "congress", "parliament", "election",
        "legislation", "government", "court", "supreme", "treaty",
    ]),
]

SUBREDDIT_DEFAULTS = {
    "worldnews":        "geopolitics",
    "geopolitics":      "geopolitics",
    "Economics":        "trade_supply_chain",
    "investing":        "financial_markets",
    "energy":           "energy_commodities",
    "environment":      "climate_disasters",
    "climate":          "climate_disasters",
    "naturaldisasters": "climate_disasters",
    "politics":         "policy_regulation",
}


def classify(title: str, subreddit: str) -> str:
    lower = title.lower()
    for category, keywords in RULES:
        if any(kw in lower for kw in keywords):
            return category
    return SUBREDDIT_DEFAULTS.get(subreddit, "geopolitics")
