## ADDED Requirements

### Requirement: Auto-spin on initial load
The globe SHALL auto-spin when the application first loads.

#### Scenario: Globe spins on startup
- **WHEN** the application loads and the globe renders
- **THEN** the globe SHALL be auto-spinning

### Requirement: Stop auto-spin on user interaction
Any user interaction with the globe or UI SHALL immediately stop auto-spin. Interactions include: mouse clicks, mouse drags, keyboard input, agent query submission, filter toggle, and timeline scrub.

#### Scenario: Mouse interaction stops spin
- **WHEN** the user clicks or drags on the globe
- **THEN** auto-spin SHALL stop immediately

#### Scenario: Agent query stops spin
- **WHEN** the user submits an agent query
- **THEN** auto-spin SHALL stop immediately

#### Scenario: Filter toggle stops spin
- **WHEN** the user toggles an event type filter
- **THEN** auto-spin SHALL stop immediately

### Requirement: Resume auto-spin after 5 minutes of inactivity
Auto-spin SHALL resume only after 5 minutes of continuous user inactivity. Any interaction during the countdown SHALL reset the 5-minute timer.

#### Scenario: Inactivity resumes spin
- **WHEN** 5 minutes pass without any user interaction
- **THEN** auto-spin SHALL resume

#### Scenario: Interaction resets timer
- **WHEN** the user interacts with the UI during the inactivity countdown
- **THEN** the 5-minute timer SHALL reset to zero and auto-spin SHALL remain stopped

### Requirement: Auto-spin state accessible to components
The auto-spin state (spinning/stopped) and the inactivity timer SHALL be accessible through the shared application context so that any component can read or trigger spin state changes.

#### Scenario: Component reads spin state
- **WHEN** any component queries the auto-spin state
- **THEN** it SHALL receive the current spinning/stopped status
