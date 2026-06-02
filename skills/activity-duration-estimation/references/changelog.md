## 1.3.2 (2026-06-02)

### 改进
- 使用示例重写：从1个紧凑示例扩展为3个完整场景（直接估算/多阶段CPM/搜索辅助），每个展示完整用户输入→系统响应→输出流程
- 触发场景压缩为联防格式，节省空间给核心示例
- Phase 2 紧前关系从代码块精简为自然语言段落
- 正文公式去除冗余行（normal_mean重复direct估算）
- SKILL.md 稳定在 230 行（≤230 合规）

---

## 1.3.1 (2026-06-02)

### 改进
- 新增"限制与边界"章节：任务数量上限(≤50)、OMP约束(O≤M≤P)、循环依赖检测、报告格式说明
- 快速开始新增完整对话示例：用户输入→系统推荐→确认→报告输出的完整链路
- FAQ新增"出错了怎么办？"（验证/约束冲突时的修复建议）
- FAQ新增"最多能算几个任务？"（容量限制说明）
- SKILL.md 触发场景从9行表格压缩为单行联防格式，释放空间给边界说明
- Phase 2依赖类型描述精简

---

## 1.3.0 (2026-06-02)

### 新增功能
- CPM支持四种依赖类型：FS(完成→开始)、SS(开始→开始)、FF(完成→完成)、SF(开始→完成)
- 新增合理性审查层：validate_cpm_input/validate_cpm_result/validate_mc_input/validate_mc_result/validate_overlap_tasks/validate_all
- 审查覆盖：工期非负、O≤M≤P、start≤end、无循环依赖、无自引用、P50≤P90、标准差非负

### 修复
- calc_overlap 空tasks返回缺少duration字段（与空segments返回结构不一致）
- report-template.md 示例日期硬编码（改为 date.today()）

### 改进
- calc_cpm 函数签名兼容新旧格式，旧格式 {2:[1]} 隐式FS保留

---

## 1.2.0 (2026-06-02)

### 新增功能
- CPM关键路径分析：前向传递(ES/EF)+后向传递(LS/LF)+总时差+关键路径提取+循环依赖检测
- 多分布蒙特卡洛：PERT-Beta/三角分布/泊松近似三种分布并行模拟
- 任务重叠分析：扫描线算法，最大重叠数+最长重叠时长
- 甘特图SVG生成：关键路径红色高亮标注，支持CPM结果渲染
- 多分布MC对比SVG：三种分布直方图叠加+均值线+P50/P90标记
- 紧前关系自动规划：自动FS顺序连接+字符串解析(1→2(FS))
- 报告中新增紧前关系表（CPM章节顶部，显示任务依赖及FS/SS/FF/SF类型）
- 分析建议扩展为5维度：工期结论/关键路径风险/重叠影响/进度缓冲/多分布对比

### 架构变更
- 工作流重组：4阶段→5阶段（新增Phase 2紧前关系规划，原Phase 2/3→Phase 3/4）

### 修复
- MC概率密度图和累计概率曲线图数据缺失（补density/binLabels/cumulative数组）
- 重叠分析返回空区间时缺少duration字段导致KeyError
- HTML模板REPORT_DATA注入方式改为{{REPORT_DATA_JSON}}占位符
- 模板header中{{METHOD_USED}}无值问题
- JS initReport未填充meta[1](SUBTITLE)

### 文档
- report-template.md重写为完整数据接口规范（REPORT_DATA 11字段+分析→格式化→报告标准化流程+LLM建议生成5维规范）
- 新增depTable数据接口文档

---

## 1.0.3 (2026-06-02)

### 修复
- 标准化改造+修复反模式格式+扩展FAQ内容+修复术语混用

---

## 1.0.2 (2026-06-02)

### 修复
- audit --fix 自动修正: writing_standards

---

# 更新日志 (Changelog)

## 1.0.1 (2026-06-02)

- 标准化改造：templates/ 迁移至 .standardization/ 数据目录
- 创建 scripts/ 目录（含 __init__.py）
- SKILL.md 拆分至 ≤230 行，符合 R-17 渐进式加载规范
- 添加渐进式文件索引表
- 删除全部耦合性词汇（"借鉴"等）
- 修复前端描述字段与 _meta.json 同步
- _meta.json 精简为 7 标准字段
- 修复 H1 位置（紧跟在 frontmatter 后）
- 修复代码块语言标识
- 修复 FAQ 格式为 Q:/A: 标准格式
- 修复反模式格式：`**错误做法**：`→`**错误做法：**`（冒号归入加粗）
- 修复术语混用："版本更新历史"→"版本更新记录"
- 扩展FAQ内容（OMP来源Q=34字/A=187字，内容完整）
- 修复 skill-standardization 的 fix.py import error（parse_simple_yaml_frontmatter 缺失）
- 扩展 fix_writing_standards 支持 R-18 反模式格式自动修正
