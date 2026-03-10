# SubjectAreas 测试分析文档

> **分析目标**：验证 SubjectAreas 5 大核心能力
> **核心文件**：
> - Prompt: `server/prompts/subjectAreas/querySubjectAreas.prompt`
> - Tool: `server/src/tools/retrieval/getSubjectArea.ts`
> - Node: `server/src/agents/chatAgent/nodes/subjectAreas.ts`
> - Notebook: `experiment/notebooks/subjectArea/querySubjectAreas.ipynb`
> - Notebook: `experiment/notebooks/subjectArea/historyEnhancedSubjectAreas.ipynb`

---

## 系统架构速览

```
用户问题
  │
  ├─── [并行] getSimpleSubjectArea()    ──→ querySubjectAreas.prompt → YAML 解析
  └─── [并行] getCompletedQuery()       ──→ completeQueryByHistory.prompt（有历史时）
         │
         ▼
   有 explicitly_mentioned=true？
         ├── YES → 直接返回（Fast Path）
         └── NO  → getEnhancedSubjectAreas()（Enhanced Path）
                      ├── 有历史 → 用 completedQuery 重新调用 getSimpleSubjectArea()
                      ├── 再检查 explicitly_mentioned=true → 返回
                      ├── 有 contextType → 按 context 过滤 SubModule
                      └── 无匹配 → 按 Module/SubModule 优先级排序，取 Top 1
```

**ContextType 完整映射表**（来自 `shared/types/contextMap.ts`）：

| UI contextType | 内部字符串 | 代码中匹配关键词 |
|---------------|-----------|----------------|
| chart | "visualization dashboard chart" | submodule 含 "chart" |
| crosstab | "visualization dashboard crosstab" | submodule 含 "crosstab" |
| table | "visualization dashboard table" | submodule 含 "table"（不含 freehand）|
| freehand | "visualization dashboard freehand table" | submodule 含 "freehand" |
| worksheet | "data worksheet" | module 含 "worksheet" |
| dashboard | "visualization dashboard" | 无具体过滤（直接走优先级） |
| em | "enterprise manager" | — |

---

## 能力一：Module 识别正确

### 规则梳理

| Module | 关键触发词/场景 | 强制性 |
|--------|--------------|--------|
| Dashboard | 可视化、展示、排序、聚合、格式化 | 默认优先 |
| Data Worksheet | 数据建模、关系、预处理、变量、命名分组（Named Grouping） | 中等 |
| Portal | Join/Link、数据类型变更（双路径触发） | 强制（双路径）|
| Enterprise Manager | 权限/用户/角色/组/审计/系统配置 | **强制覆盖**（忽略问题中其他组件）|

### 风险点

- **EM 强制覆盖**：若问题中同时出现 EM 操作词和 Dashboard 组件名，LLM 可能仍返回 Dashboard，需验证覆盖是否生效
- **Portal 双路径**：Join 场景必须同时返回 `Data Worksheet` 和 `Portal > data model`，漏返任一即为失败

---

## 能力二：SubModule 识别正确

### SubModule 完整清单与识别依据

| SubModule | 归属 Module | 识别依据 | 易混淆点 |
|-----------|-----------|---------|---------|
| chart | Dashboard | 图表类型名（bar/pie/map/gantt/funnel/heatmap）；Axis/Legend/Plot/Target Line/Series | 通用"可视化"词不触发 |
| table | Dashboard | "表格"+"明细"+"隐藏列"+"Form 编辑" | 与 Worksheet data block 易混 |
| crosstab | Dashboard | "透视表"/"交叉制表"/"行列分组"/"Grand Total" | Worksheet 也有 crosstab 格式，需结合 context |
| freehand table | Dashboard | "自由布局"/"自定义表"/"非标准结构表" + cell formula/cell binding | |
| trend&comparison | Dashboard | YoY/MoM/同比/环比/趋势分析/比较分析（**严格触发**）| 时间序列/日期字段**不触发** |
| others | Dashboard | Gauge/Calendar/Slider/Selection/Checkbox/RadioButton/Spinner/Form | |
| data block | Data Worksheet | 数据块/联合/交集/差集/合并/镜像/旋转/条件/表达式列 | |

### 风险点

