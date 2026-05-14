---
name: drawio-diagram
version: 2.0.0
description: draw.io 自动做图 Skill。当用户要求画图、生成图表、做架构图、流程图、UML、ER图、时序图、思维导图等时触发。生成 .drawio 文件并用 draw.io 打开。支持思考-确认-迭代-版本回溯的完整工作流。
tags: [diagram, drawio, flowchart, architecture, uml, er, visualization]
agent_created: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# draw.io 自动做图 Skill

## 触发条件

当用户提出以下意图时触发：
- "画一个xxx图"、"生成xxx图"、"做一个图表"
- "架构图"、"流程图"、"UML类图"、"ER图"、"时序图"、"思维导图"
- "用draw.io画"、"生成drawio文件"
- "画网络拓扑"、"画组织架构"、"画系统架构"
- "按照这个示例改成..."、"参照这个图改..."、"基于这个样式做一个..."
- 用户提供截图/示例文件并要求生成类似图表
- 任何涉及 draw.io / diagrams.net 的需求

## 核心文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 核心库 | `C:\Users\sm001\WorkBuddy\workbuddy-skills\skills\drawio-diagram\drawio_gen.py` | 节点/连线/容器/XML生成 |
| 模板库 | `C:\Users\sm001\WorkBuddy\workbuddy-skills\skills\drawio-diagram\drawio_templates.py` | 8种图表模板 |
| Agent入口 | `C:\Users\sm001\WorkBuddy\workbuddy-skills\skills\drawio-diagram\drawio_agent.py` | CLI/自然语言解析 |
| 版本管理 | `C:\Users\sm001\WorkBuddy\workbuddy-skills\skills\drawio-diagram\drawio_version.py` | 5版本回溯系统 |
| draw.io | `C:\Program Files\draw.io\draw.io.exe` | 本地安装路径 |
| 输出目录 | `C:\Users\sm001\WorkBuddy\Claw\reports\` | 所有图表输出到此 |

---

## 执行流程（4阶段工作流）

### 阶段1：思考分析（Think）

**不要直接动手画图！** 先分析用户需求，输出结构化的思考结果。

#### 1.1 判断输入类型

用户输入可能包括：
- **自然语言描述**："画一个微服务架构图"
- **示例文件/截图**：用户提供一张图要求参照或修改
- **内容+要求**："把这段文字整理成流程图"或"按照这个示例改成XX风格"
- **模糊需求**：用户说不清楚要什么图，需要你建议

#### 1.2 判断图表类型

根据用户描述自动判断：
- 流程图：含"流程"、"步骤"、"审批"、"顺序"
- 架构图：含"架构"、"分层"、"微服务"、"技术栈"、"系统设计"
- UML类图：含"类图"、"继承"、"接口"、"面向对象"
- ER图：含"ER"、"实体关系"、"数据库设计"、"表关系"
- 树形图：含"树"、"组织架构"、"目录结构"、"层级"
- 时序图：含"时序"、"交互"、"消息流"、"调用链"
- 思维导图：含"思维导图"、"脑图"、"发散"
- 网络拓扑：含"网络"、"拓扑"、"部署"、"服务器集群"
- **无法确定**：进入方案建议模式，列出可能的图表类型让用户选择

#### 1.3 输出思考结果

向用户展示你的分析，格式如下：

```
📊 需求分析

类型判断：[确定的图表类型或"需要确认"]
输入类型：[自然语言/示例文件/内容+要求/模糊需求]
复杂度：[简单/中等/复杂]

初步方案：
- 图表类型：[类型]
- 布局方向：[水平/垂直/自定义]
- 预计节点数：[数量]
- 关键元素：[列出主要节点和关系]
- 配色方案：[建议颜色]

