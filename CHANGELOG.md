# Changelog

## [Unreleased]

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

## [0.1.5] - 2025-09-27

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

## [0.1.4] - 2025-09-27

### Added
- Comprehensive debug logging throughout the integration
- Enhanced error handling with detailed error messages
- Improved session management with proper cleanup
- Better timeout and connection error handling
- Custom icon.png and logo.png for better visuals in Home Assistant

### Changed
- Multiple students support - integration now fetches all children automatically
- School selection via dropdown with autocomplete (fallback to text input)
- Automatic school year detection (no manual year input needed)
- Enhanced authentication flow with better error reporting
- Updated translations for new UI flow (Hebrew and English)

### Fixed
- Fixed "Unclosed client session" errors during integration unload
- Improved authentication error messages
- Better handling of network timeouts and connection issues
- Fixed session cleanup on integration reload/restart
- Fixed syntax error in config flow schema

## [0.1.3] - 2025-09-27

### Added
- Comprehensive debug logging throughout the integration
- Enhanced error handling with detailed error messages
- Improved session management with proper cleanup
- Better timeout and connection error handling

### Changed
- Multiple students support - integration now fetches all children automatically
- School selection via dropdown with autocomplete (fallback to text input)
- Automatic school year detection (no manual year input needed)
- Enhanced authentication flow with better error reporting

### Fixed
- Fixed "Unclosed client session" errors during integration unload
- Improved authentication error messages
- Better handling of network timeouts and connection issues
- Fixed session cleanup on integration reload/restart

## [0.1.2] - 2025-09-27

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

## [0.1.1] - 2025-09-27

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1-beta.1] - 2025-09-27 (Pre-release)

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

## [0.1.0] - 2025-01-XX

### Added
- Initial release of Mashov integration for Home Assistant
- Support for authentication with Mashov API
- Four sensors: Timetable, Weekly Plan, Homework, Behavior
- Configurable homework days range (back/forward)
- Daily automatic refresh
- Manual refresh service
- Hebrew and English translations
- Options flow for configuration
- Diagnostics support

### Features
- Student selection support
- Automatic re-authentication on token expiry
- Comprehensive error handling
- Device information for each student
