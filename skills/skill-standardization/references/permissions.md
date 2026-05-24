# 权限类型说明

> 本文档详细说明 `permission_checker.py` 检测到的所有权限类型、风险等级、触发条件，以及 skill 行为对照表。
>
> 适用读者：skill 开发者、审查者、需要声明权限的 AI 工作者。

---

## 风险等级定义

| 风险等级 | 含义 | 授权建议 |
|-----------|------|----------|
| `high` | 高风险操作，可能产生不可逆影响（删除数据、访问敏感信息、执行系统命令） | 每次执行前询问用户确认 |
| `medium` | 中风险操作，影响范围可控（网络请求、限定范围内的文件删除） | 可批量统一授权 |
| `low` | 低风险操作，仅读取或记录 | 静默执行，仅记录日志 |

---

## 权限类型总览

| 权限类型 | 风险等级 | 触发行为（脚本中出现以下模式） | frontmatter 声明字段 |
|-----------|-----------|--------------------------------|----------------------|
| `sensitive_access` | **high** | 读取 memory/、credentials、token、密钥等敏感路径或变量名 | `sensitive_access: true` |
| `critical_write` | **high** | 写入 `skills/.workbuddy/` 系统目录（非技能自身目录） | `critical_write: true` |
| `subprocess_call` | **high** | 调用 `os.system()`、`subprocess` 模块、执行 shell 命令 | `critical_write: true`（目前复用） |
| `network_access` | **medium** | 发起 HTTP 请求（`requests`、`urllib`、`curl` 等） | 无需声明（WARN 级） |
| `file_delete` | **medium** | 执行文件/目录删除（`os.remove`、`shutil.rmtree` 等） | 无需声明（WARN 级） |

> ⚠️ 注意：`subprocess_call` 和 `file_delete` 目前复用 `critical_write` 声明字段，后续版本会独立。

---

## 各权限详细说明

### 1. `sensitive_access`（敏感信息访问）

- **触发条件**：脚本中出现以下模式之一
  - 路径字符串含 `memory/`、`.workbuddy/`、`.git/`
  - 变量名含 `token`、`secret`、`password`、`credential`、`api_key`
  - 字符串含 `skills/.workbuddy`
- **风险**：可能泄露用户敏感数据，或跨技能访问其他 skill 的私有数据
- **frontmatter 声明示例**：
  ```yaml
  sensitive_access: true
  # 建议附加说明字段（非强制）
  # sensitive_access_reason: "需要读取用户 memory 实现个性化回复"
  ```
- **典型场景**：
  - 读取 `~/.workbuddy/memory/` 下的记忆文件
  - 访问环境变量中的 API Token
  - 读取其他 skill 目录下的配置文件

---

### 2. `critical_write`（关键位置写入）

- **触发条件**：脚本中**写入路径**匹配以下模式之一
  - `skills/.workbuddy/`（系统目录）
  - 指向非当前 skill 目录的写操作
- **风险**：可能破坏 WorkBuddy 系统文件，或篡改其他 skill 的文件
- **frontmatter 声明示例**：
  ```yaml
  critical_write: true
  # 建议附加说明字段（非强制）
  # critical_write_reason: "需要更新 skills/.standardization/ 下的规范文件"
  ```
- **典型场景**：
  - `git-sync` 写入 `skills/.standardization/<skill>/` 下的规范文件
  - 任何 skill 修改 `.workbuddy/` 系统目录下的文件
  - 跨 skill 目录写文件

---

### 3. `subprocess_call`（子进程调用）

- **触发条件**：脚本中出现以下模式之一
  - `os.system(`、`os.popen(`
  - `subprocess.run(`、`subprocess.Popen(`、`subprocess.call(`、`subprocess.check_output(`
  - `commands.getoutput(`（Python 2 遗留）
- **风险**：可执行任意系统命令，影响系统安全；命令注入可导致远程代码执行
- **frontmatter 声明**：目前复用 `critical_write: true`（后续版本独立）
- **典型场景**：
  - `git-sync` 执行 `git add`、`git commit`、`git push` 等 git 命令
  - 调用 `npm`、`pip` 等包管理工具
  - 执行系统工具（如 `zip`、`tar`）

---

### 4. `network_access`（网络访问）