是否按照此方案执行？
```

### 阶段2：方案确认（Confirm）

**必须等待用户确认后才能动手画图！**

#### 2.1 确认方式

使用 AskUserQuestion 工具向用户展示方案选项：
- 选项1：按方案执行（推荐）
- 选项2：调整某些参数（如布局、配色、节点内容）
- 选项3：换一种图表类型
- 选项4：用户自行输入补充说明

#### 2.2 特殊场景处理

**用户提供示例图/截图时**：
1. 分析示例图的结构、布局、样式
2. 列出你从示例中提取到的设计元素
3. 询问用户要保留哪些、修改哪些

**用户要求"按照这个改成..."时**：
1. 理解原始图表的结构
2. 明确哪些要保留、哪些要替换
3. 列出新内容的对应关系

**用户需求模糊时**：
1. 主动推荐2-3种适合的图表类型
2. 每种类型附简要说明和适用场景
3. 让用户选择或补充信息

### 阶段3：迭代修改（Iterate）

**在初始版本基础上进行修改，不是每次从头重做！**

#### 3.1 首次生成

1. 确认方案后，生成v1版本
2. 自动初始化版本管理（`drawio_version.py init`）
3. 用 draw.io 打开预览
4. 展示版本信息：`[v1] 初始版本`

#### 3.2 迭代修改流程

用户提出修改意见后：
1. **保存当前版本**：`drawio_version.py save <文件> "<修改描述>"`
2. **在当前文件基础上修改**：读取当前 .drawio 文件，定位需要修改的节点/连线，精确修改
3. **版本递增**：每次修改自动递增版本号（v1→v2→v3→v4→v5）
4. **展示版本变更**：`[v2] 修改了XX节点颜色`
5. **重新打开预览**

#### 3.3 修改操作类型

- 调整节点位置/大小
- 修改节点文本/样式/颜色
- 添加/删除节点或连线
- 调整布局（间距、对齐、排列）
- 修改连线样式/箭头方向
- 添加/删除容器/分组
- 整体风格调整（配色方案、字体等）

#### 3.4 修改原则

- **精确修改**：只改需要改的部分，不动其他节点
- **相对坐标**：容器子节点用相对坐标
- **保存版本**：每次修改前先 save 当前状态
- **说明变更**：每次修改后告知用户改了什么

### 阶段4：版本回溯（Version Control）

最多保留5个版本，支持随时回溯。

#### 4.1 版本管理命令

```bash
# 初始化版本管理（v1创建时自动执行）
python C:\Users\sm001\WorkBuddy\2026-05-13-task-1\drawio_version.py init <文件.drawio> "初始版本"

# 保存新版本（每次修改前执行）
python C:\Users\sm001\WorkBuddy\2026-05-13-task-1\drawio_version.py save <文件.drawio> "修改了XX"

# 查看版本历史
python C:\Users\sm001\WorkBuddy\2026-05-13-task-1\drawio_version.py list <文件.drawio>

# 恢复到指定版本
python C:\Users\sm001\WorkBuddy\2026-05-13-task-1\drawio_version.py restore <文件.drawio> v2

# 查看版本状态
python C:\Users\sm001\WorkBuddy\2026-05-13-task-1\drawio_version.py status <文件.drawio>
```

#### 4.2 版本自动管理规则

- **最大5版本**：超过5个时自动删除最旧版本
- **修改前自动保存**：每次迭代修改前先 save
- **恢复前自动备份**：恢复旧版本前先保存当前状态
- **版本存储位置**：`<输出目录>/.drawio_versions/<文件名>/v1/...`

#### 4.3 向用户展示版本信息

```
📋 版本历史
  v1  2026-05-13 09:30  初始版本                    2.3KB  <-- current
```

用户可以随时要求"回退到v2"或"看一下v1的样子"。

---

## 快捷模式

以下场景可以跳过方案确认，直接生成：
1. **简单流程图**：3-5个步骤的线性流程
2. **明确的模板调用**：用户给出完整的JSON spec
3. **已确认方案后的迭代修改**：用户确认过方案后的修改

---

## 生成图表

### 方式A - Python API调用（推荐）

```python
import sys
sys.path.insert(0, r"C:\Users\sm001\WorkBuddy\2026-05-13-task-1")
from drawio_templates import *

# 流程图
builder = create_flowchart(["开始", "处理", "结束"])
builder.save("output.drawio")

# 架构图
builder = create_architecture([
    {"name": "Frontend", "components": ["React", "Vue"], "color": Styles.BLUE_NODE},
    {"name": "Backend", "components": ["API", "Auth"], "color": Styles.GREEN_NODE},
])
builder.save("output.drawio")

