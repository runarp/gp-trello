# Trello Round-Trip Sync Roadmap

## Overview

This document outlines the specification for Phase 2 of the Trello sync project: enabling **round-trip synchronization** where changes made to local markdown files can be pushed back to Trello. This phase focuses on two primary operations:

1. **Adding comments** to Trello cards from local markdown files
2. **Completing/uncompleting checklist items** in Trello cards from local markdown files

## Goals

- Enable bidirectional sync: Trello → Local (existing) and Local → Trello (new)
- Support adding comments to cards via markdown file edits
- Support updating checklist item states via markdown file edits
- Maintain data integrity and prevent conflicts
- Provide clear mechanisms for triggering updates
- Consider webhook-based real-time sync for future phases

## Current State

### Existing Functionality (Phase 1)
- ✅ One-way sync: Trello → Local markdown files
- ✅ Card format with YAML frontmatter and markdown body
- ✅ Support for descriptions, checklists, attachments, comments
- ✅ Incremental sync based on modification timestamps
- ✅ MCP server integration for Trello API access

### Card Format (Current)
```markdown
---
trello_board_card_id: "68f804be4dbc3c3da44bb046"
board: "GP Family Office"
url: "https://trello.com/c/xsKdq6ZO/1621-repair-desk"
workspace: "GP Family Office Workspace"
created: null
updated: "2025-11-04T04:57:27.464Z"
list: "Current Tasks"
labels: []
members: ["Myvi Somodio"]
due-date: null
attachments-count: 1
comments-count: 2
---

# Card Title

## Description
...

## Checklist: Task Name
- [x] Completed item
- [ ] Incomplete item

## Comments
#### Comment by Author Name
**Date:** Nov 4, 2025, 04:57 AM

Comment text here
---
```

## Phase 2 Requirements

### 1. Card Format Enhancements

#### 1.1 Frontmatter Additions

**Required Fields:**
- `trello_board_card_id` (existing) - **Critical**: Must be present for round-trip
- `trello_checklist_ids` (new) - Mapping of checklist names to Trello checklist IDs
- `trello_checkitem_ids` (new) - Mapping of checkitem names to Trello checkitem IDs
- `last_synced` (new) - Timestamp of last successful sync (local → Trello)
- `sync_status` (new) - Status: `synced`, `pending`, `conflict`, `error`

**Optional Fields:**
- `trello_list_id` - List ID for potential list movement operations
- `trello_board_id` - Board ID for validation

**Format:**
```yaml
---
trello_board_card_id: "68f804be4dbc3c3da44bb046"
trello_checklist_ids:
  "Task Name": "checklist_id_123"
  "Pre-launch Tasks": "checklist_id_456"
trello_checkitem_ids:
  "Task Name":
    "Completed item": "checkitem_id_789"
    "Incomplete item": "checkitem_id_012"
  "Pre-launch Tasks":
    "Design mockups": "checkitem_id_345"
last_synced: "2025-01-20T10:30:00Z"
sync_status: "synced"
---
```

#### 1.2 Comment Format Enhancements

**Current Format:**
```markdown
## Comments

#### Comment by Author Name
**Date:** Nov 4, 2025, 04:57 AM

Comment text here
---
```

**Enhanced Format (for new comments):**
```markdown
## Comments

#### Comment by Author Name
**Date:** Nov 4, 2025, 04:57 AM

Comment text here
---

#### Comment by [Your Name]
**Date:** [Auto-generated on sync]
**Status:** pending

New comment text to be synced to Trello
---
```

**Alternative: Separate Section for Pending Comments**
```markdown
## Pending Comments

#### Comment by [Your Name]
**Date:** [Auto-generated on sync]

New comment text to be synced to Trello
---

## Comments

#### Comment by Author Name
**Date:** Nov 4, 2025, 04:57 AM

Comment text here
---
```

**Recommendation:** Use a **special marker** in the comment section to identify pending comments:
- Comments with `**Status:** pending` or in a `## Pending Comments` section
- Comments without a Trello comment ID in frontmatter
- Comments with timestamps in the future or marked as "new"

