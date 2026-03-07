from __future__ import annotations

from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel


class QueryType(StrEnum):
    event_explanation = "event_explanation"
    impact_analysis = "impact_analysis"
    connection_discovery = "connection_discovery"
    entity_relevance = "entity_relevance"
    update_request = "update_request"


class ConfidenceLevel(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class AgentQueryRequest(BaseModel):
    query: str


class NavigationPlan(BaseModel):
    center_on_event_id: Optional[str] = None
    zoom_level: Optional[str] = None  # "cluster" or "event"
    open_modal_event_id: Optional[str] = None
    pulse_event_ids: List[str] = []


class FinancialImpact(BaseModel):
    summary: str
    affected_sectors: List[str] = []
    impact_direction: str  # "positive", "negative", "mixed", "uncertain"
    uncertainty_notes: Optional[str] = None


class HighlightRelationship(BaseModel):
    event_a_id: str
    event_b_id: str
    relationship_type: Optional[str] = None


class SourceSnippet(BaseModel):
    source_name: str
    headline: str
    url: str
    type: str  # "internal" or "external"


class UpdateResult(BaseModel):
    status: str  # "success" or "failure"
    field_name: Optional[str] = None
    new_value: Optional[str] = None
    message: Optional[str] = None


class AgentResponse(BaseModel):
    answer: str
    confidence: ConfidenceLevel
    caution: Optional[str] = None
    mode: str  # "internal", "fallback_web", "update"
    query_type: QueryType
    top_event_id: Optional[str] = None
    relevant_event_ids: List[str] = []
    highlight_relationships: List[HighlightRelationship] = []
    navigation_plan: Optional[NavigationPlan] = None
    reasoning_steps: List[str] = []
    financial_impact: Optional[FinancialImpact] = None
    source_snippets: List[SourceSnippet] = []
    update_result: Optional[UpdateResult] = None