- **触发条件**：脚本中出现以下模式之一
  - `import requests`、`from urllib`、`import httpx`、`import aiohttp`
  - `urlopen(`、`http.client`、`socket.socket`（作为客户端）
- **风险**：可能泄露数据到外部服务器，或访问恶意地址
- **frontmatter 声明**：目前无需声明（R-16 WARN 级，建议说明）
- **典型场景**：
  - 调用 Web API（`requests.get()` 等）
  - Webhook 通知
  - 下载外部资源

---

### 5. `file_delete`（文件删除）

- **触发条件**：脚本中出现以下模式之一
  - `os.remove(`、`os.unlink(`、`os.rmdir(`
  - `shutil.rmtree(`、`pathlib.Path.unlink(`、`pathlib.Path.rmdir(`
- **风险**：不可逆删除用户文件，误操作后果严重
- **frontmatter 声明**：目前无需声明（R-16 WARN 级，建议说明）
- **典型场景**：
  - `git-sync` 清理 `.dist/` 下的旧 zip 文件
  - 临时文件清理
  - 重构时删除废弃文件

---

## skill 行为对照表（以 git-sync 为例）

下表展示一个真实 skill 的各行为分别触发哪些权限类型，帮助开发者理解如何声明。

| skill 行为 | 触发的权限类型 | 风险等级 | frontmatter 声明 |
|-------------|-----------------|----------|-------------------|
| 读取 `.workbuddy/memory/` 下的记忆文件（如有） | `sensitive_access` | high | `sensitive_access: true` |
| 写入 `skills/.standardization/<skill>/` 下的规范文件 | `critical_write` | high | `critical_write: true` |
| 执行 `git add` / `git commit` / `git push` 命令 | `subprocess_call` | high | `critical_write: true` |
| 执行 `zip` / `tar` 命令打包 | `subprocess_call` | high | `critical_write: true` |
| 清理 `.dist/` 下的旧 zip 文件 | `file_delete` | medium | （建议说明） |
| 读取 `skills/` 下各 skill 的 `_meta.json`（只读） | — | low | 无需声明 |

---

## 权限声明检查规则（R-13 ~ R-15）

| 规则 ID | 严重度 | 检查内容 | 修复指引 |
|----------|---------|----------|----------|
| R-13 | ERROR | `sensitive_access: true` 须与脚本中实际敏感信息访问行为一致 | 在 frontmatter 中声明，并在 SKILL.md 中说明用途 |
| R-14 | ERROR | `critical_write: true` 须与脚本中实际关键位置写入行为一致 | 在 frontmatter 中声明，并在 SKILL.md 中说明用途 |
| R-15 | ERROR | 高权限操作（文件删除/网络请求/subprocess 调用）执行前须请求用户授权 | 在 skill 中调用 `authorization_manager.py` 或等效机制 |

> 完整规则定义见 `references/reference.md` 的「审查规则（R-01 ~ R-17）」章节。

---

## 权限权重计算

`permission_checker.py` 扫描完成后，会计算每个权限维度的权重，最终汇总为 `permission_weight`（0.0 ~ 1.0）。

| 维度 | 权重占比 | 说明 |
|-------|-----------|------|
| 敏感信息访问 | 40% | 读取 memory/credentials/token 等 |
| 关键位置写入 | 30% | 写入 `skills/.workbuddy/` 系统目录 |
| 网络访问 | 20% | 发起 HTTP 请求 |
| 文件删除 | 10% | 删除文件或目录 |

**解读**：
- `permission_weight < 0.3`：低风险，可直接发布
- `permission_weight 0.3 ~ 0.6`：中风险，建议审查后发布
- `permission_weight > 0.6`：高风险，须详细说明用途并通过安全审查

---

## 授权决策逻辑参考

> 本节提供授权决策的参考逻辑，供 AI/智能体自觉参考使用。
> **不强制注入代码**，由 AI 根据实际情况自行判断是否采用。

### 决策维度

授权决策应综合考虑以下维度：

| 维度 | 说明 |
|------|------|
| **skill 工作范围** | skill 是读操作为主还是写操作为主？是否涉及系统目录？ |
| **skill 工作场景** | 交互式（用户输入驱动）还是非交互式（定时任务/后台运行）？ |
| **权限风险等级** | high / medium / low（见上方「风险等级定义」） |
| **用户显式意图** | 用户是否明确要求「不询问直接执行」？ |

