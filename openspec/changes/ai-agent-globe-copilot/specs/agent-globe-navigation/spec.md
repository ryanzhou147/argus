## ADDED Requirements

### Requirement: Clear prior agent highlights
Before executing a new agent navigation plan, the globe SHALL clear all previously applied agent highlights (pulsed nodes, highlighted arcs, previous navigation state).

#### Scenario: New query clears old highlights
- **WHEN** the user submits a new agent query
- **THEN** the globe SHALL clear all prior agent-driven pulsing, arc highlighting, and navigation state before applying the new response

### Requirement: Pause auto-spin on agent response
The globe SHALL immediately stop auto-spin when an agent response arrives with a navigation plan.

#### Scenario: Auto-spin stops on agent navigation
- **WHEN** the agent returns a response with a `navigation_plan`
- **THEN** globe auto-spin SHALL stop immediately

### Requirement: Center on top relevant event
The globe SHALL smoothly animate the camera to center on the event specified by `navigation_plan.center_on_event_id`.

#### Scenario: Camera centers on event
- **WHEN** the agent response includes `center_on_event_id`
- **THEN** the globe camera SHALL animate to center on that event's geographic coordinates

### Requirement: Zoom level control
The globe SHALL zoom to the level specified by `navigation_plan.zoom_level`. `cluster` means a wider view showing the event and its neighbors; `event` means a tighter zoom on the single event.

#### Scenario: Cluster zoom
- **WHEN** `zoom_level` is `cluster`
- **THEN** the globe SHALL zoom to show the target event and nearby related events

#### Scenario: Event zoom
- **WHEN** `zoom_level` is `event`
- **THEN** the globe SHALL zoom tightly on the single target event

### Requirement: Pulse relevant nodes
The globe SHALL apply a pulsing or glowing visual effect to all event nodes whose IDs are in `navigation_plan.pulse_event_ids`.

#### Scenario: Nodes pulse after agent response
- **WHEN** the agent response includes `pulse_event_ids: [1, 3, 7]`
- **THEN** event nodes 1, 3, and 7 SHALL display a pulsing or glowing animation

### Requirement: Highlight relevant arcs
The globe SHALL visually highlight arcs corresponding to the relationships in `highlight_relationships`.

#### Scenario: Arcs highlighted
- **WHEN** the agent response includes `highlight_relationships` with event pairs
- **THEN** the arcs between those event pairs SHALL be visually distinct (e.g., brighter color, thicker line, or animation)

### Requirement: Auto-open modal
The globe SHALL automatically open the event modal for the event specified by `navigation_plan.open_modal_event_id`.

#### Scenario: Modal opens automatically
- **WHEN** the agent response includes `open_modal_event_id`
- **THEN** the event modal SHALL open for that event after the camera animation completes

### Requirement: Sequenced multi-event focus
When multiple events are relevant, the globe SHALL sequence the focus from the anchor event (center_on_event_id) to connected events, with brief pauses between transitions.

#### Scenario: Multi-event sequence
- **WHEN** the agent response includes `pulse_event_ids` with more than one event and `highlight_relationships` connecting them
- **THEN** the globe SHALL first center on the anchor event, then briefly animate to show connected events in sequence