- **trend&comparison 严格性**：`"show data over time"` 不应触发，`"trend analysis"` 必须触发
- **others 的 Context 回退**：`others` 在代码层会按 contextType 回退为对应子模块，需验证该逻辑正常运行
- **freehand vs table**：问题含 "Table Style" 单独出现时，不应视为显式提及 `table`

---

## 能力三：explicitly_mentioned 判断正确

### 判断规则（来自 Prompt）

```
explicitly_mentioned = true 触发条件（满足任一）：
  1. 直接提及模块/组件名称，且该组件是操作目标
  2. 出现模块独占概念（见下表）
  3. 强制触发词：trend analysis / YoY / MoM / period-over-period

explicitly_mentioned = false 条件（需同时满足全部）：
  1. 未提及任何模块名
  2. 未提及任何独占概念
  3. 模块仅从通用行为推断

特殊例外：
  - "Table Style" 单独出现 → 不视为 table 的 explicit
  - 权限类问题含组件名 → EM 相关 explicit=true，其他组件 explicit 应被忽略
```

### chart 独占概念列表（触发 explicit=true）

`Axis`、`x-axis`、`y-axis`、`Legend`、`Plot`、`Target Line`、`Series`、`bar chart`、`pie chart`、`map`、`heatmap`、`gantt`、`funnel`、`line chart`

### freehand table 独占概念列表（触发 explicit=true）

`cell formula`（单元格级别公式，非系统全局公式）、`cell binding`、`free layout cell grouping`

### 已知历史 BUG（Notebook 观察）

在旧版 `historyEnhancedSubjectAreas.ipynb` 中：
- 问题 `"how to change axis color"` 返回 `explicitly_mentioned: false`
- **当前 Prompt 已修正**：axis 现为 chart 的独占概念，应返回 `true`
- **回归测试必须覆盖此用例**，确认修复生效

---

## 能力四：Prompt 规则是否生效

### 4.1 Group / Aggregate 多模块强制规则

**规则**：检测到 Group 或 Aggregate → 必须同时返回 chart + crosstab + freehand table + Data Worksheet，并**排除** table

### 4.2 Table 双模块原则

**规则**：无上下文时，"table" 同时归属 Dashboard > table 和 Data Worksheet
- 关键词 "layout" → 倾向 Dashboard > table
- 关键词 "cleansing" → 倾向 Data Worksheet

### 4.3 Total / Sorting 规则

- `totals` / `Grand Total` → 包含 crosstab 和 freehand table，**排除** Dashboard > table
- `sort a list` → 包含 table、crosstab、freehand table

### 4.4 trend&comparison 严格性 + 并行提取

- YoY / MoM / period-over-period → **必须**触发 trend&comparison
- "show data over time" / "time series" → **不触发** trend&comparison
- trend&comparison 触发时，并行返回其他相关子模块（chart、crosstab 等）

### 4.5 Join / Data Type 双路径强制规则

- Join / Link → 同时返回 Data Worksheet + Portal > data model，两者 explicit 均为 true
- 数据类型变更 → 同时返回 Data Worksheet + Portal > data model

### 4.6 Concatenation 规则

- union / intersection / minus（差集）操作 → 归属 Data Worksheet > data block，explicit=true

### 4.7 ZERO-MATCH 兜底规则

- 有 contextType 时 → 返回对应 contextType 的 subjectArea，explicit=false
- 无 contextType 时 → 返回 `{Dashboard, explicit=false}` 作为兜底

---

## 能力五：Code 层增强逻辑是否正确

### 5.1 Fast Path：explicitly_mentioned=true 直接返回

**逻辑**：只要结果中存在 ≥1 个 `explicitly_mentioned=true` 的项，立即返回，不进入 Enhanced Path

**关键验证点**：
- 有历史对话时，history 不应覆盖 explicit 结果
- trend&comparison 触发时，parallel 规则追加的 chart/crosstab 不应被过滤

### 5.2 Enhanced Path：Context 过滤逻辑

**逻辑**：无 explicit 时，按 contextType 在 LLM 结果中过滤匹配的 submodule

**Context 过滤映射**：
- contextType=chart → 过滤出含 "chart" 的 submodule
- contextType=crosstab → 过滤出含 "crosstab" 的 submodule；若无匹配但有 `others`，则回退为 crosstab
- contextType=freehand → 过滤含 "freehand" 的 submodule；`others` 回退为 freehand
- contextType=worksheet → 过滤含 "worksheet" 的 module；无结果则透传原结果按优先级排序

