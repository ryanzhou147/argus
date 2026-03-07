## ADDED Requirements

### Requirement: Globe supports agent-driven camera control
The globe SHALL expose a programmatic camera control API that allows the agent navigation system to animate the camera to specific geographic coordinates and zoom levels.

#### Scenario: Programmatic camera animation
- **WHEN** the agent navigation system requests centering on coordinates (lat, lng) with a zoom level
- **THEN** the globe SHALL smoothly animate the camera to the specified position

### Requirement: Globe supports node pulsing
The globe SHALL support a pulsing or glowing visual effect on specific event nodes, driven by the agent state. Pulsed nodes SHALL be visually distinct from normal nodes.

#### Scenario: Agent pulses specific nodes
- **WHEN** the agent state includes pulse_event_ids
- **THEN** the corresponding event nodes SHALL display a pulsing animation that is visually distinct from their default appearance

#### Scenario: Pulse cleared on new query
- **WHEN** a new agent query is submitted
- **THEN** all prior pulse effects SHALL be cleared before new ones are applied

### Requirement: Globe supports arc highlighting
The globe SHALL support visually highlighting specific arcs driven by the agent state. Highlighted arcs SHALL be visually distinct from normal arcs (e.g., brighter, thicker, or animated).

#### Scenario: Agent highlights specific arcs
- **WHEN** the agent state includes highlight_relationships
- **THEN** the arcs between those event pairs SHALL be rendered with a distinct visual style

#### Scenario: Highlights cleared on new query
- **WHEN** a new agent query is submitted
- **THEN** all prior arc highlights SHALL be cleared before new ones are applied

### Requirement: Globe clears prior agent state
The globe SHALL support clearing all agent-driven visual state (pulsed nodes, highlighted arcs, camera position) when instructed by the agent context.

#### Scenario: Agent state reset
- **WHEN** clear_previous_agent_state is true in the navigation plan
- **THEN** the globe SHALL remove all agent-driven pulsing, arc highlighting, and reset to a neutral visual state before applying new effects

## MODIFIED Requirements

### Requirement: Globe responds to timeline and filter state
The globe SHALL reactively update its displayed nodes and arcs when the timeline position, active filters, or agent highlight state change.

#### Scenario: Timeline change updates globe
- **WHEN** the timeline position changes
- **THEN** the globe SHALL re-render to show only events with `start_time <= timelinePosition`

#### Scenario: Filter change updates globe
- **WHEN** the user toggles an event type filter
- **THEN** the globe SHALL re-render to show only events matching active filters

#### Scenario: Agent state change updates globe
- **WHEN** the agent state changes (new highlights, pulses, or navigation)
- **THEN** the globe SHALL re-render to reflect the agent-driven visual changes while preserving existing filter and timeline state
