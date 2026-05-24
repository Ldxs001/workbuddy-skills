# git-sync — 权限说明

> 本文档说明 git-sync 的权限需求和风险等级，按需加载。

## 权限类型与风险等级

| 权限 | 风险等级 | 说明 |
|--------|---------|------|
| `sensitive_access` | 🟡 medium | 读取 `config.json`（含用户名配置），不读取 Token |
| `critical_write` | 🟡 medium | 写入 `.dist/` 目录、更新 `README.md`、修改 `manifest.json` |
| `subprocess_call` | 🔴 high | 执行 `git`、`bash git-sync.sh`、`python` 等外部命令 |
| `network_access` | 🔴 high | 推送到码云（gitee）和 GitHub（需要网络） |
| `file_delete` | 🟡 medium | 清理临时文件（`.tmp`/`.bak` 等） |

## 行为对照表

| 操作 | 权限 | 授权方式 | 说明 |
|--------|------|---------|------|
| 读取 `config.json` | `sensitive_access` | `unified`（默认审批） | 获取用户名和仓库配置 |
| 执行 `git push` | `subprocess_call` + `network_access` | `unified` | 推送到远程仓库 |
| 写入 `.dist/` ZIP 包 | `critical_write` | `immediate`（用户主动触发） | 生成安装包 |
| 更新 `README.md` | `critical_write` | `unified` | 全量重建技能列表 |
| 更新 `manifest.json` | `critical_write` | `unified` | 维护清单状态标记 |

## 触发条件

- 用户明确说「同步、上传、推送、打包」某个 skill 时触发
- 未明确说「全量维护」时，只同步指定 skill（按需同步）
- 明确说「全量维护」或「同步所有」时，遍历 `manifest.json` 所有条目

## 注意事项

- `config.json` 中的 Token 不应硬编码，建议通过环境变量或 git config 管理
- `subprocess_call` 和 `network_access` 为高风险权限，首次使用需经用户确认
- 敏感信息扫描（`sensitive_scan.py`）在同步前自动执行，发现敏感信息会暂停并请求决策
