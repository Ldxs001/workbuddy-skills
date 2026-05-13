#!/usr/bin/env python3
"""
WorkBuddy File System Manager
Cross-platform workspace and session management for WorkBuddy.

Usage:
  python workbuddy_fs_manager.py                  # Run all modules
  python workbuddy_fs_manager.py --archive        # Archive inactive workspaces only
  python workbuddy_fs_manager.py --tasks          # Clean ghost task records only
  python workbuddy_fs_manager.py --db             # Sync database only
  python workbuddy_fs_manager.py --tasks --session <uuid>   # Clean specific session
  python workbuddy_fs_manager.py --dry-run        # Preview without making changes

Modules:
  A) Workspace Archiver  — Archive inactive workspace dirs, sync DB
  B) Task Record Cleaner — Remove ghost TaskXxx entries from jsonl
  C) Database Sync       — Fix stale workspace/session/automation records
"""
import os
import sys
import json
import time
import shutil
import sqlite3
import glob
import argparse
import platform

# ═══════════════════════════════════════════════════════════
# Auto-detect environment (cross-platform)
# ═══════════════════════════════════════════════════════════

def detect_environment():
    """Detect WorkBuddy root, DB path, and projects dir automatically."""
    home = os.path.expanduser("~")

    # WorkBuddy root: ~/WorkBuddy (or ~/workbuddy)
    candidates = [
        os.path.join(home, "WorkBuddy"),
        os.path.join(home, "workbuddy"),
    ]
    wb_root = None
    for c in candidates:
        if os.path.isdir(c):
            wb_root = c
            break

    # DB path: ~/.workbuddy/workbuddy.db
    db_candidates = [
        os.path.join(home, ".workbuddy", "workbuddy.db"),
    ]
    db_path = None
    for c in db_candidates:
        if os.path.isfile(c):
            db_path = c
            break

    # Projects dir: ~/.workbuddy/projects/
    projects_dir = os.path.join(home, ".workbuddy", "projects")

    # Current workspace (cwd that is inside WorkBuddy)
    cwd = os.path.abspath(os.getcwd())

    return {
        "wb_root": wb_root,
        "db_path": db_path,
        "projects_dir": projects_dir,
        "cwd": cwd,
        "home": home,
        "os": platform.system(),
        "user": os.getlogin() if hasattr(os, "getlogin") else os.environ.get("USER", "unknown"),
    }


ENV = detect_environment()

# Default archive patterns for automation-generated workspaces
DEFAULT_ARCHIVE_PATTERNS = [
    "automation-*",           # automation-claw-*, automation-*
    "202*-",                  # Date-prefixed: 2026-05-12-*
    "*-task-*",               # Task workspaces: anything-task-*
]

# Tool names that produce ghost task entries in jsonl
TASK_TOOL_NAMES = {"TaskCreate", "TaskUpdate", "TaskList"}

def get_active_cwds():
    """Query DB for cwd of sessions with status 'working'. Return set of paths."""
    db_path = ENV.get("db_path")
    if not db_path or not os.path.isfile(db_path):
        return set()
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT DISTINCT cwd FROM sessions WHERE status = 'working' AND cwd IS NOT NULL"
        ).fetchall()
        conn.close()
        return {r[0] for r in rows if r[0]}
    except (sqlite3.Error, OSError):
        return set()


def get_active_session_ids():
    """Query DB for session IDs with status 'working'. Return set of UUIDs."""
    db_path = ENV.get("db_path")
    if not db_path or not os.path.isfile(db_path):
        return set()
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT id FROM sessions WHERE status = 'working'"
        ).fetchall()
        conn.close()
        return {r[0] for r in rows}
    except (sqlite3.Error, OSError):
        return set()


# ═══════════════════════════════════════════════════════════
# Utility
# ═══════════════════════════════════════════════════════════

def matches_patterns(name, patterns):
    """Check if a directory name matches any of the given glob patterns."""
    import fnmatch
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def log(msg):
    print(f"  {msg}")


