# Release Management

This document explains how to manage releases for the ha-mashov integration.

## Quick Start

### Create a Pre-release (Beta/Alpha)
```powershell
.\scripts\release.ps1 -Version 0.1.1-beta.1 -PreRelease
```

### Create a Stable Release
```powershell
.\scripts\release.ps1 -Version 0.1.1
```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.0.0)
- **Pre-releases**: Add suffix like `-beta.1`, `-alpha.2`, `-rc.1`

### Examples:
- `0.1.0` - Initial stable release
- `0.1.1` - Bug fix release
- `0.2.0` - New features
- `0.1.1-beta.1` - Pre-release with bug fixes
- `0.2.0-alpha.1` - Pre-release with new features

## What the Script Does

1. **Updates version files:**
   - `VERSION`
   - `custom_components/mashov/manifest.json`

2. **Updates documentation:**
   - `CHANGELOG.md` with new version entry

3. **Git operations:**
   - Commits changes
   - Pushes to GitHub
   - Creates and pushes git tag

4. **Shows GitHub CLI command** for creating the actual release

## Manual Steps After Script

### Option 1: Using GitHub CLI (Recommended)
```bash
# For stable release
gh release create v0.1.1 --title "Release v0.1.1" --notes "See CHANGELOG.md for details"

# For pre-release
gh release create v0.1.1-beta.1 --prerelease --title "Release v0.1.1-beta.1" --notes "See CHANGELOG.md for details"
```

### Option 2: Using GitHub Web Interface
1. Go to [Releases](https://github.com/NirBY/ha-mashov/releases)
2. Click "Create a new release"
3. Select the tag created by the script
4. Add title and description
5. Check "Set as a pre-release" if applicable
6. Click "Publish release"

## Testing Pre-releases

### Install Pre-release via HACS:
1. HACS → Integrations → Mashov
2. Click the version number
3. Select the pre-release version
4. Install

### Or manually:
1. Download the pre-release zip from GitHub
2. Extract to `custom_components/mashov/`
3. Restart Home Assistant

## Release Checklist

Before creating a release:

- [ ] All features implemented and tested
- [ ] CHANGELOG.md updated with changes
- [ ] Version numbers updated
- [ ] Code reviewed
- [ ] Tests passing (if any)
- [ ] Documentation updated

For stable releases:
- [ ] Pre-release tested by community
- [ ] No critical bugs reported
- [ ] All breaking changes documented

## Rollback

If a release has issues:

1. **Mark as deprecated** in GitHub release notes
2. **Create hotfix** with new version
3. **Update HACS** to recommend latest stable version

## HACS Integration

- **Stable releases** appear in HACS automatically
- **Pre-releases** can be installed manually by selecting version
- **HACS Store** requires stable releases only
