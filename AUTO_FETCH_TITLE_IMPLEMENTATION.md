# Auto-Fetch Title Feature - Implementation Summary

## Overview
Added automatic title fetching from Confluence pages and Jira issues when users enter a URL. The name field auto-populates with the fetched title, but remains fully editable by the user.

## What Was Implemented

### Backend Changes

#### 1. New API Endpoint (`backend/app.py`)
- **GET `/api/fetch-title?url={url}`**
  - Accepts a Confluence page URL or Jira issue URL as query parameter
  - Returns the page title or issue summary
  - Reuses existing `fetch_confluence_page_markdown` and `fetch_jira_issue_markdown` functions
  - Returns error message if credentials are missing or fetch fails
  - Lightweight endpoint - only fetches title, not full content

#### 2. New Model (`backend/models.py`)
- **`FetchTitleResponse`**: Response model with `title` and optional `error` fields

### Frontend Changes

#### 1. Updated Types (`frontend/src/types.ts`)
- Added `FetchTitleResponse` interface

#### 2. Enhanced Estimation Form (`frontend/src/components/EstimationForm.tsx`)
- **Auto-fetch functionality**:
  - Triggers when user enters/changes a URL
  - Uses 500ms debounce to avoid excessive API calls
  - Shows loading spinner in name field while fetching
  - Only populates name field if it's currently empty
  - Name field remains fully editable after auto-population
  
- **State management**:
  - `fetchingTitle`: Tracks loading state per item
  - `debounceTimers`: Ref to store debounce timers for cleanup
  
- **UX features**:
  - Loader icon appears in name field during fetch
  - Name field temporarily disabled while fetching
  - No auto-population if user already entered a name
  - Timers cleaned up on component unmount

## User Flow

1. User enters a Confluence or Jira URL in the URL field
2. After 500ms of no typing (debounce), system fetches the title
3. Loading spinner appears in the name field
4. Title auto-populates in the name field (if empty)
5. User can edit the name at any time
6. Process repeats for each URL field

## Key Features

- ✅ Automatic title fetching from Confluence and Jira
- ✅ 500ms debounce to avoid excessive API calls
- ✅ Loading indicator during fetch
- ✅ Name field remains editable
- ✅ Only populates if name field is empty
- ✅ Proper cleanup of timers
- ✅ Error handling for failed fetches
- ✅ Works with both Confluence pages and Jira issues

## Technical Details

### Debouncing
- Uses `setTimeout` with 500ms delay
- Clears previous timer when URL changes again
- Prevents API spam while user is typing
- Timers stored in ref for proper cleanup

### Smart Population
- Only auto-fills if name field is empty
- Preserves user's manual edits
- Silent failure (no error popups) if fetch fails

### Performance
- Lightweight API call (only fetches title, not full content)
- Parallel requests for multiple URL fields
- No blocking of other form interactions

## Error Handling

- **Missing credentials**: Returns empty title silently
- **Invalid URL**: Returns empty title silently
- **Network errors**: Logged to console, no user disruption
- **Invalid page/issue**: Returns empty title silently

All errors are handled gracefully without disrupting the user experience.

## Benefits

1. **Reduced manual typing**: Users don't need to copy/paste titles
2. **Consistency**: Page/issue titles match exactly
3. **Speed**: Faster form completion
4. **Flexibility**: Users can still edit or override the auto-populated name
5. **Better UX**: Clear visual feedback with loading indicator

## Future Enhancements (Not Implemented)

- Cache fetched titles to avoid re-fetching same URLs
- Show error tooltip if fetch fails
- Add "Fetch Title" button as alternative to auto-fetch
- Support for other URL types beyond Confluence/Jira

