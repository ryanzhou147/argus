from enum import StrEnum


class EventType(StrEnum):
    GEOPOLITICS = "geopolitics"
    TRADE_SUPPLY_CHAIN = "trade_supply_chain"
    ENERGY_COMMODITIES = "energy_commodities"
    FINANCIAL_MARKETS = "financial_markets"
    CLIMATE_DISASTERS = "climate_disasters"
    POLICY_REGULATION = "policy_regulation"


class RelationshipType(StrEnum):
    MARKET_REACTION = "market_reaction"
    COMMODITY_LINK = "commodity_link"
    SUPPLY_CHAIN_LINK = "supply_chain_link"
    REGIONAL_SPILLOVER = "regional_spillover"
    POLICY_IMPACT = "policy_impact"
    SAME_EVENT_FAMILY = "same_event_family"
