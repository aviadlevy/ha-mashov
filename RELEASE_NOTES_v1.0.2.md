# Release v1.0.2 - Fix State Attributes Size Limit

## 🐛 Bug Fix - State Attributes Size Limit

### Fixed
- **[Bug #2]** State attributes exceeding 16KB limit causing database warnings

### What Changed
- 🧹 **Cleaned data**: Removed redundant technical fields (GUIDs, codes, IDs)
  - Behavior: 45% smaller
  - Timetable: 26% smaller  
  - Lessons History: 14% smaller
  
- 🎯 **Smart limiting**: Binary search finds optimal item count to fit 14KB target
  
- ⚙️ **Configurable**: New option `max_items_in_attributes` (10-500, default: 100)
  - Settings → Devices & Services → Mashov → Configure
  
- 📊 **Transparent**: New attributes show what's stored
  - `total_items`: All available items
  - `stored_items`: Items in attributes
  - Full data always in `coordinator.data`

### Compatibility
✅ **100% backward compatible** with all cards and blueprints
- All required fields preserved
- No breaking changes

### Testing
Please test with your real Mashov data and report any issues!

---
**Full Changelog**: https://github.com/NirBY/ha-mashov/blob/main/CHANGELOG.md