# ═══════════════════════════════════════════════════════════
# Module A: Workspace Archiver
# ═══════════════════════════════════════════════════════════

def archive_workspaces(archive_dir_name="archive", extra_patterns=None,
                       keep_dirs=None, dry_run=False):
    """
    Archive inactive workspace directories and sync database.

    Args:
        archive_dir_name: Name of archive subdirectory (default: 'archive')
        extra_patterns: Additional glob patterns for dirs to archive
        keep_dirs: Set of directory names to never archive (in addition to cwd)
        dry_run: If True, only preview what would be done
    """
    wb_root = ENV["wb_root"]
    if not wb_root:
        print("[Archive] ERROR: Cannot detect WorkBuddy root directory.")
        return

    archive_dir = os.path.join(wb_root, archive_dir_name)
    patterns = list(DEFAULT_ARCHIVE_PATTERNS)
    if extra_patterns:
        patterns.extend(extra_patterns)

    if keep_dirs is None:
        keep_dirs = set()
    keep_dirs.add(archive_dir_name)

    # Detect primary workspace: the one with the most recent .workbuddy/ dir
    # or the one matching cwd
    primary_dir = os.path.basename(ENV["cwd"])
    if ENV["cwd"].startswith(wb_root + os.sep):
        keep_dirs.add(primary_dir)

    os.makedirs(archive_dir, exist_ok=True)
    to_archive = []

    print(f"\n[Archive] Scanning: {wb_root}")
    print(f"[Archive] Patterns: {patterns}")
    print(f"[Archive] Keep dirs: {keep_dirs}")
    print(f"[Archive] Dry run: {dry_run}")

    try:
        entries = os.listdir(wb_root)
    except PermissionError as e:
        print(f"[Archive] ERROR: Cannot list directory: {e}")
        return

    # Protect active session directories (sub-agents may be using them)
    active_cwds = get_active_cwds()

    for name in sorted(entries):
        full = os.path.join(wb_root, name)
        if not os.path.isdir(full):
            continue
        if name in keep_dirs:
            continue
        # Skip current cwd regardless of name
        if os.path.abspath(full) == ENV["cwd"]:
            log(f"SKIP (current cwd): {name}")
            continue
        # Skip directories used by active (working) sessions
        if os.path.abspath(full) in active_cwds or full in active_cwds:
            log(f"SKIP (active session): {name}")
            continue
        if matches_patterns(name, patterns):
            to_archive.append((name, full))
            log(f"TO_ARCHIVE: {name}")

    if not to_archive:
        print("[Archive] Nothing to archive.")
        return

    moved = 0
    skipped = 0
    for name, full in to_archive:
        dst = os.path.join(archive_dir, name)
        if os.path.exists(dst):
            dst += "_" + time.strftime("%Y%m%d%H%M%S")
        if dry_run:
            log(f"DRY-RUN WOULD MOVE: {name} -> {archive_dir_name}/")
            moved += 1
        else:
            try:
                shutil.move(full, dst)
                log(f"MOVED: {name} -> {archive_dir_name}/")
                moved += 1
            except (PermissionError, OSError) as e:
                log(f"SKIP (locked/in-use): {name} - {e}")
                skipped += 1

    print(f"[Archive] Moved: {moved}, Skipped: {skipped}")

    # Sync database after archiving
    if not dry_run and moved > 0:
        sync_database(archived_paths=[f for _, f in to_archive],
                      archive_dir=archive_dir)

    print("[Archive] Done.")


# ═══════════════════════════════════════════════════════════
# Module B: Task Record Cleaner
# ═══════════════════════════════════════════════════════════

