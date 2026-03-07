export type EventType =
  | 'geopolitics'
  | 'trade_supply_chain'
  | 'energy_commodities'
  | 'financial_markets'
  | 'climate_disasters'
  | 'policy_regulation'

export type RelationshipType =
  | 'market_reaction'
  | 'commodity_link'
  | 'supply_chain_link'
  | 'regional_spillover'
  | 'policy_impact'
  | 'same_event_family'

export interface Event {
  id: string
  title: string
  event_type: EventType
  primary_latitude: number
  primary_longitude: number
  start_time: string
  end_time: string | null
  confidence_score: number
  canada_impact_summary: string
  image_url: string | null
}

export interface SourceCard {
  source_name: string
  headline: string
  published_at: string
  url: string
}

export interface RelatedEvent {
  event_id: string
  title: string
  event_type: EventType
  relationship_type: RelationshipType
  relationship_score: number
  reason: string
  primary_latitude: number
  primary_longitude: number
}

export interface EngagementSnapshot {
  reddit_upvotes: number
  reddit_comments: number
  poly_volume: number
  poly_comments: number
  twitter_likes: number
  twitter_views: number
  twitter_comments: number
  twitter_reposts: number
}

export interface EventDetail extends Event {
  summary: string
  sources: SourceCard[]
  related_events: RelatedEvent[]
  entities: string[]
  engagement: EngagementSnapshot | null
}

export interface EventListResponse {
  events: Event[]
  total: number
}

export interface FilterResponse {
  event_types: string[]
  relationship_types: string[]
}

export interface TimelineResponse {
  events: Event[]
  min_time: string
  max_time: string
}

export interface RelatedEventsResponse {
  related_events: RelatedEvent[]
}

export interface ContentPoint {
  id: string
  title: string | null
  latitude: number
  longitude: number
  event_type: string | null
  published_at: string | null
}

export interface ContentPointsResponse {
  points: ContentPoint[]
}
