## ADDED Requirements

### Requirement: Globe renders event nodes
The system SHALL render a 3D globe using react-globe.gl with event nodes plotted at each event's `primary_latitude` and `primary_longitude`.

#### Scenario: Events appear as nodes on globe
- **WHEN** the globe component receives event data
- **THEN** each event SHALL be rendered as a point node at its geographic coordinates

#### Scenario: Node color indicates event type
- **WHEN** an event node is rendered
- **THEN** its color SHALL correspond to the event's `event_type` using a consistent color mapping across the application

### Requirement: Globe renders relationship arcs
The system SHALL render arcs between related events using coordinates from `event_relationships`. Arcs SHALL connect the `primary_latitude`/`primary_longitude` of `event_a` to the `primary_latitude`/`primary_longitude` of `event_b`.

#### Scenario: Arcs connect related events
- **WHEN** the globe receives relationship data
- **THEN** arcs SHALL be drawn between each pair of related events

#### Scenario: Arc visibility matches filtered events
- **WHEN** one or both events in a relationship are hidden by filters or timeline
- **THEN** the arc between them SHALL NOT be rendered

### Requirement: Click node opens modal
The system SHALL open the event modal/side panel when a user clicks an event node on the globe.

#### Scenario: Node click triggers modal
- **WHEN** the user clicks an event node
- **THEN** the system SHALL fetch the full event detail and open the event modal/side panel

### Requirement: Hover node shows tooltip
The system SHALL display a lightweight tooltip when the user hovers over an event node on the globe.

#### Scenario: Tooltip on hover
- **WHEN** the user hovers over an event node
- **THEN** a tooltip SHALL appear showing at minimum the event title and event type

#### Scenario: Tooltip disappears on mouse leave
- **WHEN** the user moves the mouse away from the event node
- **THEN** the tooltip SHALL be hidden

### Requirement: Globe is full-screen or near-full-screen
The globe SHALL occupy the full viewport or near-full viewport as the primary visual element of the application.

#### Scenario: Globe fills viewport
- **WHEN** the application loads
- **THEN** the globe SHALL be the dominant visual element, filling most of the viewport area with filter bar, timeline, and legend overlaid on top

### Requirement: Globe responds to timeline and filter state
The globe SHALL reactively update its displayed nodes and arcs when the timeline position or active filters change.

#### Scenario: Timeline change updates globe
- **WHEN** the timeline position changes
- **THEN** the globe SHALL re-render to show only events with `start_time <= timelinePosition`

#### Scenario: Filter change updates globe
- **WHEN** the user toggles an event type filter
- **THEN** the globe SHALL re-render to show only events matching active filters