### 5.3 Enhanced Path：优先级排序（无 context 匹配时）

**Module 优先级**：Dashboard(0) > Data Worksheet(1) > Others(2)

**SubModule 优先级**（Dashboard 内）：chart(0) > crosstab(1) > freehand(2) > table(3) > others(4)

### 5.4 preferRewriteWithContext 标记

**逻辑**：context 过滤命中时设为 `true`，影响下游 retrieval 策略

| 场景 | preferRewriteWithContext |
|------|--------------------------|
| context 过滤命中 | `true` |
| explicit=true（Fast Path）| `false`（Fast Path 不设置）|
| 无 context，优先级排序路径 | `false` |
| context=worksheet，LLM 返回有 Worksheet 模块 | `true` |

### 5.5 singleModules submodule 强制 undefined

**逻辑**：Data Worksheet、Portal、Enterprise Manager 的 submodule 在代码层强制设为 undefined

| LLM 返回 | 代码层输出 |
|---------|-----------|
| `{module: "Data Worksheet", subModule: "data block"}` | `{module: "Data Worksheet", submodule: undefined}` |
| `{module: "Portal", subModule: "data model"}` | `{module: "Portal", submodule: undefined}` |
| `{module: "Enterprise Manager", subModule: "administration"}` | `{module: "Enterprise Manager", submodule: undefined}` |

> **注意**：singleModules 的 submodule 虽然代码层为 undefined，但下游逻辑（retrieval 策略选择）仍需靠 module 名称区分。需确认 submodule=undefined 不会导致 retrieval 路由错误。

### 5.6 空结果兜底

- LLM 返回 `subjectAreas: []`，无 contextType → `[{module: "Dashboard", submodule: undefined, explicitly_mentioned: false}]`
- LLM 返回 `subjectAreas: []`，contextType=chart → `[{module: "visualization dashboard chart", submodule: undefined, explicitly_mentioned: false}]`

---

## 综合场景分析

### 场景一：有历史对话，无显式指向

```
历史：
  Q: How to create a bar chart?
  A: ...
  Q: How to sort the chart data?
  A: ...

当前问题："How to change the color?"
contextType: —
```

| 验证点 | 期望值 |
|-------|-------|
| getCompletedQuery 输出 | "How to change the color in Dashboard chart"（history 推断） |
| getSimpleSubjectArea（原始问题）| 可能无 explicit |
| Enhanced Path 使用 completedQuery 重跑 | chart，explicit=false |
| 最终 subjectAreas | [Dashboard > chart] |
| preferRewriteWithContext | false（无 contextType）|

### 场景二：有 contextType，问题通用，有 others 命中

```
当前问题："How to configure this component?"
contextType: freehand（"visualization dashboard freehand table"）
```

| 验证点 | 期望值 |
|-------|-------|
| LLM 可能返回 | [{Dashboard > others, false}] |
| Context 过滤（freehand 分支）| 无 freehand submodule → 检查 others → 推断为 freehand |
| 最终 subjectAreas | [Dashboard > freehand] |
| preferRewriteWithContext | true |

### 场景三：显式 + trend 并行

```
当前问题："How to do YoY comparison in a crosstab?"
contextType: —
```

| 验证点 | 期望值 |
|-------|-------|
| explicit 结果 | crosstab（true）+ trend&comparison（true）|
| Fast Path 触发 | YES |
| 最终 subjectAreas | [Dashboard > crosstab, Dashboard > trend&comparison] |
| preferRewriteWithContext | false |

### 场景四：Enterprise Manager 强制覆盖

```
当前问题："How to set read permission for a chart dashboard?"
contextType: chart
```

| 验证点 | 期望值 |
|-------|-------|
| LLM 识别 | Enterprise Manager（permission 强制），不含 Dashboard |
| 代码层 Fast Path | EM 无 explicit（视具体 prompt 结果），可能走 Enhanced |
| 最终 subjectAreas | [Enterprise Manager]，不含 Dashboard > chart |
| contextType 的过滤影响 | 不应将 EM 过滤为 Dashboard > chart |

---

## 测试优先级矩阵

