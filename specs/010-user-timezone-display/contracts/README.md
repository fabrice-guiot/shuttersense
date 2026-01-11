# API Contracts: User Timezone Display

**Feature Branch**: `010-user-timezone-display`
**Date**: 2026-01-11

## No API Changes Required

This feature is **frontend-only** and requires no backend API changes.

### Existing API Behavior (Preserved)

All timestamp fields in API responses continue to be serialized as ISO 8601 strings in UTC:

```json
{
  "created_at": "2026-01-07T15:45:00",
  "updated_at": "2026-01-10T10:30:00"
}
```

The frontend handles all timezone conversion during display using the new centralized date formatting utility.

### Why No API Changes?

1. **UTC Storage is Correct**: Storing timestamps in UTC is the standard practice for APIs
2. **Client-Side Conversion is Better**: Each user sees times in their own timezone without server-side complexity
3. **No User Accounts Yet**: Without user accounts, there's no server-side timezone preference to apply
4. **Simpler Implementation**: Frontend-only changes have no deployment coordination requirements