#### 1.3 Checklist Format Enhancements

**Current Format:**
```markdown
## Checklist: Task Name

- [x] Completed item
- [ ] Incomplete item
```

**Enhanced Format:**
```markdown
## Checklist: Task Name
<!-- trello_checklist_id: checklist_id_123 -->

- [x] Completed item <!-- trello_checkitem_id: checkitem_id_789 -->
- [ ] Incomplete item <!-- trello_checkitem_id: checkitem_id_012 -->
```

**Alternative: Use Frontmatter Only**
- Store all IDs in frontmatter (recommended)
- Keep markdown body clean and readable
- Use checklist name + item name as keys

**Recommendation:** Store IDs in frontmatter, keep markdown clean. Use checklist name and item name as composite keys.

### 2. Trigger Mechanisms

#### 2.1 Manual CLI Commands

**Command: `push`**
```bash
# Push all pending changes for a board
trello-sync push <board-id>

# Push changes for a specific card
trello-sync push-card <card-id> --file path/to/card.md

# Push only comments
trello-sync push <board-id> --comments-only

# Push only checklists
trello-sync push <board-id> --checklists-only

# Dry run to see what would be pushed
trello-sync push <board-id> --dry-run
```

**Command: `status`**
```bash
# Show sync status for all cards
trello-sync status

# Show status for a specific board
trello-sync status <board-id>

# Show status for a specific card
trello-sync status --file path/to/card.md
```

#### 2.2 File Watcher Mode

**Command: `watch`**
```bash
# Watch for file changes and auto-push
trello-sync watch <board-id>

# Watch with debounce (wait 5 seconds after last change)
trello-sync watch <board-id> --debounce 5

# Watch with filters
trello-sync watch <board-id> --comments-only
```

**Implementation Notes:**
- Use file system watchers (e.g., `watchdog` in Python)
- Debounce rapid changes (default: 3-5 seconds)
- Track file modification times
- Only push files that have changed since last sync

#### 2.3 Git Hooks Integration

**Pre-commit Hook:**
```bash
#!/bin/sh
# .git/hooks/pre-commit

# Check for pending Trello changes
trello-sync status --exit-on-pending

# If pending changes exist, prompt user
# Optionally auto-push before commit
```

**Post-commit Hook:**
```bash
#!/bin/sh
# .git/hooks/post-commit

# Optionally push changes after commit
trello-sync push --auto
```

#### 2.4 Markdown File Markers

**Special Markers in Files:**
```markdown
<!-- TRELLO_SYNC: pending -->
<!-- TRELLO_SYNC: auto-push -->
```

Files with these markers can be automatically detected and processed.

### 3. Detection Logic

#### 3.1 Comment Detection

**New Comments:**
1. Parse markdown file for comment sections
2. Compare with last synced state (stored in frontmatter or separate state file)
3. Identify comments that:
   - Don't have a corresponding Trello comment ID
   - Are in a "Pending Comments" section
   - Have `**Status:** pending` marker
   - Were added after `last_synced` timestamp

**Comment Matching:**
- Match by author name + timestamp (fuzzy matching for time differences)
- Match by content hash (for exact duplicates)
- Store Trello comment IDs in frontmatter or HTML comments

**Format for Storing Comment IDs:**
```yaml
trello_comment_ids:
  - id: "comment_id_123"
    author: "Author Name"
    date: "2025-11-04T04:57:27.464Z"
    content_hash: "abc123..."
```

#### 3.2 Checklist Detection

**State Changes:**
1. Parse markdown checklists
2. Compare checkbox states with last synced state
3. Identify items that changed from `[ ]` to `[x]` or vice versa
4. Use checklist name + item name to find corresponding Trello IDs

**Matching Logic:**
- Use checklist name from markdown heading
- Use item text (normalized: trim, lowercase comparison)
- Match against `trello_checkitem_ids` in frontmatter

**Edge Cases:**
- Checklist items renamed in markdown (match by ID, update name in Trello?)
- Checklist items reordered (match by ID, preserve order?)
- New checklist items added (create in Trello or ignore?)

