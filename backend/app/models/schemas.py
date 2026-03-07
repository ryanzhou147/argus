from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .enums import EventType, RelationshipType


# ------------------------------------------------------------------
# Base / internal models
# ------------------------------------------------------------------

class Source(BaseModel):
    id: str
    name: str
    type: str
    base_url: str
    trust_score: float


class ContentItem(BaseModel):
    id: str
    source_id: str
    title: str
    body: str
    url: str
    published_at: datetime
    latitude: float
    longitude: float
    event_type: EventType
    sentiment_score: Optional[float] = None
    # SQL content_table has market_signal FLOAT; we use str for categorical labels (e.g. "freight_spike").
    # Consider changing SQL to TEXT if storing labels; or store numeric and map in app.
    market_signal: Optional[str] = None
    image_url: Optional[str] = None


class Entity(BaseModel):
    id: str
    name: str
    canonical_name: str
    entity_type: str


class ContentEntity(BaseModel):
    content_item_id: str
    entity_id: str
    relevance_score: float


class EventRelationship(BaseModel):
    id: str
    event_a_id: str
    event_b_id: str
    relationship_type: RelationshipType
    relationship_score: float
    # SQL event_relationships.reason_codes is TEXT[]; join to str when reading from DB
    reason_codes: str


class Engagement(BaseModel):
    id: str
    event_id: str
    reddit_upvotes: int
    reddit_comments: int
    poly_volume: float  # SQL: FLOAT
    poly_comments: int
    twitter_likes: Optional[int] = None
    twitter_views: Optional[int] = None
    twitter_comments: Optional[int] = None
    twitter_reposts: Optional[int] = None


# ------------------------------------------------------------------
# API response models
# ------------------------------------------------------------------

class EngagementSnapshot(BaseModel):
    reddit_upvotes: int
    reddit_comments: int
    poly_volume: float  # SQL engagement.poly_volume is FLOAT
    poly_comments: int
    twitter_likes: Optional[int] = None
    twitter_views: Optional[int] = None
    twitter_comments: Optional[int] = None
    twitter_reposts: Optional[int] = None


class SourceCard(BaseModel):
    source_name: str
    headline: str
    published_at: datetime
    url: str


class RelatedEvent(BaseModel):
    event_id: str
    title: str
    event_type: EventType
    relationship_type: RelationshipType
    relationship_score: float
    reason: str
    primary_latitude: float
    primary_longitude: float


class Event(BaseModel):
    id: str
    title: str
    event_type: EventType
    primary_latitude: float
    primary_longitude: float
    start_time: datetime
    end_time: Optional[datetime] = None
    confidence_score: float
    canada_impact_summary: str
    image_url: Optional[str] = None


class EventDetail(Event):
    summary: str
    sources: List[SourceCard] = []
    related_events: List[RelatedEvent] = []
    entities: List[str] = []
    engagement: Optional[EngagementSnapshot] = None


# ------------------------------------------------------------------
# List / wrapper response models
# ------------------------------------------------------------------

class EventListResponse(BaseModel):
    events: List[Event]
    total: int


class FilterResponse(BaseModel):
    event_types: List[str]
    relationship_types: List[str]


class TimelineResponse(BaseModel):
    events: List[Event]
    min_time: datetime
    max_time: datetime


class RelatedEventsResponse(BaseModel):
    related_events: List[RelatedEvent]


# ------------------------------------------------------------------
# Market signals (from Polymarket / Kalshi scrapers)
# ------------------------------------------------------------------

class MarketSignalEngagement(BaseModel):
    poly_volume: float
    poly_comments: Optional[int] = None


class MarketSignal(BaseModel):
    title: str
    body: str
    url: str
    published_at: Optional[datetime] = None
    engagement: MarketSignalEngagement
    source: str  # "polymarket" | "kalshi"
    error: Optional[bool] = None  # True if this source failed to fetch


class MarketSignalsResponse(BaseModel):
    signals: List[MarketSignal]
    total: int
