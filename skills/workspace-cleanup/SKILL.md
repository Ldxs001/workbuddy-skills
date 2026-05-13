---
name: workspace-cleanup
description: >
  WorkBuddy 综合清理技能，包含两大功能：
  1) 工作区归档：归档非活跃工作区目录，同步数据库。
  2) 会话任务清理：清理会话 jsonl 文件中的 TaskCreate/TaskUpdate/TaskList 幽灵任务记录。
  由 heartbeat（每6小时）或手动触发运行。
---

# WorkBuddy Workspace Cleanup Skill

## 概述

本技能负责 WorkBuddy 环境的综合清理，包含两个模块：
- **模块 A：工作区归档** — 归档非活跃工作区目录，同步数据库
- **模块 B：会话任务清理** — 清理 jsonl 中的幽灵任务记录

两个模块可独立运行，也可一起运行。

---

## 模块 A：工作区归档

### 目标

保持 WorkBuddy 工作区目录整洁，只保留 `Claw` 作为唯一活跃工作区，其余自动归档。

### 判定规则

**需要归档的目录：**
- 位于 `WorkBuddy/` 根目录下
- 目录名匹配模式：`automation-claw-*` 或 `YYYY-MM-DD-task-N*`
- 心跳触发时直接归档，**不做时间判断**

**不归档：**
- `Claw/` — 主工作区，永远保留
- `archive/` — 归档目录本身
- 当前正在使用的工作区（cwd）

### 执行步骤

```python
import os, time, shutil, sqlite3

WORKBUDDY_ROOT = os.path.expanduser('~/WorkBuddy')
ARCHIVE_DIR = os.path.join(WORKBUDDY_ROOT, 'archive')
CLAW_NAME = 'Claw'
DB_PATH = os.path.expanduser('~/.workbuddy/workbuddy.db')

def archive_workspaces():
    """归档非Claw工作区并同步数据库（不做时间判断）"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    to_archive = []

    print(f"[Module A] Scanning {WORKBUDDY_ROOT} ...")
    for name in os.listdir(WORKBUDDY_ROOT):
        full = os.path.join(WORKBUDDY_ROOT, name)
        if not os.path.isdir(full):
            continue
        if name == CLAW_NAME or name == 'archive':
            continue
        if name.startswith('automation-claw-') or name.startswith('2026-') or name.startswith('2025-') or '-task-' in name:
            to_archive.append((name, full))
            print(f"  TO_ARCHIVE: {name}")

    if not to_archive:
        print("[Module A] Nothing to archive.")
        return

    # 文件系统归档
    for name, full in to_archive:
        dst = os.path.join(ARCHIVE_DIR, name)
        if os.path.exists(dst):
            dst += '_' + time.strftime('%Y%m%d%H%M%S')
        try:
            shutil.move(full, dst)
            print(f"  MOVED: {name} -> archive/")
        except (PermissionError, OSError) as e:
            print(f"  SKIP (locked): {name} - {e}")

    # 同步数据库
    if not os.path.exists(DB_PATH):
        print(f"[Module A] DB not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    claw_cwd = "C:\\Users\\" + os.getlogin() + "\\WorkBuddy\\Claw"

    for row in conn.execute('SELECT rowid, path FROM workspaces').fetchall():
        if not os.path.exists(row[1]):
            conn.execute('DELETE FROM workspaces WHERE rowid = ?', (row[0],))
            print(f"  workspaces DEL rowid={row[0]}")

    updated = 0
    for row in conn.execute('SELECT rowid, cwd FROM sessions').fetchall():
        if row[1] and not os.path.exists(row[1]):
            conn.execute('UPDATE sessions SET cwd = ? WHERE rowid = ?', (claw_cwd, row[0]))
            updated += 1
    print(f"  sessions UPDATED: {updated} rows")

    # 清理 automation_runs 表中已归档工作区的历史记录
    for name, full in to_archive:
        cur = conn.execute('DELETE FROM automation_runs WHERE source_cwd = ?', (full,))
        if cur.rowcount > 0:
            print(f"  automation_runs DELETED: {cur.rowcount} rows for {name}")

    # 清理 sessions 表中旧的 cleanup heartbeat 记录，只保留最新一条
    rows = conn.execute(
        "SELECT id FROM sessions WHERE custom_title = 'workbuddy-cleanup-heartbeat' AND status = 'completed' ORDER BY created_at DESC"
    ).fetchall()
    if len(rows) > 1:
        to_archive_ids = [r[0] for r in rows[1:]]
        placeholders = ','.join('?' * len(to_archive_ids))
        cur = conn.execute(
            f"UPDATE sessions SET status = 'archived' WHERE id IN ({placeholders})",
            to_archive_ids
        )
        print(f"  sessions ARCHIVED: {cur.rowcount} old cleanup sessions")

    conn.commit()
    conn.close()
    print("[Module A] Done.")
```