| 优先级 | 测试能力 | 原因 |
|-------|---------|-----|
| P0（必测）| explicitly_mentioned 正确性 | 直接影响 Fast/Enhanced 路径分支 |
| P0（必测）| trend&comparison 严格触发 | 历史高频错误，影响用户意图理解 |
| P0（必测）| Enterprise Manager 强制覆盖 | 权限相关逻辑错误后果严重 |
| P0（必测）| Axis 独占概念回归 | 已知历史 Bug（旧 notebook 返回 false）|
| P1（重要）| Group 多模块强制 | 规则复杂，LLM 容易漏返 |
| P1（重要）| Table 双模块原则 | 歧义场景高频出现 |
| P1（重要）| Context 过滤 + others 回退 | 代码层逻辑 |
| P1（重要）| preferRewriteWithContext 标记 | 影响 retrieval 策略 |
| P2（一般）| singleModules submodule 处理 | 代码层强制处理 |
| P2（一般）| 优先级排序 | 兜底路径 |
| P2（一般）| 空结果兜底 | 边界保护 |

---

## 已知风险与关注点

| 风险 | 描述 | 影响级别 |
|-----|------|---------|
| Axis 回归 Bug | 旧 notebook 中 axis color 返回 explicit=false，当前 prompt 已修正，需回归验证 | High |
| trend&comparison 误触发 | 时间序列/日期字段可能被 LLM 误识别为 trend | High |
| Table Style 例外规则 | LLM 可能将 Table Style 误判为 table 的 explicit | Medium |
| EM 覆盖不彻底 | 含权限词但同时提及组件名，LLM 可能混合返回 Dashboard + EM | High |
| context 过滤截断 explicit | 若 explicit=true 的结果与 contextType 不匹配，Fast Path 应优先，不应被 context 截断 | High |
| singleModules submodule 丢失 | Portal 的 subModule（data model/VPM 等）在代码层被清空，下游可能无法区分 | Medium |
| Enhanced Path 的 completedQuery 质量 | 若 completedQuery 质量差，重跑 getSimpleSubjectArea 结果更差（噪声放大）| Medium |
| others 的 context 回退 | 代码中 `othersArea` 检测仅靠 submodule 含 "others" 字符串，若 LLM 返回其他描述则回退失效 | Medium |

---

## 测试用例表

