export type QueryType =
  | 'event_explanation'
  | 'impact_analysis'
  | 'connection_discovery'
  | 'entity_relevance'
  | 'update_request'

export type ConfidenceLevel = 'high' | 'medium' | 'low'

export interface NavigationPlan {
  center_on_event_id: string | null
  zoom_level: 'cluster' | 'event' | null
  open_modal_event_id: string | null
  pulse_event_ids: string[]
}

export interface FinancialImpact {
  summary: string
  affected_sectors: string[]
  impact_direction: 'positive' | 'negative' | 'mixed' | 'uncertain'
  uncertainty_notes: string | null
}

export interface HighlightRelationship {
  event_a_id: string
  event_b_id: string
  relationship_type: string | null
}

export interface SourceSnippet {
  source_name: string
  headline: string
  url: string
  type: 'internal' | 'external'
}

export interface UpdateResult {
  status: 'success' | 'failure'
  field_name: string | null
  new_value: string | null
  message: string | null
}

export interface AgentResponse {
  answer: string
  confidence: ConfidenceLevel
  caution: string | null
  mode: 'internal' | 'fallback_web' | 'update'
  query_type: QueryType
  top_event_id: string | null
  relevant_event_ids: string[]
  highlight_relationships: HighlightRelationship[]
  navigation_plan: NavigationPlan | null
  reasoning_steps: string[]
  financial_impact: FinancialImpact | null
  source_snippets: SourceSnippet[]
  update_result: UpdateResult | null
  /** Maps event_id -> title for resolving [cite:id] inline citations in the answer */
  cited_event_map: Record<string, string>
}