### 4. Sync Process

#### 4.1 Comment Sync Workflow

```
1. Parse markdown file
2. Extract comments section
3. Compare with last synced state
4. Identify new/pending comments
5. For each new comment:
   a. Extract author (from frontmatter or default)
   b. Extract comment text
   c. Call mcp_trello-admin_add_comment(cardId, text)
   d. Store returned comment ID
6. Update frontmatter with new comment IDs
7. Update last_synced timestamp
8. Update sync_status
```

#### 4.2 Checklist Sync Workflow

```
1. Parse markdown file
2. Extract all checklists
3. For each checklist:
   a. Get checklist ID from frontmatter
   b. For each checkitem:
      i. Get checkitem ID from frontmatter
      ii. Compare current state with last synced state
      iii. If changed:
          - Call mcp_trello-admin_update_checkitem_state_on_card(
              cardId, checkItemId, newState
            )
          - Update last_synced timestamp
4. Update sync_status
```

#### 4.3 Conflict Detection

**Conflicts Occur When:**
- Local file was modified after last sync
- Trello card was modified after last sync
- Both have changes that conflict

**Conflict Resolution:**
1. **Last Write Wins** (default): Trello changes overwrite local
2. **Manual Resolution**: Prompt user to choose
3. **Merge Strategy**: Attempt to merge non-conflicting changes
4. **Three-way Merge**: Compare local, Trello, and common ancestor

**Conflict Markers:**
```markdown
## Comments

#### Comment by Author
**Date:** Nov 4, 2025
**Status:** conflict

<!-- CONFLICT: This comment exists in Trello but not in local file -->
Comment text from Trello
---

#### Comment by [Your Name]
**Date:** Nov 5, 2025
**Status:** conflict

<!-- CONFLICT: This comment exists locally but not in Trello -->
Local comment text
---
```

### 5. State Management

#### 5.1 Sync State File

**Location:** `.trello-sync/card-states/{card-id}.json`

**Format:**
```json
{
  "cardId": "68f804be4dbc3c3da44bb046",
  "filePath": "data/gp-family-office/current-tasks/repair-desk.md",
  "lastLocalSync": "2025-01-20T10:30:00Z",
  "lastTrelloSync": "2025-01-20T10:25:00Z",
  "lastLocalModification": "2025-01-20T10:28:00Z",
  "lastTrelloModification": "2025-01-20T10:25:00Z",
  "syncStatus": "synced",
  "pendingChanges": {
    "comments": [],
    "checklists": []
  },
  "commentIds": {
    "comment_hash_1": "trello_comment_id_123"
  },
  "checklistState": {
    "Task Name": {
      "Completed item": "complete",
      "Incomplete item": "incomplete"
    }
  }
}
```

#### 5.2 Frontmatter vs. State File

**Recommendation:** Hybrid approach
- **Frontmatter**: Store essential IDs for readability and portability
- **State File**: Store detailed sync state, timestamps, hashes
- **Sync Process**: Update both during sync

### 6. Webhook Support (Future Phase)

#### 6.1 Webhook Architecture

**Components:**
1. **Webhook Receiver**: HTTP server to receive Trello webhooks
2. **Webhook Processor**: Process webhook events and update local files
3. **Webhook Registration**: Register webhooks with Trello API

**Trello Webhook Events:**
- `commentCard` - New comment added
- `updateCard` - Card updated
- `updateCheckItemStateOnCard` - Checklist item state changed
- `addAttachmentToCard` - Attachment added
- `updateList` - Card moved to different list

#### 6.2 Webhook Implementation Considerations

**Challenges:**
1. **Webhook URL**: Need publicly accessible URL (ngrok, cloud service, etc.)
2. **Authentication**: Verify webhook authenticity
3. **Idempotency**: Handle duplicate webhook deliveries
4. **Ordering**: Ensure events are processed in order
5. **Conflict Resolution**: Handle simultaneous local and webhook changes

**Implementation Options:**

**Option A: Full Webhook Server**
- Run a background service
- Receive and process all webhook events
- Update local files in real-time
- Most complex but most responsive