| CaseID | 场景/类别 | User Query | 预期 module | 预期 subModule | explicitly_mentioned | 设计意图 |
|--------|-----------|------------|-------------|----------------|----------------------|---------|
| TC-M-01 | Module 基础：Dashboard 语义推断 | "How to visualize data in a report?" | Dashboard | chart | false | 通用可视化词语义推断到 Dashboard，chart 为默认最高优先级子模块，无独占概念出现 |
| TC-M-02 | Module 基础：Data Worksheet 语义推断 | "How to preprocess raw data before modeling?" | Data Worksheet | — | false | 数据预处理是 DW 核心场景，仅语义推断，"Data Worksheet" 未出现 |
| TC-M-03 | Module 基础：Enterprise Manager 语义推断 | "How to configure system settings?" | Enterprise Manager | — | false | 系统配置归属 EM，语义推断，无 "Enterprise Manager" 关键词，不触发强制规则 |
| TC-M-04 | Module 基础：Portal 直接命名 | "How to manage data sources in the portal?" | Portal | — | true | "portal" 直接出现，显式命名 module |
| TC-M-05 | Module 显式，subModule 语义推断 ★新增 | "How to set the background color in the Dashboard?" | Dashboard | chart（语义推断） | true | "Dashboard" 显式出现故 explicit=true，但无 subModule 名称，subModule 由优先级规则推断；验证 module 显式即可触发 true |
| TC-C-01 | chart：图表类型名称直接触发 | "How to create a funnel chart?" | Dashboard | chart | true | "chart" 作为 subModule 名直接出现；module 由语义推断，subModule 显式命名 |
| TC-C-02 | chart：独占概念触发（Legend） | "How to change the legend position?" | Dashboard | chart | true | "legend" 是 chart 独占概念，无需 "chart" 词出现即可触发 explicit=true；代表所有独占概念触发路径 |
| TC-C-03 | chart：Axis 独占概念（历史 Bug 回归）⚠️ | "How to change the axis color?" | Dashboard | chart | true | **已知历史 Bug**：旧 prompt 对此用例返回 false，当前 prompt 修正后必须为 true，必须回归验证 |
| TC-C-06 | chart：语义推断（无独占词） | "How to change the color of the visualization?" | Dashboard | chart | false | 通用可视化操作，无独占概念或模块名，仅语义推断为 chart；验证无独占词时 explicit=false |
| TC-C-07 | Module 与 subModule 均显式提到 ★新增 | "How to format the legend in the Dashboard chart?" | Dashboard | chart | true | "Dashboard"（module）+ "chart"（subModule）均显式出现，"legend" 同时作为独占概念强化；验证双重命名场景 |
| TC-CT-01 | crosstab：直接命名 | "How to sort rows in a crosstab?" | Dashboard | crosstab | true | "crosstab" 直接出现，显式命名 subModule |
| TC-CT-02 | crosstab：Grand Total 规则（排除 table） | "How to display the Grand Total in a report?" | Dashboard | crosstab / freehand table | false | Grand Total 规则：必须包含 crosstab + freehand table，且排除 Dashboard > table；无显式 subModule 名 |
| TC-CT-03 | crosstab：透视表语义推断 | "How to build a pivot table with row and column grouping?" | Dashboard | crosstab | false | "pivot table" + 行列分组语义触发 crosstab，"crosstab" 未出现，语义推断，explicit=false |
| TC-FT-01 | freehand table：直接命名 | "How to design a custom layout in a freehand table?" | Dashboard | freehand table | true | "freehand table" 直接出现，显式命名 subModule |
| TC-FT-02 | freehand table：cell formula 独占概念 | "How to write a cell formula for custom calculation?" | Dashboard | freehand table | true | "cell formula" 是 freehand table 独占概念，代表所有 freehand table 独占触发路径 |
| TC-TR-01 | trend&comparison：YoY 强制触发 | "How to create a YoY comparison report?" | Dashboard | trend&comparison | true | YoY 是强制触发词，代表 YoY / MoM / period-over-period 三类触发词；必须返回 trend&comparison |
| TC-TR-04 | trend&comparison：时间序列不触发（负面） | "How to display monthly sales as a time series?" | Dashboard | chart（不含 trend&comparison） | false | 时间序列不应触发 trend&comparison；代表所有"时间范畴"负面用例，验证严格性 |
| TC-OT-01 | others：具体组件命名 | "How to add a slider to filter report data?" | Dashboard | others | true | Slider 是 others 类组件的代表性触发词，直接命名触发 |
| TC-TB-01 | table：Dashboard > table 直接命名 | "How to hide a column in a table?" | Dashboard | table | true | "table" 直接出现，"隐藏列" 是 Dashboard > table 特征，确认归属 Dashboard 而非 DW |
| TC-TB-02 | table：Table Style 例外规则（负面） | "How to apply a Table Style to the report?" | Dashboard | chart（语义推断） | false | "Table Style" 单独出现是例外规则，不触发 table 的 explicit=true |
| TC-DW-01 | Data Worksheet：语义推断（表达式列） | "How to create a calculated expression column?" | Data Worksheet | data block | false | 表达式列是 DW 特有概念，语义推断，"Data Worksheet" 未出现，explicit=false |
| TC-DW-02 | Data Worksheet：union concatenation 规则 | "How to perform a union of two data blocks?" | Data Worksheet | data block | true | "data block" 直接出现 + union 触发 concatenation 规则；代表所有 concatenation 触发路径 |
| TC-EM-01 | Enterprise Manager：基础关键词触发 | "How to set read permission for a specific user?" | Enterprise Manager | — | true | permission 是 EM 强制触发词的代表，代表 permission / user / role / audit 所有触发路径 |
| TC-EM-05 | Enterprise Manager：强制覆盖（含 subModule 干扰词） | "How to create a user role for the chart module?" | Enterprise Manager | — | true | "chart" 出现但 role/user 触发 EM 强制覆盖，结果中不应出现 Dashboard > chart |
| TC-EM-06 | Enterprise Manager：强制覆盖（含 module 干扰词） | "How to set permissions for a dashboard?" | Enterprise Manager | — | true | "dashboard" 出现但 permissions 触发 EM 强制覆盖；与 TC-EM-05 区分：干扰在 module 级别而非 subModule 级别 |
| TC-P-01 | Portal 双路径：Join 规则 | "How to join two data tables?" | Data Worksheet / Portal | — | true（均） | Join 触发双路径强制规则，代表 Join / Link / 数据类型变更 所有双路径场景；两者 explicit 均为 true |
| TC-SP-01 | 特殊规则：Group 多模块强制（排除 table） | "How to group data by category?" | Dashboard / Data Worksheet | chart / crosstab / freehand table（排除 table） | false | Group 强制规则：必须同时返回 chart + crosstab + freehand table + DW，且严格排除 Dashboard > table |
| TC-SP-02 | 特殊规则：Table 双模块原则（无 context） | "How to create a table to display records?" | Dashboard / Data Worksheet | table（Dashboard）/ —（DW） | true | 无 context 时 "table" 同时归属 Dashboard > table 和 Data Worksheet；"table" 直接出现故 explicit=true |
| TC-SP-03 | 特殊规则：trend 与 chart 并行返回 | "How to do a YoY analysis in a bar chart?" | Dashboard | trend&comparison / chart | true（均） | YoY 触发 trend&comparison，"bar chart" 触发 chart，两子模块必须并行返回，均为 explicit=true |
| TC-MX-01 | 多 subModule 均显式命名 ★新增 | "How to display data in a table or crosstab?" | Dashboard | table / crosstab | true（均） | "table" 和 "crosstab" 均显式出现，验证两个 subModule 并行识别且各自 explicit=true；与 TC-SP-03 区分：此处由用户主动命名而非规则触发 |
| TC-FB-01 | ZERO-MATCH fallback ★新增 | "What is the capital of France?" | Dashboard | — | false | 完全无关的问题，触发 ZERO-MATCH 兜底规则，返回 Dashboard 作为默认 module，explicit=false |