---

## 模块 B：会话任务清理

### 目标

清理会话 jsonl 文件中的 `TaskCreate`、`TaskUpdate`、`TaskList` 工具调用记录。
这些记录会导致 UI 显示幽灵任务（TaskList 为空但 UI 仍显示旧任务）。

### 背景

WorkBuddy UI 的任务面板从 jsonl 历史记录中读取 `TaskCreate` 的 `function_call` 条目来渲染任务列表。
即使 TaskList 工具返回空，UI 仍会显示历史中的 TaskCreate 记录。
需要删除这些行才能彻底清理。

### jsonl 文件位置

```
~/.workbuddy/projects/<workspace-hash>/<session-id>.jsonl
```

路径示例：
```
C:\Users\sm001\.workbuddy\projects\c-Users-sm001-WorkBuddy-Claw\<uuid>.jsonl
```

### 执行步骤

```python
import json, os, glob

PROJECTS_DIR = os.path.expanduser('~/.workbuddy/projects')

def cleanup_session_tasks(session_id=None, workspace_pattern=None):
    """
    清理会话 jsonl 中的 TaskCreate/TaskUpdate/TaskList 记录。

    参数：
      session_id: 指定清理某个会话（UUID）
      workspace_pattern: 指定清理某个工作区目录下的所有会话
      不传参数：清理所有 jsonl 文件
    """
    # 确定 jsonl 文件列表
    jsonl_files = []

    if session_id:
        # 在所有工作区下搜索该 session
        for root, dirs, files in os.walk(PROJECTS_DIR):
            if session_id + '.jsonl' in files:
                jsonl_files.append(os.path.join(root, session_id + '.jsonl'))
    elif workspace_pattern:
        # 搜索匹配的工作区目录
        ws_dir = os.path.join(PROJECTS_DIR, workspace_pattern)
        if os.path.isdir(ws_dir):
            jsonl_files = glob.glob(os.path.join(ws_dir, '*.jsonl'))
    else:
        # 全量扫描
        jsonl_files = glob.glob(os.path.join(PROJECTS_DIR, '**/*.jsonl'), recursive=True)

    task_tool_names = {'TaskCreate', 'TaskUpdate', 'TaskList'}
    total_removed = 0

    for fpath in jsonl_files:
        lines_out = []
        removed = 0

        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if not line.strip():
                    lines_out.append(line)
                    continue
                try:
                    obj = json.loads(line)
                    # 删除 TaskXxx 的 function_call 行
                    if obj.get('type') == 'function_call' and obj.get('name') in task_tool_names:
                        removed += 1
                        continue
                    # 删除 TaskXxx 的 function_call_result 行
                    if obj.get('type') == 'function_call_result' and obj.get('name') in task_tool_names:
                        removed += 1
                        continue
                    lines_out.append(json.dumps(obj, ensure_ascii=False))
                except json.JSONDecodeError:
                    lines_out.append(line)

        if removed > 0:
            with open(fpath, 'w', encoding='utf-8') as f:
                for line in lines_out:
                    f.write(line + '\n')
            print(f"  {os.path.basename(fpath)}: removed {removed} lines")
            total_removed += removed

    print(f"[Module B] Total removed: {total_removed} lines across {len(jsonl_files)} files")
```

### 使用方式

```python
# 1. 清理指定会话
cleanup_session_tasks(session_id='8892d3c4-129f-4e2b-85c9-d6d1315e0ae0')

# 2. 清理指定工作区下所有会话
cleanup_session_tasks(workspace_pattern='c-Users-sm001-WorkBuddy-Claw')

# 3. 全量清理（慎用）
# cleanup_session_tasks()
```

---

## 完整脚本（可复用）

将以下脚本保存为 `workbuddy_cleanup.py`，放在 `Claw/` 目录下：