# 自定义（完全控制）
from drawio_gen import DrawIOBuilder, Styles
builder = DrawIOBuilder(name="My Diagram")
builder.add_node("Node1", 100, 100, 120, 60, style=Styles.BLUE_NODE)
builder.add_node("Node2", 100, 220, 120, 60, style=Styles.GREEN_NODE)
builder.connect(node1, node2, "label")
builder.save("output.drawio")
```

### 方式B - CLI调用

```bash
cd C:\Users\sm001\WorkBuddy\2026-05-13-task-1
python drawio_agent.py "画一个用户登录流程图：输入账号 → 验证 → 查询数据库 → 返回结果" --open
python drawio_agent.py spec.json --open  # JSON模式
```

### 方式C - JSON spec文件

```json
{
  "type": "flowchart",
  "title": "用户登录",
  "steps": ["输入账号", "验证密码", "查询数据库", "返回结果"]
}
```

支持的type：`flowchart`, `architecture`, `class_diagram`, `er_diagram`, `tree`, `sequence`, `mindmap`, `network`

### 打开预览

```bash
"C:\Program Files\draw.io\draw.io.exe" "生成的文件路径"
```

---

## API参考

### 核心库 (drawio_gen)

- `DrawIOBuilder(name)` - 创建画布
- `builder.add_node(label, x, y, w, h, style, parent_id)` - 添加节点
- `builder.add_edge(source_id, target_id, label, style)` - 添加连线
- `builder.add_container(label, x, y, w, h, style)` - 添加容器
- `builder.connect(src_node, tgt_node, label, style)` - 连接两个节点
- `builder.save(filepath)` - 保存文件
- `Styles.*` - 20+预设样式

### 模板库 (drawio_templates)

- `create_flowchart(steps, title, direction)` - 流程图
- `create_architecture(layers, title)` - 分层架构图
- `create_class_diagram(classes, title)` - UML类图
- `create_er_diagram(entities, title)` - ER实体关系图
- `create_tree(root, children, x, y)` - 树形/组织图
- `create_sequence_diagram(actors, messages, title)` - 时序图
- `create_mindmap(center, branches, title)` - 思维导图
- `create_network_topology(devices, connections, title)` - 网络拓扑图

### 布局工具

- `vertical_layout(count, x, y, w, h, gap)` - 垂直排列
- `horizontal_layout(count, x, y, w, h, gap)` - 水平排列
- `grid_layout(rows, cols, x, y, w, h, gap_x, gap_y)` - 网格排列
- `auto_size_node(label)` - 根据文本自动计算节点大小

### 版本管理 (drawio_version)

```python
import sys
sys.path.insert(0, r"C:\Users\sm001\WorkBuddy\2026-05-13-task-1")
from drawio_version import VersionManager