def cleanup_tasks(session_id=None, workspace_pattern=None, dry_run=False):
    """
    Remove ghost TaskCreate/TaskUpdate/TaskList entries from jsonl files.

    These entries cause the UI to display stale tasks even after TaskList
    returns empty. Removing the jsonl lines clears the ghost entries.

    Args:
        session_id: Clean a specific session (UUID)
        workspace_pattern: Clean all sessions under a workspace dir pattern
        dry_run: If True, only count what would be removed
    """
    projects_dir = ENV["projects_dir"]
    if not os.path.isdir(projects_dir):
        print(f"[Tasks] ERROR: Projects directory not found: {projects_dir}")
        return

    jsonl_files = []

    if session_id:
        for root, dirs, files in os.walk(projects_dir):
            if session_id + ".jsonl" in files:
                jsonl_files.append(os.path.join(root, session_id + ".jsonl"))
        if not jsonl_files:
            print(f"[Tasks] No jsonl found for session: {session_id}")
            return
    elif workspace_pattern:
        ws_dir = os.path.join(projects_dir, workspace_pattern)
        if os.path.isdir(ws_dir):
            jsonl_files = glob.glob(os.path.join(ws_dir, "*.jsonl"))
    else:
        jsonl_files = glob.glob(os.path.join(projects_dir, "**/*.jsonl"),
                                recursive=True)

    total_removed = 0
    total_files = 0
    print(f"\n[Tasks] Scanning {len(jsonl_files)} jsonl files...")
    print(f"[Tasks] Dry run: {dry_run}")

    # Get active session IDs to skip
    active_ids = get_active_session_ids()
    skipped_active = 0

    for fpath in jsonl_files:
        # Skip jsonl files belonging to active sessions
        fname = os.path.splitext(os.path.basename(fpath))[0]
        if fname in active_ids:
            log(f"SKIP (active session): {os.path.basename(fpath)}")
            skipped_active += 1
            continue

        lines_out = []
        removed = 0

        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip():
                    lines_out.append(line)
                    continue
                try:
                    obj = json.loads(line)
                    if (obj.get("type") == "function_call"
                            and obj.get("name") in TASK_TOOL_NAMES):
                        removed += 1
                        continue
                    if (obj.get("type") == "function_call_result"
                            and obj.get("name") in TASK_TOOL_NAMES):
                        removed += 1
                        continue
                    lines_out.append(json.dumps(obj, ensure_ascii=False))
                except json.JSONDecodeError:
                    lines_out.append(line)

        if removed > 0:
            if dry_run:
                log(f"{os.path.basename(fpath)}: WOULD remove {removed} lines")
            else:
                with open(fpath, "w", encoding="utf-8") as f:
                    for line in lines_out:
                        f.write(line + "\n")
                log(f"{os.path.basename(fpath)}: removed {removed} lines")
            total_removed += removed
            total_files += 1

    action = "Would remove" if dry_run else "Removed"
    print(f"[Tasks] {action}: {total_removed} lines across {total_files} files")
    if skipped_active:
        print(f"[Tasks] Skipped {skipped_active} active session files")
    print("[Tasks] Done.")


# ═══════════════════════════════════════════════════════════
# Module C: Database Sync
# ═══════════════════════════════════════════════════════════

