## ADDED Requirements

### Requirement: Timeline slider component
The system SHALL render a timeline slider at the bottom of the viewport that represents the time range of all seeded events.

#### Scenario: Timeline displays full range
- **WHEN** the application loads
- **THEN** the timeline slider SHALL span from the earliest `start_time` to the latest `start_time` across all events

### Requirement: Events appear based on timeline position
Events SHALL appear on the globe when the current timeline position is greater than or equal to their `start_time`. Events SHALL disappear only when filtered out or outside the selected range.

#### Scenario: Event becomes visible as timeline advances
- **WHEN** the timeline position reaches an event's `start_time`
- **THEN** the event node SHALL appear on the globe

#### Scenario: Event remains visible after its start_time
- **WHEN** the timeline position is past an event's `start_time` and the event is not filtered out
- **THEN** the event node SHALL remain visible on the globe

### Requirement: Drag mode
The timeline SHALL support manual drag interaction where the user can scrub to any position within the time range.

#### Scenario: User drags timeline
- **WHEN** the user drags the timeline handle to a new position
- **THEN** the timeline position SHALL update and the globe SHALL re-render with the corresponding visible events

### Requirement: Play mode
The timeline SHALL support an auto-play mode that automatically advances the timeline position over time.

#### Scenario: User starts playback
- **WHEN** the user clicks the play button
- **THEN** the timeline position SHALL automatically advance at a steady rate and the globe SHALL update accordingly

#### Scenario: User pauses playback
- **WHEN** the user clicks the pause button during playback
- **THEN** the timeline position SHALL stop advancing

### Requirement: Timeline state drives globe redraw
The timeline state SHALL be the single source of truth for which events are temporally visible. Changes to the timeline position SHALL trigger a globe re-render.

#### Scenario: Globe syncs with timeline
- **WHEN** the timeline position changes by any mechanism (drag, play, or programmatic)
- **THEN** the globe SHALL immediately reflect the updated set of visible events