vm = VersionManager(base_dir=r"C:\Users\sm001\WorkBuddy\2026-05-13-task-1")
vm.init("output.drawio", "初始版本")
vm.save_version("output.drawio", "修改了颜色")
vm.list_versions("output.drawio")
vm.restore_version("output.drawio", "v2")
vm.status("output.drawio")
```

### 样式预设

**节点样式**: DEFAULT_NODE, BLUE_NODE, GREEN_NODE, ORANGE_NODE, RED_NODE, PURPLE_NODE, YELLOW_NODE, CYAN_NODE, GRAY_NODE, PINK_NODE

**特殊形状**: DIAMOND(菱形), CYLINDER(圆柱/数据库), CLOUD(云), CIRCLE(圆), HEXAGON(六边形), PARALLELOGRAM(平行四边形), DOCUMENT(文档), NOTE(便签)

**标题样式**: HEADER_BLUE, HEADER_GREEN, HEADER_ORANGE, HEADER_RED, HEADER_GRAY

**连线样式**: DEFAULT_EDGE, BOLD_EDGE, DASHED_EDGE, RED_EDGE, BLUE_EDGE, GREEN_EDGE, GRAY_EDGE, NO_ARROW, DIAMOND_ARROW, OPEN_ARROW

## 坐标系规则

- 画布坐标：左上角(0,0)，X向右增大，Y向下增大
- **容器子节点坐标是相对于容器的**：parent_id指向容器时，子节点x/y是相对于容器左上角的偏移
- 页面默认：1169x827 (A4横向)
- 建议起始坐标：x>=40, y>=40

## 布局精度规则

### 思维导图 (create_mindmap)

**布局策略**：
- 中心节点在画布中央，宽度根据文本自适应
- 分支节点均匀分布在中心周围（半径220）
- 子节点排列方向与分支方向垂直：
  - 上下分支 → 子节点水平排列
  - 左右分支 → 子节点垂直排列
- 所有节点宽度根据文本自适应（中文字符1.8倍宽度）
- 子节点间距最小30px，自动调整避免重叠
- 连线使用正交路由（orthogonalEdgeStyle）

**精确参数**：
```
中心节点: 字体16px, 高度60, 内边距30px
分支节点: 字体13px, 高度50, 内边距24px, 半径220
子节点:   字体11px, 高度40, 内边距20px, 间距30px
```

### 架构图 (create_architecture)

**布局策略**：
- 画布宽度1100，左右边距40
- 容器宽度 = 画布宽 - 2*边距 = 1020
- 容器header高度28px（swimlane startSize）
- 容器内边距：左右20px，上下12px
- 子节点高度50px，水平间距16px
- 子节点宽度按可用空间均匀分配
- 层间距30px
- 子节点使用相对坐标（parent_id指向容器）

**精确参数**：
```
CANVAS_W = 1100, MARGIN_X = 40, MARGIN_Y = 40
CONTAINER_W = 1020
CONTAINER_HEADER_H = 28
CONTAINER_PAD_X = 20, CONTAINER_PAD_Y = 12, CONTAINER_BOTTOM_PAD = 12
COMP_MIN_W = 100, COMP_H = 50, COMP_GAP_X = 16
LAYER_GAP = 30
```

## 连线连接点规则

### 连接点定义
- `0` = 顶部 (Top)
- `1` = 右侧 (Right)
- `2` = 底部 (Bottom)
- `3` = 左侧 (Left)

### 思维导图连线

**中心→分支**：
| 分支方向 | sourcePort (中心) | targetPort (分支) |
|----------|-------------------|-------------------|
| 上       | 0 (顶部输出)      | 2 (底部输入)      |
| 下       | 2 (底部输出)      | 0 (顶部输入)      |
| 左       | 3 (左侧输出)      | 1 (右侧输入)      |
| 右       | 1 (右侧输出)      | 3 (左侧输入)      |

**分支→子节点**：
| 子节点位置 | sourcePort (分支) | targetPort (子节点) |
|------------|-------------------|---------------------|
| 上方       | 0 (顶部输出)      | 2 (底部输入)        |
| 下方       | 2 (底部输出)      | 0 (顶部输入)        |
| 左侧       | 3 (左侧输出)      | 1 (右侧输入)        |
| 右侧       | 1 (右侧输出)      | 3 (左侧输入)        |

### XML输出（关键）

draw.io 通过 **style 字符串中的 `exitX`/`exitY`/`entryX`/`entryY`** 控制连线出入点，**不是** mxCell 的 sourcePort/targetPort 属性。

正确做法（在 `build_xml()` 中将端口信息写入 edge style）：
```
exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;
```

错误做法（draw.io 不认这个属性，直接忽略）：
```xml
<mxCell ... source="node1" target="node2" sourcePort="0" targetPort="2">
```

### 连线路由样式

| 图表类型 | 推荐路由 | style |
|----------|----------|-------|
| 思维导图 | 直线 | `edgeStyle=none;html=1;` |
| 流程图 | 正交折线 | `edgeStyle=orthogonalEdgeStyle;...` |
| 架构图 | 正交虚线 | `edgeStyle=orthogonalEdgeStyle;...dashed=1;...` |
| 时序图 | 直线 | `edgeStyle=none;html=1;` |

## 输出规范

- 输出目录：`C:\Users\sm001\WorkBuddy\2026-05-13-task-1\`
- 文件命名：`{类型}_{描述}.drawio`，如 `architecture_microservice.drawio`
- 生成后自动用 draw.io 打开预览
- 交付附件给用户
- 每次生成/修改后初始化或更新版本管理

## 已知问题与修复记录

### 2026-05-13 思维导图布局修复

**问题**：子节点使用极坐标计算位置，导致：
1. 子节点坐标超出画布（负坐标或大于1169/827）
2. 子节点间距不足，3个以上时重叠
3. 文本宽度固定（100px），中文字符被截断
4. 连线交叉混乱

**修复**：
1. 重写 `_sub_layout()` 函数，改为笛卡尔坐标系
2. 子节点排列方向与分支方向垂直（上下分支→水平排列，左右分支→垂直排列）
3. 节点宽度根据文本自适应：`_text_width()` 中文字符1.8倍宽度
4. 子节点间距最小30px，根据数量动态调整
5. 所有坐标限制在画布范围内

**验证**：AI技术思维导图（4分支×3子节点）测试通过，所有节点在画布内，无重叠，文本完整显示。

### 2026-05-13 思维导图连线修复

**问题**：连线混乱，交叉、方向不对

**根因**：
1. `build_xml()` 没有将 `source_port`/`target_port` 写入 XML
2. `create_mindmap()` 没有根据分支方向指定连接点

**修复**：
1. `drawio_gen.py build_xml()`：Edge 生成时添加 `sourcePort`/`targetPort` 属性
2. `drawio_templates.py create_mindmap()`：根据分支/子节点方向指定正确的 sourcePort/targetPort

**连接点定义**：0=顶部, 1=右侧, 2=底部, 3=左侧

### 2026-05-13 连线端口传递方式修复

**问题**：`sourcePort`/`targetPort` XML 属性被 draw.io 完全忽略，连线依然乱

**根因**：draw.io 不识别 mxCell 的 `sourcePort="0"` 属性，只认 style 字符串里的 `exitX`/`exitY`/`entryX`/`entryY`

**修复**：`build_xml()` 中将端口映射为坐标，写入 edge style 字符串：
- port 0 (顶部) → `exitX=0.5;exitY=0;`
- port 1 (右侧) → `exitX=1;exitY=0.5;`
- port 2 (底部) → `exitX=0.5;exitY=1;`
- port 3 (左侧) → `exitX=0;exitY=0.5;`

### 2026-05-13 思维导图连线路由修复

**问题**：连线到处拐直角，非常丑

**根因**：默认 EdgeStyle 使用 `orthogonalEdgeStyle`（正交路由），思维导图不适合

**修复**：思维导图所有连线改用 `edgeStyle=none`（直线连接）
