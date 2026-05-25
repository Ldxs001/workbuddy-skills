# universal-file-ops 使用指南

本指南详细说明 universal-file-ops 技能的使用方式、脚本接口和设计理念。

---

## 设计理念

1. **鲁棒性优先**：所有写操作前自动备份，支持回滚
2. **标准化 IO**：所有脚本输入输出均为 JSON，便于程序化调用和调试
3. **幂等性**：重复执行不产生副作用（读操作天然幂等，写操作在适当条件下幂等）
4. **可回溯**：所有操作记录日志（`data/logs/ops.log`），备份留存（`data/backup/`）

---

## 快速开始

### 方式一：直接调用脚本（LLM 推荐）

```bash
# 读取文件
python scripts/text_crud.py --action read --file hello.txt

# 创建文件（自动备份已有文件）
python scripts/text_crud.py --action create --file hello.txt --content "Hello World"

# 拷贝文件
python scripts/file_ops.py --action copy --src hello.txt --dst hello_copy.txt

# 删除文件（先备份）
python scripts/file_ops.py --action delete --file hello.txt
```

### 方式二：JSON 模式（程序化调用）

```bash
# 通过 stdin 传入 JSON
echo '{"action":"create","file":"test.txt","content":"Hello"}' | python scripts/text_crud.py

# 通过 --input 文件传入
echo '{"action":"copy","src":"a.txt","dst":"b.txt"}' > /tmp/req.json
python scripts/file_ops.py --input /tmp/req.json
```

### 方式三：通过 orchestrator 批量执行

```bash
# 1. 编写批量配置文件 batch.json
# 2. 执行
python scripts/orchestrator.py --batch batch.json
```

---

## 标准化 IO 接口

所有脚本遵循统一的输入输出规范。

### 输入（三种方式）

| 方式 | 适用场景 |
|------|----------|
| CLI 参数（`--action --file ...`） | LLM 直接调用，最简单 |
| stdin JSON | 管道传递，程序化调用 |
| `--input <file>` | JSON 配置从文件读取 |

### 输出（统一 JSON 到 stdout）

**成功时：**
```json
{
  "success": true,
  "action": "create",
  "file": "path/to/file.txt",
  "result": { "size": 11, "backup_file": "..." },
  "error": null,
  "rollback_id": "backup/20260525_...bak"
}
```

**失败时：**
```json
{
  "success": false,
  "action": null,
  "file": "path/to/file.txt",
  "result": null,
  "error": "文件不存在: ...",
  "rollback_id": null
}
```

### rollback_id 的使用

`rollback_id` 是备份文件的相对路径（相对于 `data/backup/`）。
用于出错时回滚：

```bash
python scripts/rollback.py --id "20260525_164457_file.txt_abcdef01.bak"
```

---

## 各脚本说明

### text_crud.py — 文本类文件增删查改

支持格式：`.txt`, `.py`, `.html`, `.md`, `.csv`, `.json`, `.yaml`, `.xml`, `.css`, `.js`, `.ts`

| action | 必填参数 | 可选参数 | 说明 |
|--------|------------|------------|------|
| `read` | `--file` | `--encoding`（默认 utf-8） | 读取文件内容 |
| `create` | `--file`, `--content` | `--overwrite`, `--no-backup` | 创建文件 |
| `update` | `--file`, `--content` | `--mode`（`replace`/`append`/`insert`）, `--line`, `--no-backup` | 更新文件 |
| `delete` | `--file` | `--no-backup` | 删除文件 |

### office_crud.py — Office 文件增删查改

支持格式：`.docx`, `.xlsx`

依赖（可选，缺失时报错引导安装）：
- `python-docx`（处理 .docx）：`pip install python-docx`
- `openpyxl`（处理 .xlsx）：`pip install openpyxl`

| action | 必填参数 | 说明 |
|--------|------------|------|
| `read` | `--file` | 读取 docx 全文 / xlsx 全部 sheet |
| `create` | `--file`, `--content`（docx 时） | 创建 Office 文件 |
| `update` | `--file`, `--content` | 更新 docx 全文覆盖 |
| `delete` | `--file` | 删除 Office 文件 |

### file_ops.py — 通用文件操作

| action | 必填参数 | 可选参数 | 说明 |
|--------|------------|------------|------|
| `copy` | `--src`, `--dst` | `--overwrite`, `--no-backup` | 拷贝文件或目录 |
| `move` | `--src`, `--dst` | `--overwrite`, `--no-backup` | 移动（跨文件系统自动降级为 拷贝+删除） |
| `rename` | `--file`, `--new-name` | `--overwrite`, `--no-backup` | 重命名（封装 move） |
| `delete` | `--file` | `--no-backup` | 删除文件或目录（不存在时幂等返回 success） |

### orchestrator.py — 统一调度器

| 参数 | 说明 |
|------|------|
| `--list` | 列出所有可用操作 |
| `--op <name>` | 单操作模式（从 stdin 传 JSON） |
| `--batch <file>` | 批量执行（JSON 配置文件） |
| `--parallel` | 并行执行（默认串行） |
| `--no-stop` | 失败不中止（继续后续任务） |
| `--dry-run` | 仅打印计划，不实际执行 |

### rollback.py — 容灾回滚

| 参数 | 说明 |
|------|------|
| `--id <backup_file>` | 回滚单个备份 |
| `--ids <id1,id2>` | 批量回滚 |
| `--restore-to <path>` | 显式指定恢复路径（覆盖 manifest） |
| `--list` | 列出所有可用备份 |
| `--dry-run` | 预览模式 |

---

## 批量配置格式（batch.json）

```json
{
  "tasks": [
    {
      "op": "text_crud",
      "args": {"action": "create", "file": "a.txt", "content": "Hello"}
    },
    {
      "op": "file_ops",
      "args": {"action": "copy", "src": "a.txt", "dst": "b.txt"}
    },
    {
      "op": "text_crud",
      "args": {"action": "read", "file": "b.txt"}
    }
  ],
  "parallel": false,
  "stop_on_error": true
}
```

**字段说明：**
- `tasks`：任务数组，每项包含 `op`（操作脚本名）和 `args`（传给脚本的 JSON 参数）
- `parallel`：`true` 时并行执行（线程池），`false` 时串行
- `stop_on_error`：`true` 时任意任务失败立即中止后续任务

---

## 容灾与回溯机制

### 自动备份

所有破坏性操作（create overwrite、update、delete、move、copy overwrite）执行前，自动将目标文件备份至：

```
skills/.standardization/universal-file-ops/data/backup/
    └── 20260525_164457_123456_file.txt_abcdef01.bak
```

备份文件名格式：`<时间戳>_<原文件名>_<SHA256前8位>.bak`

### 回滚

1. 从操作结果的 `rollback_id` 字段获取备份文件名
2. 执行回滚：

```bash
python scripts/rollback.py --id "<rollback_id>"
```

3. 批量回滚（orchestrator 失败时会打印提示）：

```bash
python scripts/rollback.py --ids "id1.bak,id2.bak"
```

### 操作日志

所有操作记录在：

```
skills/.standardization/universal-file-ops/data/logs/ops.log
```

格式：`[timestamp] OK|FAIL | action | file_path | rollback=... | detail`

---

## LLM 使用建议

1. **优先直接调用脚本**（方式一），最简单直观
2. **需要编排多步骤时使用 orchestrator**（方式三）
3. **不要更新 `scripts/` 下的原始脚本**——如需适配，创建副本并注明来源
4. **检查返回的 `success` 字段**——失败时有 `error` 字段说明原因
5. **重要操作前可手动备份**——虽然脚本自动备份，但重要数据双重保护更安全
