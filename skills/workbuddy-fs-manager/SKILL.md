---
name: workbuddy-fs-manager
description: >
  Cross-platform WorkBuddy file system management. Archive inactive workspace
  directories, sync the workbuddy.db database, and clean ghost task records
  from session jsonl files. Use when (1) WorkBuddy UI shows duplicate automation
  sessions or ghost tasks, (2) workspace directories need archiving after
  automation runs, (3) the workbuddy.db database has stale entries from deleted
  or archived workspaces, (4) user asks to clean up, archive, or organize
  WorkBuddy workspaces/sessions/tasks, (5) setting up a heartbeat automation
  for periodic cleanup, (6) user mentions "workbuddy cleanup", "workspace
  archive", "ghost tasks", "stale sessions", or "jsonl cleanup".
---

# WorkBuddy File System Manager

Cross-platform tool for managing WorkBuddy workspace directories, database
consistency, and session jsonl files. Three independent modules:

- **Archive** — Move inactive workspace dirs to an archive folder
- **DB Sync** — Fix stale entries in workbuddy.db
- **Task Clean** — Remove ghost TaskCreate/TaskUpdate/TaskList from jsonl

## Quick Start

Run the bundled script with all modules:

```bash
python scripts/workbuddy_fs_manager.py
```

Dry-run to preview changes:

```bash
python scripts/workbuddy_fs_manager.py --dry-run
```

Check environment status:

```bash
python scripts/workbuddy_fs_manager.py --status
```

## Module Details

### 1. Workspace Archiver (`--archive`)

Scans the WorkBuddy root directory for inactive workspace directories and moves
them to an `archive/` subfolder.

**Default archive patterns** (directories matching any of these are archived):

| Pattern | Matches |
|---------|---------|
| `automation-*` | `automation-claw-2026-05-12-task-25` |
| `202*-` | `2026-05-12-my-project` |
| `*-task-*` | `anything-task-1` |

**Protected directories** (never archived):
- `archive/` — the archive folder itself
- Current working directory — wherever the agent is running
- **Active session directories** — any directory used by a `working` session (sub-agents are protected)
- Directories specified via `--keep` flag

**Custom patterns:**

```bash
# Add extra pattern
python scripts/workbuddy_fs_manager.py --archive --pattern "temp-*"

# Protect additional directories
python scripts/workbuddy_fs_manager.py --archive --keep my-project --keep important
```

### 2. Database Sync (`--db`)

Synchronizes `~/.workbuddy/workbuddy.db` with the actual filesystem:

- Removes `workspaces` entries pointing to deleted directories
- Fixes `sessions.cwd` that reference non-existent paths (redirects to primary workspace)
- Deletes `automation_runs` for archived workspaces
- Archives duplicate automation sessions (keeps latest per title, marks rest as `archived`)

This runs automatically after archiving. Can also run standalone:

```bash
python scripts/workbuddy_fs_manager.py --db
```

### 3. Task Record Cleaner (`--tasks`)

Removes ghost task entries from session jsonl files. WorkBuddy UI renders tasks
from `TaskCreate` function_call lines in the jsonl history. Even when `TaskList`
returns empty, old TaskCreate entries persist in the UI.

**Scope options:**

```bash
# Clean all jsonl files
python scripts/workbuddy_fs_manager.py --tasks

# Clean a specific session
python scripts/workbuddy_fs_manager.py --tasks --session <uuid>
```

**What gets removed:** Lines where `type` is `function_call` or
`function_call_result` AND `name` is in `{TaskCreate, TaskUpdate, TaskList}`.

**Warning:** This is irreversible. Task history parameters are permanently deleted.
Active session jsonl files are automatically skipped to avoid corrupting
running conversations.

## Setting Up a Heartbeat Automation

Create a recurring automation to run cleanup periodically:

- **Schedule:** Every 6 hours (`FREQ=HOURLY;INTERVAL=6`)
- **Prompt:** `Run the workbuddy-fs-manager skill: execute scripts/workbuddy_fs_manager.py`
- **Workspace:** Your primary WorkBuddy workspace directory

## Key Paths (auto-detected)

| Item | Default Location |
|------|-----------------|
| WorkBuddy root | `~/WorkBuddy` |
| Database | `~/.workbuddy/workbuddy.db` |
| Projects dir | `~/.workbuddy/projects/` |
| Archive dir | `~/WorkBuddy/archive/` |

## CLI Reference

```
python scripts/workbuddy_fs_manager.py [OPTIONS]

Options:
  --archive       Archive inactive workspaces only
  --tasks         Clean ghost task records only
  --db            Sync database only
  --session UUID  Clean tasks for specific session
  --pattern GLOB  Extra glob pattern for archive matching
  --keep NAME     Protect directory from archival (repeatable)
  --dry-run       Preview without making changes
  --status        Print environment status and exit

No flags = run all modules.
```
