# 权限说明

权限扫描风险等级：**HIGH**

## 权限总览

共 6 项权限风险，按类别分组如下：

### 敏感信息访问（1 项）
> **权限作用**：读取内存文件、凭证、Token 等敏感数据

| # | 文件 | 行号 | 匹配内容 | 风险等级 | 授权方式 | 说明 |
|---|------|------|----------|----------|----------|------|
| 1 | `scripts\permission_checker.py` | 439 | `credential` | 🔴 高 | 即时授权 | 检测到敏感信息访问（字符串常量含敏感关键词） |

### 子进程调用（5 项）
> **权限作用**：调用系统命令或其他可执行文件

| # | 文件 | 行号 | 匹配内容 | 风险等级 | 授权方式 | 说明 |
|---|------|------|----------|----------|----------|------|
| 1 | `scripts\permission_checker.py` | 74 | `SUBPROCESS` | 🔴 高 | 即时授权 | 检测到 subprocess 调用（os.system/subprocess 等） |
| 2 | `scripts\permission_checker.py` | 86 | `Subprocess` | 🔴 高 | 即时授权 | 检测到 subprocess 调用（os.system/subprocess 等） |
| 3 | `scripts\permission_checker.py` | 248 | `subprocess` | 🔴 高 | 即时授权 | 检测到 subprocess 调用（os.system/subprocess 等） |
| 4 | `scripts\permission_checker.py` | 598 | `subprocess` | 🔴 高 | 即时授权 | 检测到 subprocess 调用（os.system/subprocess 等） |
| 5 | `scripts\permission_checker.py` | 606 | `SUBPROCESS` | 🔴 高 | 即时授权 | 检测到 subprocess 调用（os.system/subprocess 等） |

## 授权方式说明

- **即时授权**：每次执行前需获得用户批准
- **统一授权**：首次执行前获得用户批准，后续不再询问
- **静默授权**：无需用户交互，自动执行并记录

## 详细风险列表

1. **[高] 检测到敏感信息访问（字符串常量含敏感关键词）**
   - 位置：`scripts\permission_checker.py` 第 439 行
   - 原因：高风险操作，每次执行前需用户确认

2. **[高] 检测到 subprocess 调用（os.system/subprocess 等）**
   - 位置：`scripts\permission_checker.py` 第 74 行
   - 原因：高风险操作，每次执行前需用户确认

3. **[高] 检测到 subprocess 调用（os.system/subprocess 等）**
   - 位置：`scripts\permission_checker.py` 第 86 行
   - 原因：高风险操作，每次执行前需用户确认

4. **[高] 检测到 subprocess 调用（os.system/subprocess 等）**
   - 位置：`scripts\permission_checker.py` 第 248 行
   - 原因：高风险操作，每次执行前需用户确认

5. **[高] 检测到 subprocess 调用（os.system/subprocess 等）**
   - 位置：`scripts\permission_checker.py` 第 598 行
   - 原因：高风险操作，每次执行前需用户确认

6. **[高] 检测到 subprocess 调用（os.system/subprocess 等）**
   - 位置：`scripts\permission_checker.py` 第 606 行
   - 原因：高风险操作，每次执行前需用户确认