```python
#!/usr/bin/env python3
"""
workbuddy_cleanup.py
WorkBuddy 综合清理：工作区归档 + 会话任务清理（含子 Agent 安全保障）
用法：
  python workbuddy_cleanup.py              # 运行全部
  python workbuddy_cleanup.py --archive    # 仅归档
  python workbuddy_cleanup.py --tasks      # 仅清理任务
  python workbuddy_cleanup.py --tasks --session <uuid>  # 清理指定会话
"""
import os, sys, json, time, shutil, sqlite3, glob, argparse

# ========== 配置 ==========
WORKBUDDY_ROOT = os.path.expanduser('~/WorkBuddy')
ARCHIVE_DIR = os.path.join(WORKBUDDY_ROOT, 'archive')
CLAW_NAME = 'Claw'
DB_PATH = os.path.expanduser('~/.workbuddy/workbuddy.db')
PROJECTS_DIR = os.path.expanduser('~/.workbuddy/projects')
TASK_TOOL_NAMES = {'TaskCreate', 'TaskUpdate', 'TaskList'}
CURRENT_CWD = os.path.abspath(os.getcwd()) if os.getcwd() else ''


def get_active_cwds():
    """查询数据库获取所有活跃会话（status='working'）的 cwd"""
    if not os.path.exists(DB_PATH):
        return set()
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT cwd FROM sessions WHERE status = 'working'").fetchall()
        conn.close()
        active = set()
        for (cwd,) in rows:
            if cwd:
                active.add(os.path.abspath(cwd))
        return active
    except Exception:
        return set()


def get_active_session_ids():
    """查询数据库获取所有活跃会话（status='working'）的 session UUID"""
    if not os.path.exists(DB_PATH):
        return set()
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT id FROM sessions WHERE status = 'working'").fetchall()
        conn.close()
        return {row[0] for row in rows}
    except Exception:
        return set()


def archive_workspaces():
    """模块 A：归档非活跃工作区并同步数据库"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    to_archive = []

    # 获取活跃会话 cwd 列表，保护正在运行的子 Agent 工作区
    active_cwds = get_active_cwds()

    print(f"\n[Module A] Scanning {WORKBUDDY_ROOT} ...")
    if active_cwds:
        print(f"  Active session cwds: {len(active_cwds)}")
    for name in os.listdir(WORKBUDDY_ROOT):
        full = os.path.join(WORKBUDDY_ROOT, name)
        if not os.path.isdir(full):
            continue
        if name == CLAW_NAME or name == 'archive':
            continue
        # 跳过当前正在使用的工作区（避免 WinError 32）
        if os.path.abspath(full) == CURRENT_CWD or full == CURRENT_CWD:
            print(f"  SKIP (current cwd): {name}")
            continue
        # 跳过活跃会话所在的工作区目录（保护正在运行的子 Agent）
        if os.path.abspath(full) in active_cwds:
            print(f"  SKIP (active session): {name}")
            continue
        # 匹配自动化工作区命名模式，直接归档，不做时间判断
        if name.startswith('automation-claw-') or name.startswith('2026-') or name.startswith('2025-') or '-task-' in name:
            to_archive.append((name, full))
            print(f"  TO_ARCHIVE: {name}")

    if not to_archive:
        print("[Module A] Nothing to archive.")
        return

    for name, full in to_archive:
        dst = os.path.join(ARCHIVE_DIR, name)
        if os.path.exists(dst):
            dst += '_' + time.strftime('%Y%m%d%H%M%S')
        try:
            shutil.move(full, dst)
            print(f"  MOVED: {name} -> archive/")
        except (PermissionError, OSError) as e:
            print(f"  SKIP (locked): {name} - {e}")

    if not os.path.exists(DB_PATH):
        print(f"[Module A] DB not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    claw_cwd = "C:\\Users\\" + os.getlogin() + "\\WorkBuddy\\Claw"

    for row in conn.execute('SELECT rowid, path FROM workspaces').fetchall():
        if not os.path.exists(row[1]):
            conn.execute('DELETE FROM workspaces WHERE rowid = ?', (row[0],))
            print(f"  workspaces DEL rowid={row[0]}")

    updated = 0
    for row in conn.execute('SELECT rowid, cwd FROM sessions').fetchall():
        if row[1] and not os.path.exists(row[1]):
            conn.execute('UPDATE sessions SET cwd = ? WHERE rowid = ?', (claw_cwd, row[0]))
            updated += 1
    print(f"  sessions UPDATED: {updated} rows")

    # 清理 automation_runs 表中已归档工作区的历史记录
    for name, full in to_archive:
        cur = conn.execute('DELETE FROM automation_runs WHERE source_cwd = ?', (full,))
        if cur.rowcount > 0:
            print(f"  automation_runs DELETED: {cur.rowcount} rows for {name}")

    # 清理 sessions 表中旧的 cleanup heartbeat 记录，只保留最新一条
    rows = conn.execute(
        "SELECT id FROM sessions WHERE custom_title = 'workbuddy-cleanup-heartbeat' AND status = 'completed' ORDER BY created_at DESC"
    ).fetchall()
    if len(rows) > 1:
        to_archive_ids = [r[0] for r in rows[1:]]
        placeholders = ','.join('?' * len(to_archive_ids))
        cur = conn.execute(
            f"UPDATE sessions SET status = 'archived' WHERE id IN ({placeholders})",
            to_archive_ids
        )
        print(f"  sessions ARCHIVED: {cur.rowcount} old cleanup sessions")

    conn.commit()
    conn.close()
    print("[Module A] Done.")


def cleanup_tasks(session_id=None):
    """模块 B：清理 jsonl 中的幽灵任务记录，跳过活跃会话"""
    jsonl_files = []

    # 获取活跃会话 ID 列表，保护正在写入的 jsonl 文件
    active_ids = get_active_session_ids()

    if session_id:
        for root, dirs, files in os.walk(PROJECTS_DIR):
            if session_id + '.jsonl' in files:
                jsonl_files.append(os.path.join(root, session_id + '.jsonl'))
    else:
        jsonl_files = glob.glob(os.path.join(PROJECTS_DIR, '**/*.jsonl'), recursive=True)

    total_removed = 0
    print(f"\n[Module B] Scanning {len(jsonl_files)} jsonl files ...")
    if active_ids:
        print(f"  Active session IDs: {len(active_ids)} (will skip)")

    for fpath in jsonl_files:
        # 跳过活跃会话的 jsonl 文件
        basename = os.path.splitext(os.path.basename(fpath))[0]
        if basename in active_ids:
            print(f"  SKIP (active session): {basename}.jsonl")
            continue

        lines_out = []
        removed = 0

        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if not line.strip():
                    lines_out.append(line)
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get('type') == 'function_call' and obj.get('name') in TASK_TOOL_NAMES:
                        removed += 1
                        continue
                    if obj.get('type') == 'function_call_result' and obj.get('name') in TASK_TOOL_NAMES:
                        removed += 1
                        continue
                    lines_out.append(json.dumps(obj, ensure_ascii=False))
                except json.JSONDecodeError:
                    lines_out.append(line)

        if removed > 0:
            with open(fpath, 'w', encoding='utf-8') as f:
                for line in lines_out:
                    f.write(line + '\n')
            print(f"  {os.path.basename(fpath)}: removed {removed} lines")
            total_removed += removed

    print(f"[Module B] Total removed: {total_removed} lines")


def main():
    parser = argparse.ArgumentParser(description='WorkBuddy Cleanup')
    parser.add_argument('--archive', action='store_true', help='Run workspace archiver only')
    parser.add_argument('--tasks', action='store_true', help='Run task cleanup only')
    parser.add_argument('--session', type=str, default=None, help='Specific session UUID for task cleanup')
    args = parser.parse_args()

    if not args.archive and not args.tasks:
        archive_workspaces()
        cleanup_tasks(session_id=args.session)
    else:
        if args.archive:
            archive_workspaces()
        if args.tasks:
            cleanup_tasks(session_id=args.session)

    print("\nAll cleanup complete.")


if __name__ == '__main__':
    main()
```