---

### 三种授权模式

#### 模式 A：默认审批（推荐用于低风险 skill）

**适用场景**：
- skill 工作范围：仅读取、日志记录、临时文件操作
- skill 工作场景：交互式或非交互式均可
- 权限权重 < 0.3

**决策逻辑**：
```
权限风险等级 == low
  → 默认授权，静默执行，仅记录日志
权限风险等级 == medium
  → 首次运行时询问一次，后续默认授权
权限风险等级 == high
  → 转入模式 B 或模式 C
```

---

#### 模式 B：即时审批（推荐用于中高风险 skill）

**适用场景**：
- skill 工作范围：涉及文件删除、网络请求、subprocess 调用
- skill 工作场景：交互式（用户输入驱动）
- 权限权重 0.3 ~ 0.7

**决策逻辑**：
```
执行每个高风险操作前：
  → 向用户展示操作描述（description）
  → 询问：是否执行？（y/n）
  → 用户同意 → 执行
  → 用户拒绝 → 跳过，记录到日志
```

**注意**：非交互场景（定时任务）下，即时审批不可用，应转入模式 A（默认拒绝高风险）或模式 C（统一审批）。

---

#### 模式 C：统一审批（推荐用于非交互式 skill）

**适用场景**：
- skill 工作范围：涉及高风险操作
- skill 工作场景：非交互式（定时任务、后台运行、CI/CD）
- 无法在运行时等待用户输入

**决策逻辑**：
```
skill 启动前（非交互环境检测）：
  → 扫描将要执行的高风险操作清单
  → 一次性展示给用户确认
  → 用户统一审批通过 → 执行
  → 用户拒绝其中某项 → 跳过该项
  → 用户全部拒绝 → 退出
```

---

### AI 自觉参考指南

当 AI 在处理技能时，应自觉参考以上逻辑：

1. **扫描阶段**：运行 `permission_checker.py`，得到权限清单和风险等级
2. **评估阶段**：根据 skill 工作范围和工作场景，判断适用哪种授权模式
3. **说明阶段**：向用户说明权限类型和推荐的授权模式，由用户决策
4. **执行阶段**：按用户选择的模式执行（或 AI 自觉按推荐模式执行）

> ⚠️ **重要**：以上逻辑为参考建议，非强制规则。AI 应根据实际情况灵活处理，本质是「自觉」而非「强制」。

---

当用户请求创建或更新 skill 时，AI 应按以下流程处理权限：

```
1. 运行 permission_checker.py 扫描目标 skill
   ↓
2. 解析报告中的 issues[] 列表
   ↓
3. 按 issue.type 归类，去重得到权限类型清单
   ↓
4. 检查 skill 的 frontmatter 是否已声明对应字段
   - 未声明 → 在 SKILL.md 中提示用户补充声明
   - 已声明但与扫描结果不一致 → 提示修正
   ↓
5. 将权限类型、风险等级、触发行为记录到 references/permissions.md（本文档）
   ↓
6. 如用户同意，执行注入 auth_check.py（可选，非强制）
```

> **注意**：本 skill（skill-standardization v2.14.0+）仅做权限说明和扫描，**不进行强制注入**。是否注入 `auth_check.py` 由用户决定。

---

## 常见问题

**Q：`sensitive_access` 和 `critical_write` 必须同时声明吗？**
A：不一定。如果你的 skill 只读取敏感信息但不写入关键位置，只需声明 `sensitive_access: true`。反之亦然。

**Q：网络访问一定要声明吗？**
A：目前 R-16 是 WARN 级，不强制。但建议在 SKILL.md 的「注意事项」中说明网络访问的用途。

**Q：`subprocess_call` 为什么复用 `critical_write` 字段？**
A：这是 v2.14.0 的临时方案。后续版本会引入独立的 `subprocess_call: true` 字段。

**Q：如何降低 skill 的权限权重？**
A：尽量减少敏感信息访问和关键位置写入；网络访问和文件删除的影响相对较小。也可将高风险操作拆到独立的子 skill 中。

---

*本文档由 skill-standardization v2.14.0+ 维护。最后更新：2026-05-24*
