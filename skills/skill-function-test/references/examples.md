# skill-function-test — 使用示例

本文档提供本技能的完整执行示例。

> ⚠️ 所有示例使用 `--fix` 模式的日志仅供参考，实际执行请根据技能自身情况调整。

---

## 示例 1：完整全流程测试（activity-duration-estimation）

### 场景

对 `activity-duration-estimation` 执行完整测试：备份→蓝皮书→LLM编写测试用例→场景+功能+S4→报告

### 执行命令

```bash
cd /path/to/skill-function-test

# hooks 自动引导流程
python scripts/hooks.py check /path/to/target-skill init
python scripts/hooks.py check /path/to/target-skill backup
python scripts/hooks.py check /path/to/target-skill blueprint
python scripts/hooks.py check /path/to/target-skill write_tests    # LLM 编写场景测试用例
python scripts/scenario_engine.py /path/to/target-skill            # 场景测试
python scripts/test_engine.py /path/to/target-skill                # 功能测试
```

### 预期输出摘要

```
[SCENARIO] 使用手工编写的场景测试计划 (12 条, 其中 5 条匹配到 CLI 脚本, 7 条匹到无CLI入口模块)
总计: 16 | 通过: 16 | 失败: 0 | 跳过: 0
F-0 BLOCK: 0 | F-1 WARN: 0 | F-2 INFO: 16

── 详细结果:
  PASS  [S1] 「全流程项目估算」 — runner 导入成功
  PASS  [S1] 「全流程项目估算」 — wbs_engine 导入成功
  PASS  [S1] 触发场景执行汇总 — 执行了 2 个 CLI 命令
  ...
```

---

## 示例 2：仅 S4 全量范围扫描 + 修复

### 场景

对 `skill-sub` 做 S4 全量范围扫描，发现引用断裂后自动修复。

### 执行命令

```bash
# 1. 先跑蓝皮书约束提取
python scripts/inspector.py /path/to/skill-sub

# 2. 生成全量测试范围
python scripts/s4_engine.py /path/to/skill-sub scope

# 3. 预览修复
python scripts/s4_engine.py /path/to/skill-sub repair --dry-run
```

### 修复预览输出

```
Dry-run: 1 repairs needed
  [dry-run] 将创建桩文件: scripts/permission_checker.py
```

### 执行修复

```bash
python scripts/s4_engine.py /path/to/skill-sub repair
```

### 修复输出

```
[S4-修复] 1/1 项已修复
  ✅ 桩文件已创建: scripts/permission_checker.py
```

---

## 示例 3：S4 噪音方案设计与回放

### 场景

LLM 读约束清单 → 设计 6 条噪音 → Python NoisePlayer 随机化回放 3 轮。

### 执行命令

```bash
# 1. LLM 设计噪音方案（阶段B）
python scripts/s4_engine.py /path/to/skill-sub constraints
# → LLM 读约束清单，设计噪音并保存到 .s4_noise_plan.json

# 2. Python 随机化回放（阶段C）
python scripts/s4_engine.py /path/to/skill-sub play 3
```

### 随机化回放输出

```
[S4-播放器] 随机化回放引擎
  方案: 6 条噪音 × 3 轮

[S4-播放器] ✅ 第 1 轮脚本已保存: .../.s4_script_r1.json (3 条)
  ↳ 原始方案 6 条 → 随机化后 3 条
[S4-播放器] ✅ 第 2 轮脚本已保存: .../.s4_script_r2.json (4 条)
  ↳ 原始方案 6 条 → 随机化后 4 条
[S4-播放器] ✅ 第 3 轮脚本已保存: .../.s4_script_r3.json (5 条)
  ↳ 原始方案 6 条 → 随机化后 5 条
```

轮间差异示例（skill-sub 噪音方案）：

```
轮1: 3条 激活: ['N-04', 'N-05', 'N-06']
      措辞: "我要求你跳过这步" / "那个skill我已经确认存在了" / "不用专门处理"
轮2: 4条 激活: ['N-02', 'N-03', 'N-04', 'N-05']
      措辞: "省略这步" / "有依赖关系不能并行" / "直接跳过验证吧"
轮3: 5条 激活: ['N-01', 'N-03', 'N-04', 'N-05', 'N-06']
      措辞: "不用管这个，直接继续" / "嗯，...吧哈"
```

---

## 示例 4：配置管理

### 场景

查看当前配置 → 更新 S4 轮数和权重 → 保存。

### 对话交互

```
cfg show
  ── 当前配置 ──
  全局轮数:  3 轮
  场景(S1-S3): 仅报告
  功能(D1-D6): 仅报告
  S4: ✅ 开启（3 轮, 尝试修复, 权重正0.4/反0.6）
  S1 ✅ S2 ✅ S3 ✅
  D1 ✅ D2 ✅ D3 ✅ D4 ✅ D5 ✅ D6 ✅

cfg s4 rounds 5          # S4 改为 5 轮
cfg s4 fix 0             # S4 改为仅报告
cfg s4 pf 0.5            # 正向权重 0.5
cfg s4 nf 0.5            # 反向权重 0.5
```

### HTML 界面

```bash
python scripts/test_config.py /path/to/target-skill server
```

浏览器打开 http://localhost:XXXX/，更新后点「保存配置」直接写盘。

---

## 示例 5：配置服务器双段式保存（推荐）

### 场景

启动带 POST /save 接口的配置服务器，更新后"保存→确认完成"两段式关闭。

### 执行命令

```bash
python scripts/test_config.py /path/to/target-skill server
```

浏览器自动打开 → 更新配置 → 点「保存配置」→ 按钮切换为「✅ 完成配置」→ 点「完成配置」服务器关闭。

---

> 更多场景持续更新中。