def sync_database(archived_paths=None, archive_dir=None, dry_run=False):
    """
    Synchronize WorkBuddy database with the actual filesystem state.

    - Remove workspace entries whose directories no longer exist
    - Fix session cwd pointing to deleted directories
    - Clean stale automation_runs for archived workspaces
    - Archive old automation heartbeat sessions (keep latest only)

    Args:
        archived_paths: List of full paths that were just archived
        archive_dir: Path to archive directory
        dry_run: If True, only preview changes
    """
    db_path = ENV["db_path"]
    if not db_path:
        print("[DB] ERROR: Database not found.")
        return

    print(f"\n[DB] Syncing: {db_path}")
    print(f"[DB] Dry run: {dry_run}")

    wb_root = ENV["wb_root"]

    if dry_run:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(db_path)

    try:
        conn.row_factory = sqlite3.Row

        # ── 1. Clean stale workspaces ──
        changes = 0
        try:
            for row in conn.execute("SELECT rowid, path FROM workspaces").fetchall():
                if not os.path.exists(row["path"]):
                    if dry_run:
                        log(f"DRY-RUN: would DELETE workspaces rowid={row['rowid']} path={row['path']}")
                    else:
                        conn.execute("DELETE FROM workspaces WHERE rowid = ?",
                                     (row["rowid"],))
                    changes += 1
        except sqlite3.OperationalError:
            pass  # Table might not exist
        if changes:
            action = "Would clean" if dry_run else "Cleaned"
            log(f"{action} {changes} stale workspace entries")

        # ── 2. Fix session cwd for deleted directories ──
        # Target: point orphaned sessions to the primary active workspace
        primary_cwd = ENV["cwd"] if ENV["cwd"].startswith(wb_root + os.sep) else wb_root

        session_updates = 0
        try:
            for row in conn.execute("SELECT rowid, cwd FROM sessions").fetchall():
                cwd_val = row["cwd"]
                if cwd_val and not os.path.exists(cwd_val):
                    if dry_run:
                        log(f"DRY-RUN: would UPDATE sessions rowid={row['rowid']} cwd -> {primary_cwd}")
                    else:
                        conn.execute("UPDATE sessions SET cwd = ? WHERE rowid = ?",
                                     (primary_cwd, row["rowid"]))
                    session_updates += 1
        except sqlite3.OperationalError:
            pass
        if session_updates:
            action = "Would fix" if dry_run else "Fixed"
            log(f"{action} {session_updates} orphaned session paths")

        # ── 3. Clean automation_runs for archived workspaces ──
        if archived_paths:
            for path in archived_paths:
                try:
                    cur = conn.execute(
                        "DELETE FROM automation_runs WHERE source_cwd = ?", (path,))
                    if cur.rowcount > 0:
                        if dry_run:
                            log(f"DRY-RUN: would DELETE {cur.rowcount} automation_runs for {os.path.basename(path)}")
                        else:
                            log(f"DELETE {cur.rowcount} automation_runs for {os.path.basename(path)}")
                except sqlite3.OperationalError:
                    pass

        # ── 4. Archive old heartbeat sessions (keep latest per title) ──
        try:
            # Find automation titles that have multiple completed sessions
            titles = conn.execute(
                "SELECT custom_title FROM sessions "
                "WHERE status = 'completed' AND custom_title IS NOT NULL "
                "GROUP BY custom_title HAVING COUNT(*) > 1"
            ).fetchall()

            for title_row in titles:
                title = title_row["custom_title"]
                rows = conn.execute(
                    "SELECT id FROM sessions "
                    "WHERE custom_title = ? AND status = 'completed' "
                    "ORDER BY created_at DESC",
                    (title,)
                ).fetchall()

                if len(rows) > 1:
                    old_ids = [r["id"] for r in rows[1:]]
                    ph = ",".join("?" * len(old_ids))
                    if dry_run:
                        log(f"DRY-RUN: would archive {len(old_ids)} old sessions for '{title}'")
                    else:
                        cur = conn.execute(
                            f"UPDATE sessions SET status = 'archived' WHERE id IN ({ph})",
                            old_ids)
                        if cur.rowcount > 0:
                            log(f"Archived {cur.rowcount} old sessions for '{title}'")
        except sqlite3.OperationalError:
            pass

        # ── 5. Clean automation_runs for non-existent source_cwd ──
        stale_runs = 0
        try:
            for row in conn.execute("SELECT rowid, source_cwd FROM automation_runs").fetchall():
                src = row["source_cwd"]
                if src and not os.path.exists(src):
                    if dry_run:
                        stale_runs += 1
                    else:
                        conn.execute("DELETE FROM automation_runs WHERE rowid = ?",
                                     (row["rowid"],))
                        stale_runs += 1
        except sqlite3.OperationalError:
            pass
        if stale_runs:
            action = "Would delete" if dry_run else "Deleted"
            log(f"{action} {stale_runs} stale automation_runs")

        if not dry_run:
            conn.commit()
        else:
            conn.rollback()

    finally:
        conn.close()

    print("[DB] Done.")


