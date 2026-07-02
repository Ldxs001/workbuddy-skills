---
risk_level: LOW
high_risk_operations:
  - none
data_access: none
network_access: none
external_services: none
filesystem_write:
  - user-specified output directory
description: >
  SVG 拼接工具，仅写入用户指定的输出目录，
  不修改系统文件
---

# 权限声明

> 本文件由 skill-standardization 权限扫描工具自动生成与维护。
> 声明本技能对文件系统、网络、进程等资源的访问权限。

## 风险评估

| 风险类型 | 风险等级 | 说明 |
|---------|:--------:|------|
| 文件系统访问 | 🟢 低 | 用户指定的输出目录写入 SVG 文件 |
| 网络请求 | 🟢 低 | 无网络请求 |
| subprocess 调用 | 🟢 低 | 无子进程调用 |
| 数据删除 | 🟢 低 | 无自动删除操作 |

**综合风险等级**：LOW

## 权限说明

本技能不执行以下操作：
- 不访问网络
- 不执行系统命令
- 不删除或修改用户系统文件
- 不收集或上传任何数据

所有 SVG 文件生成操作均在用户指定的输出目录内完成。
