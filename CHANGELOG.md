# Changelog

## [Unreleased]

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

## [0.1.18] - 2025-01-28

### Fixed
- Fixed "cannot access local variable 'asyncio'" error in config flow
- Added proper asyncio import at module level to prevent variable scope issues
- Resolved authentication flow crash during school selection process

## [0.1.17] - 2025-01-28

### Fixed
- Fixed "Cannot reach Mashov" authentication error
- Updated API version from 3.20210425 to 4.20250101 for compatibility with latest Mashov API
- Enhanced authentication token detection with multiple fallback methods
- Added comprehensive retry mechanism (3 attempts with 2-second delays) for login failures
- Improved error handling and logging throughout authentication process
- Enhanced session timeout settings (60 seconds total, 30 seconds connect)
- Better handling of network timeouts and connection issues
- Improved error messages in Hebrew translations for better user experience

### Changed
- Enhanced device identification parameters for better API compatibility
- Improved authorization header handling with multiple token formats
- Better session management with proper connection limits

## [0.1.16] - 2025-09-28

### Fixed
- Fixed SelectSelector value type error - values must be strings
- Corrected school selection dropdown data type handling
- Improved school choice processing with proper type conversion

## [0.1.15] - 2025-09-28

### Fixed
- Fixed integration failure during school search
- Removed premature authentication attempt during school name resolution
- Improved school search flow to only authenticate after school selection
- Enhanced error handling for school search operations

## [0.1.14] - 2025-09-28

### Fixed
- Fixed school selection display when multiple schools match
- Added proper school names with city and semel in selection dropdown
- Improved school choice presentation with SelectSelector
- Enhanced user experience for multiple school matches

## [0.1.13] - 2025-09-27

### Fixed
- Fixed Config Flow 400 Bad Request error by switching back to TextSelector
- Reduced school catalog from 200 to 50 items for better performance
- Improved autocomplete functionality with proper semel extraction
- Enhanced school selection user experience

## [0.1.12] - 2025-09-27

### Improved
- Properly implemented asyncio.create_task for all MainThread operations
- Fixed MainThread blocking in Config Flow, authentication, and data fetching
- Enhanced performance by running all network operations in background tasks
- Improved UI responsiveness during integration setup and data updates

## [0.1.11] - 2025-09-27

### Fixed
- Fixed Config Flow 400 Bad Request error
- Reverted to SelectSelector for better compatibility
- Fixed dropdown selection handling
- Improved school selection user experience

## [0.1.10] - 2025-09-27

### Fixed
- Fixed autocomplete error: 'NoneType' object has no attribute 'lower'
- Fixed session management - keep session open for future use
- Improved error handling for None values in school catalog
- Fixed "Unclosed client session" error during authentication
- Enhanced school catalog sorting with proper None handling

## [0.1.9] - 2025-09-27

### Improved
- Optimized MainThread usage to prevent UI blocking
- Added asyncio.create_task for parallel execution
- Improved performance by running operations in separate tasks
- Enhanced responsiveness during data fetching and school catalog loading

## [0.1.8] - 2025-09-27

### Fixed
- Fixed "Unclosed client session" error during authentication
- Improved session management with proper cleanup
- Added timeout handling for student data fetching
- Enhanced error handling for network issues
- Fixed session closure timing issues

## [0.1.7] - 2025-09-27

### Fixed
- Fixed ValueError in school selection dropdown
- Replaced SelectSelector with TextSelector for better autocomplete support
- Added proper semel extraction from autocomplete format
- Improved school selection user experience with working autocomplete
- Added debug logging for school ID selection process

## [0.1.6] - 2025-09-27

### Improved
- Enhanced school selection autocomplete performance
- Reduced school list from 500 to 200 items for better UI responsiveness
- Added sorting by school name for improved user experience
- Optimized dropdown performance with sort=True option
- Updated documentation with autocomplete improvements

### Fixed
- Improved autocomplete functionality in school selection dropdown
- Better handling of large school catalogs

## [0.1.5] - 2025-09-27

### Fixed
- Fixed Config Flow schema definition causing 400 Bad Request error
- Improved school selection dropdown handling with proper error handling
- Limited school catalog to 200 items for better autocomplete performance
- Added fallback to text input if dropdown creation fails
- Enhanced error logging for better troubleshooting of Config Flow issues
- Improved autocomplete functionality with sorted school list
- Optimized dropdown performance with sort=True option

## [0.1.4] - 2025-09-27

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
