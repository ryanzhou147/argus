import type {
  ContentArcsResponse,
  ContentPointsResponse,
  EventDetail,
  EventListResponse,
  EventType,
  FilterResponse,
  RelatedEventsResponse,
  TimelineResponse,
} from '../types/events'
import type { AgentResponse } from '../types/agent'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

export function getEvents(params?: {
  event_type?: EventType
  start_time?: string
  end_time?: string
}): Promise<EventListResponse> {
  const qs = new URLSearchParams()
  if (params?.event_type) qs.set('event_type', params.event_type)
  if (params?.start_time) qs.set('start_time', params.start_time)
  if (params?.end_time) qs.set('end_time', params.end_time)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return fetchJson<EventListResponse>(`/events${query}`)
}

export function getEventById(eventId: string): Promise<EventDetail> {
  return fetchJson<EventDetail>(`/events/${eventId}`)
}

export function getRelatedEvents(eventId: string): Promise<RelatedEventsResponse> {
  return fetchJson<RelatedEventsResponse>(`/events/${eventId}/related`)
}

export function getFilters(): Promise<FilterResponse> {
  return fetchJson<FilterResponse>('/filters')
}

export function getTimeline(): Promise<TimelineResponse> {
  return fetchJson<TimelineResponse>('/timeline')
}

export function postAgentQuery(query: string): Promise<AgentResponse> {
  return postJson<AgentResponse>('/agent/query', { query })
}

export function getContentPoints(): Promise<ContentPointsResponse> {
  return fetchJson<ContentPointsResponse>('/content/points')
}

export function getContentArcs(threshold = 0.7): Promise<ContentArcsResponse> {
  return fetchJson<ContentArcsResponse>(`/content/arcs?threshold=${threshold}`)
}