**Option B: Polling with Webhook Hints**
- Use webhooks to trigger polling
- Webhook just signals "something changed"
- Poll API to get full details
- Simpler, less real-time

**Option C: Hybrid Approach**
- Webhooks for high-priority events (comments, checklist changes)
- Polling for other changes
- Best of both worlds

**Recommendation for Phase 2:** Defer webhook implementation to Phase 3. Focus on manual/CLI-based sync first.

#### 6.3 Webhook Registration

**Trello API Endpoints:**
- `POST /1/webhooks` - Create webhook
- `GET /1/webhooks/{id}` - Get webhook details
- `PUT /1/webhooks/{id}` - Update webhook
- `DELETE /1/webhooks/{id}` - Delete webhook

**Webhook Model:**
```json
{
  "idModel": "board_id_or_card_id",
  "callbackURL": "https://your-server.com/webhooks/trello",
  "description": "GP Trello Sync Webhook",
  "active": true
}
```

### 7. Implementation Plan

#### Phase 2.1: Core Round-Trip Infrastructure
- [ ] Extend card format with required frontmatter fields
- [ ] Implement state management (state files)
- [ ] Add comment detection and parsing
- [ ] Add checklist state detection
- [ ] Implement conflict detection logic

#### Phase 2.2: CLI Commands
- [ ] Implement `push` command
- [ ] Implement `status` command
- [ ] Add dry-run support
- [ ] Add filtering options (comments-only, checklists-only)

#### Phase 2.3: MCP Integration
- [ ] Integrate `mcp_trello-admin_add_comment`
- [ ] Integrate `mcp_trello-admin_update_checkitem_state_on_card`
- [ ] Add error handling and retry logic
- [ ] Add rate limiting

#### Phase 2.4: File Watcher (Optional)
- [ ] Implement file system watcher
- [ ] Add debouncing
- [ ] Add filtering options

#### Phase 2.5: Testing & Documentation
- [ ] Unit tests for detection logic
- [ ] Integration tests for sync workflows
- [ ] Update documentation
- [ ] Add examples and use cases

#### Phase 3: Webhook Support (Future)
- [ ] Webhook receiver implementation
- [ ] Webhook registration CLI
- [ ] Real-time sync processing
- [ ] Conflict resolution for webhook events

### 8. Gotchas and Edge Cases

#### 8.1 Comment Gotchas

**Duplicate Comments:**
- Problem: Same comment added multiple times
- Solution: Check content hash before adding

**Comment Formatting:**
- Problem: Markdown formatting in comments may not match Trello
- Solution: Preserve original formatting, normalize on sync

**Comment Author:**
- Problem: Local comments don't have author until synced
- Solution: Use default author from config or frontmatter

**Comment Threading:**
- Problem: Trello supports threaded comments, markdown doesn't
- Solution: Use blockquotes for replies, store thread IDs

#### 8.2 Checklist Gotchas

**Checklist Item Renaming:**
- Problem: Item renamed in markdown, how to match with Trello?
- Solution: Match by ID first, then by name, update Trello if ID matches

**Checklist Item Reordering:**
- Problem: Items reordered in markdown
- Solution: Preserve Trello order, ignore markdown order (or update Trello)

**New Checklist Items:**
- Problem: New items added in markdown
- Solution: Option 1: Ignore (only sync existing items). Option 2: Create in Trello (requires checklist ID)

**Checklist Deletion:**
- Problem: Checklist removed from markdown
- Solution: Don't delete in Trello (safety), just mark as "not in file"

**Multiple Checklists with Same Name:**
- Problem: Ambiguous checklist matching
- Solution: Use checklist ID from frontmatter, require unique names

#### 8.3 Sync Gotchas

**File Moved/Renamed:**
- Problem: Card file moved to different location
- Solution: Track by card ID, not file path. Update state file path.

**Card Deleted in Trello:**
- Problem: Card no longer exists in Trello
- Solution: Detect on sync, mark file as "orphaned", don't attempt push

