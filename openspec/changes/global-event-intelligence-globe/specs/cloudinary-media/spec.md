## ADDED Requirements

### Requirement: Cloudinary React starter kit scaffold
The frontend SHALL be scaffolded using the official create-cloudinary-react starter kit as the bootstrap path.

#### Scenario: Project uses Cloudinary starter
- **WHEN** the frontend project is initialized
- **THEN** it SHALL be based on the create-cloudinary-react starter kit with Cloudinary React SDK dependencies present

### Requirement: Media config layer
The system SHALL provide a `mediaConfig.ts` utility that builds Cloudinary image URLs from public IDs when `VITE_CLOUDINARY_CLOUD_NAME` is set, and returns fallback placeholder URLs when the environment variable is absent.

#### Scenario: Cloudinary URL generation
- **WHEN** `VITE_CLOUDINARY_CLOUD_NAME` is set and a valid public ID is provided
- **THEN** the media config SHALL return a Cloudinary URL with appropriate transformations

#### Scenario: Fallback URL generation
- **WHEN** `VITE_CLOUDINARY_CLOUD_NAME` is not set
- **THEN** the media config SHALL return a local placeholder image URL

### Requirement: Event hero images use Cloudinary public IDs
Seed data SHALL reference Cloudinary public IDs for event hero images. The event modal SHALL render images through the media config layer.

#### Scenario: Seed data contains image references
- **WHEN** seed data is loaded
- **THEN** each event SHALL have an associated image public ID or URL for Cloudinary delivery

### Requirement: Graceful degradation without credentials
The application SHALL NOT crash or block functionality when Cloudinary credentials are missing. All features except Cloudinary image rendering SHALL work normally.

#### Scenario: App runs without Cloudinary credentials
- **WHEN** `VITE_CLOUDINARY_CLOUD_NAME` is not set
- **THEN** the application SHALL load and function fully with placeholder images displayed instead of Cloudinary images

### Requirement: No complex upload workflow
The MVP SHALL NOT include any Cloudinary upload widget or user-initiated upload flow. Cloudinary usage SHALL be limited to image delivery and transformation for seeded event images.

#### Scenario: No upload UI exists
- **WHEN** the user navigates the entire application
- **THEN** there SHALL be no upload button, drag-and-drop zone, or file picker for Cloudinary uploads