# ═══════════════════════════════════════════════════════════
# Status Report
# ═══════════════════════════════════════════════════════════

def print_status():
    """Print current WorkBuddy environment status."""
    print(f"\n{'='*50}")
    print(f"WorkBuddy File System Manager — Status")
    print(f"{'='*50}")
    print(f"  OS:            {ENV['os']}")
    print(f"  User:          {ENV['user']}")
    print(f"  Home:          {ENV['home']}")
    print(f"  WB Root:       {ENV['wb_root'] or 'NOT FOUND'}")
    print(f"  DB:            {ENV['db_path'] or 'NOT FOUND'}")
    print(f"  Projects Dir:  {ENV['projects_dir']}")
    print(f"  Current CWD:   {ENV['cwd']}")

    # Workspace directories
    wb_root = ENV["wb_root"]
    if wb_root and os.path.isdir(wb_root):
        dirs = [d for d in os.listdir(wb_root)
                if os.path.isdir(os.path.join(wb_root, d))]
        print(f"\n  Workspace directories ({len(dirs)}):")
        for d in sorted(dirs):
            size = _dir_size(os.path.join(wb_root, d))
            marker = " <-- current" if os.path.abspath(os.path.join(wb_root, d)) == ENV["cwd"] else ""
            print(f"    {d}/  ({_human_size(size)}){marker}")

    # DB stats
    db_path = ENV["db_path"]
    if db_path:
        conn = sqlite3.connect(db_path)
        try:
            for table in ["workspaces", "sessions", "automations",
                          "automation_runs", "automation_runtime_state"]:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    print(f"  DB.{table}: {count} rows")
                except sqlite3.OperationalError:
                    pass
        finally:
            conn.close()

    print(f"{'='*50}\n")


def _dir_size(path):
    """Recursively calculate directory size."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += _dir_size(entry.path)
    except (PermissionError, OSError):
        pass
    return total


def _human_size(size):
    """Convert bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="WorkBuddy File System Manager — "
                    "workspace archiving, task cleanup, and DB sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python workbuddy_fs_manager.py                    # Run all modules
  python workbuddy_fs_manager.py --archive          # Archive only
  python workbuddy_fs_manager.py --tasks            # Clean task records only
  python workbuddy_fs_manager.py --db               # Sync database only
  python workbuddy_fs_manager.py --tasks --session abc-123  # Specific session
  python workbuddy_fs_manager.py --dry-run          # Preview mode
  python workbuddy_fs_manager.py --status           # Show environment status
        """)

    parser.add_argument("--archive", action="store_true",
                        help="Run workspace archiver only")
    parser.add_argument("--tasks", action="store_true",
                        help="Run task record cleaner only")
    parser.add_argument("--db", action="store_true",
                        help="Run database sync only")
    parser.add_argument("--session", type=str, default=None,
                        help="Clean tasks for a specific session UUID")
    parser.add_argument("--pattern", type=str, default=None,
                        help="Extra glob pattern for archive matching")
    parser.add_argument("--keep", type=str, action="append", default=None,
                        help="Directory name to never archive (repeatable)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without executing")
    parser.add_argument("--status", action="store_true",
                        help="Print environment status and exit")

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    # If no module flag is set, run all
    run_all = not (args.archive or args.tasks or args.db)

    extra_patterns = [args.pattern] if args.pattern else None
    keep_dirs = set(args.keep) if args.keep else None

    if run_all or args.archive:
        archive_workspaces(
            extra_patterns=extra_patterns,
            keep_dirs=keep_dirs,
            dry_run=args.dry_run,
        )

    if run_all or args.tasks:
        cleanup_tasks(
            session_id=args.session,
            dry_run=args.dry_run,
        )

    if run_all or args.db:
        sync_database(dry_run=args.dry_run)

    if not run_all:
        print("\nDone.")


if __name__ == "__main__":
    main()
