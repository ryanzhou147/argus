## ADDED Requirements

### Requirement: Filter bar component
The system SHALL render a filter bar displaying all six event types as toggleable options: `geopolitics`, `trade_supply_chain`, `energy_commodities`, `financial_markets`, `climate_disasters`, `policy_regulation`.

#### Scenario: All filters active by default
- **WHEN** the application loads
- **THEN** all six event type filters SHALL be active and all events SHALL be visible on the globe

### Requirement: Toggle event type filter
The user SHALL be able to toggle individual event types on or off. Toggling a filter SHALL update the visible nodes and arcs on the globe in real time.

#### Scenario: User deactivates a filter
- **WHEN** the user deactivates the `geopolitics` filter
- **THEN** all events with `event_type` equal to `geopolitics` SHALL be hidden from the globe and their associated arcs SHALL also be hidden

#### Scenario: User reactivates a filter
- **WHEN** the user reactivates the `geopolitics` filter
- **THEN** events with `event_type` equal to `geopolitics` that are within the current timeline range SHALL reappear on the globe

### Requirement: Filters combine with timeline
Active filters and the current timeline position SHALL be combined to determine visible events. An event is visible only if its type is active AND its `start_time` is within the timeline range.

#### Scenario: Combined filtering
- **WHEN** the user has deactivated `climate_disasters` and the timeline is at a position where 10 events have started
- **THEN** the globe SHALL show only those of the 10 events whose `event_type` is not `climate_disasters`

### Requirement: Filter state reflected in filter bar UI
Each filter option in the filter bar SHALL visually indicate whether it is active or inactive.

#### Scenario: Active filter appearance
- **WHEN** a filter is active
- **THEN** its button or chip SHALL appear visually highlighted or filled

#### Scenario: Inactive filter appearance
- **WHEN** a filter is inactive
- **THEN** its button or chip SHALL appear visually dimmed or outlined