---

## 用例覆盖统计

| 类别 | 用例数 | 覆盖规则 |
|------|--------|---------|
| Module 基础识别 | 5 | Dashboard / DW / EM / Portal 语义推断；Module 显式+subModule 推断（★新增）|
| chart 子模块 | 5 | 类型名直接触发；独占概念触发（Legend 代表）；历史 Bug 回归（Axis）；语义推断；双重命名（★新增）|
| crosstab 子模块 | 3 | 直接命名；Grand Total 规则（排除 table）；透视表语义推断 |
| freehand table 子模块 | 2 | 直接命名；cell formula 独占概念 |
| trend&comparison | 2 | YoY 强制触发（代表三类触发词）；时间序列不触发（负面）|
| others 子模块 | 1 | Slider 组件命名（代表 others 触发路径）|
| table 子模块 | 2 | 直接命名；Table Style 例外规则（负面）|
| Data Worksheet | 2 | 语义推断；union concatenation（代表所有 concatenation）|
| Enterprise Manager | 3 | permission 基础触发（代表四类触发词）；含 subModule 干扰的强制覆盖；含 module 干扰的强制覆盖 |
| Portal 双路径 | 1 | Join 规则（代表所有双路径触发场景）|
| 特殊规则 | 3 | Group 多模块强制（排除 table）；Table 双模块原则；trend+chart 并行提取 |
| 多 subModule 并列 | 1 | 用户主动命名两个 subModule（★新增）|
| ZERO-MATCH fallback | 1 | 无关问题兜底（★新增）|
| **合计** | **31** | |

---

## explicitly_mentioned 判断依据说明

| 触发类型 | 判断结果 | 代表用例 |
|---------|---------|---------|
| 直接出现 module 名称 | true | TC-M-04、TC-M-05、TC-C-07 |
| 直接出现 subModule 名称 | true | TC-C-01、TC-CT-01、TC-FT-01、TC-TB-01 |
| 出现 chart 独占概念（legend/axis/Target Line/Series 等）| true | TC-C-02、TC-C-03、TC-C-07 |
| 出现 freehand table 独占概念（cell formula/cell binding）| true | TC-FT-02 |
| 出现 trend 强制触发词（YoY/MoM/period-over-period）| true | TC-TR-01、TC-SP-03 |
| EM 强制触发词（permission/user/role/audit）| true | TC-EM-01、TC-EM-05、TC-EM-06 |
| Portal 双路径触发词（join/link/data type change）| true（均）| TC-P-01 |
| 仅通用行为/语义推断 | false | TC-M-01、TC-M-02、TC-C-06、TC-DW-01 |
| Table Style 例外规则 | false | TC-TB-02 |
| ZERO-MATCH 兜底 | false | TC-FB-01 |