---

## Heartbeat 定时配置

在 WorkBuddy 中创建 automation，每 6 小时触发一次：

- **名称：** `workbuddy-cleanup-heartbeat`
- **提示词：** `运行 C:\Users\sm001\WorkBuddy\Claw\workbuddy_cleanup.py，执行综合清理`
- **调度：** 每 6 小时（`RRULE:FREQ=HOURLY;INTERVAL=6`）
- **工作区：** `C:\Users\sm001\WorkBuddy\Claw`

## 注意事项

1. **永远不要归档 `Claw/` 目录和当前 cwd 目录**
2. **不做时间判断**，心跳触发时直接归档所有匹配的非Claw目录
3. **数据库路径** `~/.workbuddy/workbuddy.db` 是固定的
4. 归档操作是 **move**（非删除），可从 `archive/` 恢复
5. jsonl 清理是**不可逆**的，清理后 TaskCreate 的历史参数会丢失
6. 清理 jsonl 后需**重启 WorkBuddy 客户端**才能看到效果
7. 模块 B 的全量模式（不指定 session）会扫描所有 jsonl，谨慎使用
8. **子 Agent 安全保障**：自动查询 `sessions WHERE status='working'` 获取活跃会话，归档跳过其 cwd 目录，jsonl 清理跳过其文件，防止中断正在运行的子任务
