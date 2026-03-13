# SubjectAreas 测试分析文档

> **分析目标**：验证 SubjectAreas 5 大核心能力
> **核心文件**：
> - Prompt: `server/prompts/subjectAreas/querySubjectAreas.prompt`
> - Tool: `server/src/tools/retrieval/getSubjectArea.ts`
> - Node: `server/src/agents/chatAgent/nodes/subjectAreas.ts`

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
                      ├── 有 contextType（且在已处理类型中）→ 按 context 过滤 SubModule
                      └── 无匹配 → 按 Module/SubModule 优先级排序，取 Top 1
```

**ContextType 完整映射表**（来自 `shared/types/contextMap.ts`）：

| UI contextType | 内部字符串 | 代码层过滤逻辑 | 备注 |
|---------------|-----------|--------------|------|
| chart | "visualization dashboard chart" | submodule 含 "chart" | 支持 others 回退 |
| crosstab | "visualization dashboard crosstab" | submodule 含 "crosstab" | 支持 others 回退 |
| table | "visualization dashboard table" | submodule 含 "table" | ⚠️ 代码层未排除 freehand table（见风险说明）；支持 others 回退 |
| freehand | "visualization dashboard freehand table" | submodule 含 "freehand" | 支持 others 回退 |
| worksheet | "data worksheet" | module 含 "worksheet" | 无 others 回退，不命中则透传 |
| dashboard | "visualization dashboard" | 无代码层过滤 | 直接走优先级排序 |
| portal | "portal data" | 无代码层过滤 | 直接走优先级排序；LLM 会感知并返回 Portal 相关模块 |
| em | "enterprise manager" | 无代码层过滤 | 直接走优先级排序；EM 优先级最低（score=2） |
| scheduleTask | "schedule task" | 无代码层过滤 | 影响 LLM 返回 Portal/EM > scheduled task；代码层无对应分支，走优先级排序（见风险说明） |
| dashboardPortal | "pinned dashboard" | 无代码层过滤 | 影响 LLM 返回 Dashboard 相关；代码层无对应分支，走优先级排序 |
| (空/undefined) | — | 跳过整个 context 过滤块 | 直接走优先级排序；兜底模块为 "Dashboard" |

> **⚠️ 代码层 table 过滤 Bug**：`getEnhancedSubjectAreas` 中 table 分支使用 `includes("table")` 进行匹配，
> 会命中 "freehand table"。而 `isModuleMatchingContext` 函数则正确加了 `&& !includes("freehand")` 排除。
> 两处逻辑不一致，实际执行 context 过滤时 freehand table 可能被误纳入 table 结果。

---

## 能力一：Module 识别正确

### 规则梳理

| Module | 关键触发词/场景 | 强制性 |
|--------|--------------|--------|
| Dashboard | 可视化、展示、排序、聚合、格式化 | 默认优先 |
| Data Worksheet | 数据建模、关系、预处理、变量、命名分组（Named Grouping） | 中等 |
| Portal | Join/Link、数据类型变更（双路径触发）、数据源/数据模型/VPM | 强制（双路径）|
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

- 有 contextType（且在已处理类型 chart/crosstab/table/freehand/worksheet 中）→ 返回对应 contextType 的 subjectArea，explicit=false
- 有 contextType 但不在已处理类型中（如 portal/em/scheduleTask/dashboardPortal/dashboard）→ 走优先级排序兜底
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

**有代码层过滤分支的 contextType**：

| contextType | 过滤条件 | 无匹配时的 others 回退 |
|-------------|----------|----------------------|
| chart | submodule 含 "chart" | 推断为 `Dashboard > chart` |
| crosstab | submodule 含 "crosstab" | 推断为 `Dashboard > crosstab` |
| freehand | submodule 含 "freehand" | 推断为 `Dashboard > freehand` |
| table | submodule 含 "table"（⚠️ 实际会命中 freehand table，见 Bug 说明）| 推断为 `Dashboard > table` |
| worksheet | module 含 "data worksheet" 或 "worksheet" | 无回退，直接透传原结果按优先级排序 |

**无代码层过滤分支（透传到优先级排序）**：

| contextType | 内部字符串 | 实际行为 |
|-------------|-----------|---------|
| dashboard | "visualization dashboard" | 无 if-else 分支命中 → 走优先级排序 |
| portal | "portal data" | 无 if-else 分支命中 → 走优先级排序 |
| em | "enterprise manager" | 无 if-else 分支命中 → 走优先级排序 |
| scheduleTask | "schedule task" | 无 if-else 分支命中 → 走优先级排序（Portal/EM 优先级最低，可能被 Dashboard 压过）|
| dashboardPortal | "pinned dashboard" | 无 if-else 分支命中 → 走优先级排序 |
| (空) | — | `parsedContext?.contextType` 为 false → 跳过整个过滤块 |

> **scheduleTask 关键风险**：scheduleTask 上下文会让 LLM 倾向返回 Portal > scheduled task 或
> EM > scheduled task，但代码层没有对应过滤分支，且 Portal/EM 在优先级排序中优先级最低（score=2），
> 若 LLM 同时返回 Dashboard 相关模块，Portal/EM scheduled task 可能被排在后面被过滤掉。

### 5.3 Enhanced Path：优先级排序（无 context 匹配时）

**Module 优先级**：Dashboard(0) > Data Worksheet(1) > Others(2)

**SubModule 优先级**（Dashboard 内）：chart(0) > crosstab(1) > freehand(2) > table(3) > others(4)

### 5.4 preferRewriteWithContext 标记

**逻辑**：context 过滤命中时设为 `true`，影响下游 retrieval 策略

| 场景 | preferRewriteWithContext |
|------|--------------------------|
| context 过滤命中（chart/crosstab/table/freehand/worksheet）| `true` |
| explicit=true（Fast Path）| `false`（Fast Path 不设置）|
| 无 context，优先级排序路径 | `false` |
| context=portal/em/scheduleTask/dashboardPortal/dashboard（无过滤分支）| `false` |

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

> **⚠️ 非标准 contextType 的兜底风险**：
> 代码为 `module: parsedContext?.contextType || vsModuleName`，当 LLM 返回空且 contextType 为
> `"schedule task"` 或 `"pinned dashboard"` 时，兜底 module 会被赋值为这些字符串（非标准模块名），
> 不匹配任何已知 Module（Dashboard/Data Worksheet/Portal/Enterprise Manager），可能导致下游路由异常。

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

### 场景五：scheduleTask contextType

```
当前问题："How to configure an email notification for a task?"
contextType: scheduleTask（"schedule task"）
```

| 验证点 | 期望值 |
|-------|-------|
| LLM 识别 | Portal > scheduled task 或 Enterprise Manager > scheduled task |
| 代码层过滤 | scheduleTask 无对应分支 → filteredAreas 为空 → 走优先级排序 |
| 优先级排序 | Portal/EM score=2（最低）→ 若只有 Portal/EM，仍会返回 |
| 最终 subjectAreas | [Portal] 或 [Enterprise Manager]（取决于 LLM 输出和优先级） |
| preferRewriteWithContext | false（无过滤命中）|
| 潜在风险 | LLM 若同时返回 Dashboard 相关，Dashboard 优先级更高会压过 Portal/EM |

---