**Card Moved to Different List:**
- Problem: Card moved in Trello, file still in old location
- Solution: Update file location on next pull, or keep in old location (user choice)

**Concurrent Edits:**
- Problem: File edited while sync in progress
- Solution: Lock file during sync, or detect and retry

**Rate Limiting:**
- Problem: Trello API rate limits (300 requests per 10 seconds)
- Solution: Implement rate limiting, queue requests, batch operations

**Network Failures:**
- Problem: API call fails mid-sync
- Solution: Retry with exponential backoff, partial state updates

#### 8.4 Format Gotchas

**YAML Parsing:**
- Problem: Invalid YAML in frontmatter breaks parsing
- Solution: Validate YAML, provide clear error messages, auto-fix common issues

**Markdown Parsing:**
- Problem: Non-standard markdown breaks parsing
- Solution: Use robust parser, handle edge cases gracefully

**Encoding Issues:**
- Problem: Special characters in comments/checklists
- Solution: Use UTF-8 encoding, escape special characters

**Line Ending Differences:**
- Problem: Windows vs. Unix line endings
- Solution: Normalize to Unix (LF) or detect and preserve

### 9. Security Considerations

#### 9.1 API Credentials
- Store credentials securely (environment variables, not in code)
- Use read-write tokens (not just read-only)
- Rotate tokens periodically

#### 9.2 File Permissions
- Ensure state files are not world-readable
- Protect sensitive information in frontmatter

#### 9.3 Webhook Security (Future)
- Verify webhook signatures
- Use HTTPS for webhook endpoints
- Implement authentication/authorization

### 10. Performance Considerations

#### 10.1 Batch Operations
- Batch multiple comment additions
- Batch multiple checklist updates
- Reduce API calls

#### 10.2 Caching
- Cache Trello card states
- Cache checklist/checkitem IDs
- Invalidate cache on sync

#### 10.3 Incremental Processing
- Only process changed files
- Only process changed sections (comments, checklists)
- Skip unchanged cards

### 11. User Experience

#### 11.1 Clear Feedback
- Show what will be pushed before pushing
- Show sync status clearly
- Provide error messages with actionable steps

#### 11.2 Undo/Redo
- Consider implementing undo for sync operations
- Log all sync operations
- Allow reverting changes

#### 11.3 Preview Mode
- Show diff before syncing
- Highlight pending changes
- Show conflicts clearly

### 12. Testing Strategy

#### 12.1 Unit Tests
- Comment detection logic
- Checklist state detection
- Conflict detection
- State file management

#### 12.2 Integration Tests
- Full sync workflows
- MCP API integration
- Error handling scenarios

#### 12.3 End-to-End Tests
- Complete round-trip scenarios
- Conflict resolution
- Concurrent operations

### 13. Migration Path

#### 13.1 Existing Cards
- Existing cards need to be updated with new frontmatter fields
- Run migration script to add IDs to frontmatter
- Update state files for all existing cards

#### 13.2 Backward Compatibility
- Support cards without new frontmatter fields (read-only)
- Gracefully handle missing IDs
- Provide migration tools

### 14. Documentation Updates

#### 14.1 User Guide
- How to add comments locally
- How to update checklists
- How to trigger sync
- How to resolve conflicts

#### 14.2 Developer Guide
- Architecture overview
- Extension points
- API documentation
- Contributing guidelines

#### 14.3 Rule Files
- Update `trello-structure.mdc` with new format
- Update `trello-sync.mdc` with round-trip workflow
- Add new rule file for round-trip operations

## Conclusion

This roadmap provides a comprehensive plan for implementing round-trip sync functionality. The phased approach allows for incremental development and testing, with webhook support deferred to a future phase for complexity management.

Key priorities:
1. **Reliability**: Robust conflict detection and resolution
2. **Usability**: Clear triggers and feedback
3. **Safety**: Don't lose data, handle errors gracefully
4. **Performance**: Efficient sync operations

The implementation should start with Phase 2.1 (core infrastructure) and Phase 2.2 (CLI commands) to provide immediate value, then expand with optional features like file watching and webhook support.

