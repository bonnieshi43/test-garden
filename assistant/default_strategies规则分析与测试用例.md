# 检索策略 Prompt 规则分析与测试维度（含测试用例集）

---

## Part A：检索策略 Prompt 规则分析与测试维度

# 检索策略 Prompt 规则分析与测试维度

> 基于 `default_strategies.prompt` 及其引用的 `rewrite_rule.prompt`、`decomposition_rule.prompt`、`minor_expansion.prompt` 分析。

---

## 一、Rewrite 阶段主要规则总结

### 1. 上下文注入开关（allowContextInjection）

默认为 `false`，满足以下任一条件时置为 `true`：

- `rewriteWithContext` 参数为 `true`
- 问题是仪表板模糊操作 + 当前模块含 chart/crosstab/freehand table + 问题动作与模块类型匹配
- 问题是步骤追问 + 历史有清晰流程 或 `allowContextInjection = true`

### 2. Step 1：判断是否需要改写

| 条件 | 处理方式 |
|------|----------|
| 问题清晰、术语正确（如"how to create a bar chart"） | 仅去除疑问词，跳过 Step 2，直接进入 Step 3 |
| 问题模糊、缺乏上下文、询问具体步骤（如"下一步是什么"） | 进入 Step 2 改写 |

### 3. Step 2：改写规则

#### 规则一：是否注入上下文
- `allowContextInjection = false` → 严禁添加任何上下文，只用原始输入
- `allowContextInjection = true` → 仅授权，实际注入由后续规则（Step 2.2、Step 3）决定

#### 规则二：步骤追问处理
- 识别关键词：first step / second step / next step / then / continue 等
- 有历史流程上下文 → 改写为询问后续步骤
- 无历史但 `allowContextInjection = true` → 使用模块上下文改写
- **禁止**：直接回答步骤内容；禁止对其他类型问题拼接上下文

#### 规则三：聚焦功能操作（核心规则）

**必须忽略（业务内容）：**
- 具体字段名（如"销售额"、"客户姓名"）
- 业务实体名（如"A渠道"、"华东区"）
- 业务指标名（如"ROI"、"转化率"）
- 业务场景描述（如"销售分析"、"用户群体"）

**必须保留/转换（操作内容）：**

| 原始表达 | 转换结果 |
|----------|----------|
| 排名、Top N、最高/最低 | view data ranking / sort data |
| 筛选、过滤、排除、只显示 | filter data |
| 对比、比较 | data comparison |
| 目标线、基准线、均值线 | target line |
| 时间序列展示 | display time series |
| 同比、环比、趋势分析 | date comparison / trend analysis |
| 分组操作 | group data（数据字段）/ group components（UI组件） |
| 汇总、求和、平均、合并列属性 | aggregate data |
| 自定义布局表格 | freehand table |
| 关联表、查看相关实体 | join tables |
| 合并表 | union |
| 笛卡尔积 | Crossjoin |
| Excel数据 | Excel data source |

**优先级规则（关键）：**
- 排名检测优先于过滤（当子集选择依赖排序位置时）
- target line ≠ 过滤，target line ≠ 排名
- 时间序列展示 ≠ 趋势分析（无明确对比意图时不转换为 date comparison）

#### 规则四：禁止主动扩展
- 只做被动转换（已有内容 → 标准术语）
- 禁止添加用户未提及的操作或功能
- 保持查询单一性

### 4. Step 3：Dashboard 组件上下文注入

同时满足以下**全部条件**才注入：
1. `allowContextInjection = true`
2. 当前模块包含 chart / crosstab / freehand table
3. 用户问题对组件类型模糊（功能可适用于多种组件）
4. 问题中未已明确提及具体组件类型

操作：从上下文提取组件关键词追加到改写结果末尾。

**反例（不注入）：**
- "how to create a bar chart" + 上下文包含 freehand table → 不注入（问题已明确 bar chart）

### 5. Stage Two：改写自检（Self-Check）

7 项检查：
1. 是否避免了业务数据
2. 步骤追问是否正确处理
3. 是否聚焦功能操作
4. 是否使用标准术语
5. 是否有不当上下文拼接
6. 是否仅改写未扩展
7. Enterprise Manager 上下文处理（若属于 EM 操作，改写结果中不得出现 dashboard/chart 等可视化词汇）

---

## 二、Decomposition 阶段主要规则总结

### 1. 完全隔离原则（Critical）

分解阶段**唯一输入**是 `rewritten_query`，完全忽略：
- `contextType`（当前模块）
- `history`（历史对话）
- `question`（原始问题）

### 2. 不需要分解的情况（优先级从高到低）

| 类型 | 示例 | 处理 |
|------|------|------|
| 单概念查询 | "improve dashboard performance" | 不分解 |
| 单操作查询 | "create a bar chart" | 不分解 |
| 优化/性能目标查询 | "improve dashboard loading speed" | 不分解 |
| 多参数单操作 | "group sales by year and quarter" | 不分解（共享同一动词） |

### 3. 需要分解的情况

| 类型 | 示例 |
|------|------|
| 显式多功能组合（and/also/simultaneously） | "create a bar chart and add data labels" |
| 复合步骤（first...then...） | "first filter data then create a chart" |

### 4. 分解判断流程（顺序执行）

1. 仅分析 `rewritten_query` 的语言结构
2. 判断是否是单概念/单目标 → 是则不分解
3. 判断是否显式包含多个独立功能（靠连接词识别） → 否则不分解
4. 仍不确定 → **保守原则：倾向不分解**

### 5. 分解原则

- **上下文保留**：分解后每个子查询须保留必要的关键对象（如含 chart 则子查询也须含 chart）
- **严禁扩展**：只分解改写结果中明确存在的内容
- **原子性**：每个子查询对应单一可独立配置的功能
- **合理数量**：通常 1-3 个

### 6. 分解自检（Phase 4）

1. 分解是否真的必要
2. 是否引入了改写结果中未有的内容
3. 上下文是否在子查询中保留
4. 子查询数量是否合理（1-3个）
5. 子查询是否真正原子化

---

## 三、rewriteWithContext 的判断逻辑与应用场景

### 1. 参数的计算位置

`rewriteWithContext` 由 TypeScript 代码计算后作为参数传入 prompt，**不由 prompt 内部决定**。
最终传入 prompt 的字符串为 `"true"` 或 `"false"`（`promptRetriever.ts:23`）。

---

### 2. TypeScript 侧：`preferRewriteWithContext` 的计算（两个来源取 OR）

#### 来源 A：`getSubjectArea.ts` 内部 context 过滤触发

位置：`getSubjectArea.ts:251~263`，返回时直接设 `preferRewriteWithContext: true`。

**同时满足以下全部条件：**

1. LLM 返回的 subjectAreas 不为空
2. 不存在 `explicitly_mentioned=true` 的 area（否则直接走显式结果，不进过滤分支）
3. 存在 `parsedContext.contextType`（用户当前打开了具体页面）
4. 按 contextType 过滤后 `filteredAreas.length > 0`（过滤成功收窄了结果）

各 contextType 的过滤规则：

| contextType | 过滤条件 |
|---|---|
| `worksheet` | module 包含 "data worksheet" 或 "worksheet" |
| `freehand` | submodule 包含 "freehand" 或 "freehand table" |
| `chart` | submodule 包含 "chart" |
| `crosstab` | submodule 包含 "crosstab" |
| `table` | submodule 包含 "table" 且不含 "freehand" |

**含义**：LLM 返回了多个候选模块，系统根据用户当前页面把范围收窄了，query 应结合上下文重写。

#### 来源 B：`subjectAreas.ts` 中的补充判断

位置：`subjectAreas.ts:40~41`

```typescript
const finalPreferRewriteWithContext = preferRewriteWithContext ||
   (originalSubjectObj.length === 1 && isModuleMatchingContext(originalSubjectObj[0], internalContext));
```

**条件**：`getSubjectArea` 返回的**恰好只有 1 个** subjectArea，且该 area 与 `internalContext` 匹配。

`isModuleMatchingContext` 的匹配规则（`getSubjectArea.ts:381~410`）：

| contextType | 匹配条件 |
|---|---|
| `worksheet` | module 包含 "data worksheet" 或 "worksheet" |
| `freehand` | submodule 包含 "freehand" 或 "freehand table" |
| `chart` | submodule 包含 "chart" |
| `crosstab` | submodule 包含 "crosstab" |
| `table` | submodule 包含 "table" 且不含 "freehand" |

**含义**：LLM 只返回了一个模块，且刚好就是用户当前所在页面，问题是强上下文相关的。

---

### 3. Prompt 侧：`allowContextInjection` 的计算

默认 `allowContextInjection = false`，满足以下**任一**条件置为 `true`：

| 条件 | 说明 |
|---|---|
| `rewriteWithContext = true` | TypeScript 侧已判定需要上下文（直接透传） |
| query 是 **Dashboard 模糊操作** AND module 含 chart/crosstab/freehand table AND 操作动作与模块类型匹配 | 用户在 Dashboard 某组件页面提出模糊操作 |
| query 是**步骤询问**（含"下一步"/"第几步"/"then"/"continue"等关键词）AND（历史有明确流程 OR `allowContextInjection = true`） | 追问步骤场景 |

---

### 4. 实际注入的两个时机（allowContextInjection=true 后仍受限）

#### Step 2（query rewrite 阶段）—— 仅限步骤询问

- 必须含有步骤关键词（first/next/then/continue 等）
- 有历史流程 → 用历史流程改写为续步骤查询
- 无历史且 `allowContextInjection = true` → 用 module context 改写
- **严禁**对其他类型 query 直接拼接上下文

#### Step 3（Dashboard 组件注入）—— 同时满足以下全部

1. `allowContextInjection = true`
2. 当前 module context 包含 chart / crosstab / freehand table 之一
3. 用户 query 对组件类型**有歧义**（功能可适用于多个 Dashboard 组件）
4. query 中**没有**已经提到具体组件名

满足时：从 context 提取组件关键词（chart/crosstab/freehand table）追加到 query 末尾。

---

### 5. 完整决策树

```
preferRewriteWithContext (TS计算)
  = (来源A：LLM返回多area → contextType过滤成功收窄)
  || (来源B：LLM返回单area && 该area与internalContext匹配)
          ↓ 作为字符串参数 rewriteWithContext 传入 prompt
          ↓
allowContextInjection (Prompt计算，默认 false)
  = rewriteWithContext == "true"
  || (Dashboard模糊操作 && module匹配 && 动作与模块匹配)
  || (步骤询问 && (历史有流程 || allowContextInjection == true))
          ↓
实际注入（仍受场景限制）
  Step 2：仅步骤询问 → 拼接历史流程或module context
  Step 3：Dashboard组件歧义 && 未提及具体组件 → 追加组件名
```

---

### 6. 关键区分

- `rewriteWithContext = true` 只是"授权允许注入"，不代表每次都一定会注入
- `allowContextInjection = true` 之后仍受步骤询问 / Dashboard 组件歧义两个具体时机约束
- 非步骤询问的问题即使 `allowContextInjection = true` 也严禁拼接上下文
- Step 3 问题已明确组件类型时不注入（即使 `allowContextInjection = true`）
- 模块非 chart/crosstab/freehand table 时 Step 3 不注入

---

## 四、可转化的测试维度

### 维度 1：Rewrite - 业务内容剥离

| 测试点 | 描述 |
|--------|------|
| T1-1 | 含具体字段名的问题 → 改写结果不含字段名 |
| T1-2 | 含业务实体名的问题 → 改写结果不含实体名 |
| T1-3 | 含业务指标（ROI/转化率）的问题 → 改写结果转为通用操作词 |
| T1-4 | 含业务场景描述的问题 → 改写结果不含场景词 |

### 维度 2：Rewrite - 操作类型转换准确性

| 测试点 | 描述 |
|--------|------|
| T2-1 | "Top 10 产品" → "view data ranking"（不转为 filter） |
| T2-2 | "过滤掉某类数据" → "filter data"（不转为 ranking） |
| T2-3 | 排名与过滤共存时，排名优先（dashboard 模块） |
| T2-4 | "均值线/目标线" → "target line"（不转为 filter 或 ranking） |
| T2-5 | "按时间展示" → "display time series"（不转为 date comparison） |
| T2-6 | "同比/环比" → "date comparison"（明确对比意图才转换） |
| T2-7 | "group by year and quarter" → 单个 group 查询（不拆分维度） |
| T2-8 | "join 两张表" → "join tables" |
| T2-9 | 自定义布局表格 → "freehand table"（普通表格样式不触发） |

### 维度 3：Rewrite - 步骤追问处理

| 测试点 | 描述 |
|--------|------|
| T3-1 | 含"下一步"关键词 + 历史有流程 → 改写为流程续问，不直接回答 |
| T3-2 | 含"下一步"关键词 + 无历史 + `allowContextInjection=true` → 用模块上下文改写 |
| T3-3 | 含"下一步"关键词 + `allowContextInjection=false` → 只基于原始输入，不拼接上下文 |
| T3-4 | 非步骤追问 → 不拼接历史上下文 |

### 维度 4：Rewrite - 上下文注入（Step 3）

| 测试点 | 描述 |
|--------|------|
| T4-1 | `allowContextInjection=true` + 模块=chart + 问题模糊 → 注入 "in chart" |
| T4-2 | `allowContextInjection=true` + 模块=chart + 问题已明确 chart → 不注入 |
| T4-3 | `allowContextInjection=false` + 模块=chart + 问题模糊 → 不注入 |
| T4-4 | `allowContextInjection=true` + 模块非chart/crosstab/freehand table → 不注入 |

### 维度 5：Rewrite - rewriteWithContext 参数

| 测试点 | 描述 |
|--------|------|
| T5-1 | `rewriteWithContext=true` → `allowContextInjection=true` 被激活 |
| T5-2 | `rewriteWithContext=false` + 其他条件不满足 → `allowContextInjection=false` |
| T5-3 | `rewriteWithContext=false` + 仪表板模糊操作 + 匹配模块 → `allowContextInjection=true` |
| T5-4 | `rewriteWithContext=true` + 步骤追问 + 有历史流程 → 优先使用历史流程上下文 |
| T5-5 | `rewriteWithContext=true` + 问题已明确组件类型 → Step 3 不注入 |
| T5-6 | `rewriteWithContext=true` + 非步骤追问问题 → 不拼接任何上下文（仅授权，不强制注入） |

### 维度 6：Rewrite - 禁止主动扩展

| 测试点 | 描述 |
|--------|------|
| T6-1 | 问题只提一个操作 → 改写结果不引入额外功能 |
| T6-2 | 问题提及优化目标 → 不展开为具体功能列表 |

### 维度 7：Rewrite - Enterprise Manager 场景

| 测试点 | 描述 |
|--------|------|
| T7-1 | EM 用户管理操作 → 改写结果不含 dashboard/chart/table 等词 |

### 维度 8：Decomposition - 是否分解判断

| 测试点 | 描述 |
|--------|------|
| T8-1 | 单操作改写结果 → `final_queries` 只有1条，与 `rewritten_query` 一致 |
| T8-2 | 含 "and" 连接两个独立功能 → 拆为两条子查询 |
| T8-3 | "group by year and quarter" → 不拆（多参数同动词） |
| T8-4 | 优化目标类查询 → 不拆，不扩展为功能列表 |
| T8-5 | 含 "first...then..." → 拆为两步骤查询 |

### 维度 9：Decomposition - 上下文保留

| 测试点 | 描述 |
|--------|------|
| T9-1 | "create a bar chart and add data labels" → 第二条子查询含 "bar chart" |
| T9-2 | "add charts and filters to a dashboard" → 两条子查询均含 "dashboard" |
| T9-3 | 分解后每条子查询独立可理解 |

### 维度 10：Decomposition - 隔离性验证

| 测试点 | 描述 |
|--------|------|
| T10-1 | 历史含额外信息 → 分解结果不受历史影响 |
| T10-2 | 原始问题含业务词 → 分解只基于 rewritten_query |
| T10-3 | 模块上下文不影响分解结果 |

### 维度 11：输出格式

| 测试点 | 描述 |
|--------|------|
| T11-1 | 输出为合法 JSON，含 `rewritten_query`（string）和 `final_queries`（array） |
| T11-2 | 无多余文字、无 markdown 包裹 |
| T11-3 | `final_queries` 数组不为空 |

---

## 五、最容易出错的地方

### 1. 排名 vs 过滤 的判断边界（高风险）

> "显示销售额最高的10个产品" → 应为 **ranking**，不是 filter
> "只显示销售额大于10万的产品" → 应为 **filter**，不是 ranking

当两者同时出现时，dashboard 模块下优先识别 ranking，但规则表述略复杂，模型容易混淆。

### 2. 时间序列 vs 趋势分析 的误判（高风险）

> "按月展示销售数据" → display time series（不含对比意图）
> "查看今年和去年的对比" → date comparison（明确对比）

模型易将所有时间相关表达都转为 date comparison，需要严格检查是否有明确对比/趋势意图。

### 3. Step 3 的注入条件漏判

四个条件必须**同时满足**，缺一不注入。尤其容易遗漏：
- 问题已明确组件类型 → 不注入（但易忘记检查）
- 模块不含 chart/crosstab/freehand table → 不注入

### 4. 步骤追问的上下文拼接滥用

`allowContextInjection = true` 只授权步骤追问和 Step 3 使用上下文，不代表所有问题都可以拼接历史。非步骤追问的问题如果触发了上下文拼接，属于严重违规。

### 5. 分解时的过度拆分

模型易将以下情况错误拆分：
- 多参数同动词（"group by year and quarter"）→ 错拆为两条
- 优化目标查询 → 错拆为具体功能列表

保守原则是核对时的底线：**不确定就不拆**。

### 6. 分解时上下文丢失

拆分后第二条、第三条子查询丢失关键对象词（如 chart、dashboard），导致检索时语义不完整。这是最常见的分解错误。

### 7. Enterprise Manager 与 Dashboard 上下文污染

当用户在 EM 模块操作时（管理用户/组/角色），若改写结果含 dashboard/chart 等词，会导致检索结果偏向可视化文档，完全偏离用户意图。

### 8. rewriteWithContext 参数理解歧义（高风险）

**常见误解：**
- `rewriteWithContext = true` ≠ 一定会注入上下文，仅代表"开关打开"
- `rewriteWithContext = true` ≠ 所有问题都可以拼接上下文，只有步骤追问和 Step 3 可以
- `rewriteWithContext = true` 不会覆盖"问题已明确组件类型"的判断（Step 3 仍不注入）

**正确理解：**
- `rewriteWithContext = true` 激活 `allowContextInjection = true`
- `allowContextInjection = true` 仅授权，实际注入由具体场景规则决定
- 即使授权，也要满足场景条件才能注入

---

*文件生成时间：2026-03-12*
*基于 prompts-v2/retrievers/ 目录下的 prompt 文件分析*

## Part B：检索策略测试用例集

# 检索策略测试用例集（第四版）

> 基于 `检索策略Prompt规则分析与测试维度.md` 生成，覆盖全部 contextType 与主要规则维度。
> 生成时间：2026-03-12

---

## 说明

- **总计 38 个 case**：34 个复杂问题（需要关注 rewrite/decompose 的 case）+ 4 个简单问题（≤ 1/6）
- **语言分布**：英文 30 个（79%）、中文 8 个（21%）
- **多轮对话**：C06、C07、C18、C24、C30、C38（以 `[History]` 标注上轮内容）
- **rewriteWithContext 列**：该 case 的入参值（`true` / `false`）
- **预期 rewritten_query**：仅填写改写后的查询字符串，无注释
- **预期 final_queries**：JSON 数组，仅包含查询字符串
- **C31–C38**：补充覆盖的遗漏测试点（T5-3、T3-3、T4-4、T10-2/T10-3、Excel转换、Crossjoin转换、data comparison、T3-4）

---

## 测试用例总表

| Case ID | 用户问题 | contextType | rewriteWithContext | 预期 rewritten_query | 预期 final_queries | 验证的规则 |
|---------|---------|-------------|-------------------|---------------------|-------------------|-----------|
| C01 | How do I show the top 10 products by sales amount and also add an average target line to the chart? | dashboard | false | `view data ranking in chart and add target line in chart` | `["view data ranking in chart", "add target line in chart"]` | 字段名（sales amount）不进改写; Top N → view data ranking（非filter）; 均值线/目标线 → target line; and连接独立功能 → 分解2条; 分解子查询保留chart |
| C02 | I want to create a bar chart and then add data labels to display the exact values on each bar. | chart | false | `create bar chart and add data labels to bar chart` | `["create bar chart", "add data labels to bar chart"]` | first...then结构 → 按步骤分解; 分解后子查询保留bar chart对象词 |
| C03 | How can I join the orders table with the customers table and then group the result by region? | worksheet | false | `join tables and group data` | `["join tables", "group data"]` | join tables术语转换; 业务实体名（orders/customers/region）不进改写; first-then结构 → 分解; and连接独立功能 → 分解2条 |
| C04 | How do I show year-over-year comparison by quarter and also apply conditional formatting to highlight values below the benchmark? | crosstab | false | `date comparison in crosstab and apply conditional formatting in crosstab` | `["date comparison in crosstab", "apply conditional formatting in crosstab"]` | year-over-year明确对比意图 → date comparison; 均值基准不转target line而是作为对比条件被剥离; and连接 → 分解2条; 子查询保留crosstab |
| C05 | I need to create a custom layout table showing department performance metrics and group the components by business unit. | freehand | false | `create freehand table and group components` | `["create freehand table", "group components in freehand table"]` | 自定义布局表格 → freehand table; 业务实体名/业务场景词不进改写; group components（UI组件）vs group data（数据字段）区分; and连接 → 分解2条; 子查询保留freehand table |
| C06 | **[History]** "How do I create a line chart?" → answered. **[Current]** What should I do next to configure it? | chart | true | `configure line chart` | `["configure line chart"]` | 步骤追问关键词(next) + 历史有流程 → 改写为流程续步骤; rewriteWithContext=true → allowContextInjection激活; 历史上下文优先（不直接回答步骤内容）; 单操作→不分解 |
| C07 | **[History]** "How do I create a bar chart in the dashboard?" → answered. **[Current]** Then how do I add filters to control the data displayed? | dashboard | true | `add filters to dashboard` | `["add filters to dashboard"]` | 步骤追问关键词(then) + 历史有流程 → 续步骤改写; rewriteWithContext=true + 步骤追问 + 有历史流程 → 优先使用历史流程上下文; 单操作→不分解 |
| C08 | How do I display monthly sales data over time and filter out records where the conversion rate is below 5%? | table | false | `display time series in table and filter data in table` | `["display time series in table", "filter data in table"]` | 按月展示+无对比意图 → display time series（非date comparison）; 阈值过滤 → filter data（非ranking）; 指标名（conversion rate）不进改写; 字段名（monthly sales）不进改写; and连接 → 分解2条 |
| C09 | Why can't I view certain reports in the portal, and how do I configure the access permissions for different user groups? | portal | false | `view reports in portal and configure permissions in portal` | `["view reports in portal", "configure permissions in portal"]` | 业务实体名（user groups）不进改写; and连接不同操作 → 分解2条; 分解后两条子查询均保留portal |
| C10 | 如何在 Enterprise Manager 中给用户分配角色权限，并且同时管理用户组的成员？ | em | false | `assign role to user and manage user groups` | `["assign role to user", "manage user groups"]` | EM操作改写结果不含dashboard/chart/table等可视化词; 业务实体名不进改写; and连接 → 分解2条 |
| C11 | How do I set up a schedule task to export a dashboard report as PDF and automatically email it to the sales team every Monday? | scheduleTask | false | `configure schedule task to export dashboard as PDF and configure email notification for schedule task` | `["configure schedule task to export dashboard as PDF", "configure email notification for schedule task"]` | 业务实体名（sales team）不进改写; and连接独立功能 → 分解2条; 分解后子查询保留schedule task |
| C12 | How do I embed a dashboard in the portal and configure interactive filter settings for the embedded view? | dashboardPortal | false | `embed dashboard in portal and configure filter settings in portal` | `["embed dashboard in portal", "configure filter settings in portal"]` | and连接独立功能 → 分解2条; 分解后两条子查询均保留portal |
| C13 | How do I display only the top 5 highest-grossing customers who exceed the annual revenue threshold? | dashboard | false | `view data ranking in dashboard` | `["view data ranking in dashboard"]` | ranking与filter共存时dashboard模块ranking优先; Top N → view data ranking（非filter）; 业务实体名（customers）不进改写; 业务指标名（annual revenue）不进改写; 单输出→不分解 |
| C14 | How do I group the transaction data by year and quarter to analyze seasonal business patterns? | worksheet | false | `group data by year and quarter` | `["group data by year and quarter"]` | group by year and quarter → 单条group查询（多参数共享同一动词，不拆分）; 业务场景词（seasonal patterns）不进改写; 字段名（transaction data）不进改写 |
| C15 | How do I add labels? *(当前 chart 模块)* | chart | true | `add data labels in chart` | `["add data labels in chart"]` | rewriteWithContext=true → allowContextInjection激活; 问题模糊+模块含chart → Step3注入in chart; 单操作→不分解 |
| C16 | How do I create a bar chart? *(上下文同时含 freehand table 组件)* | chart | true | `create bar chart` | `["create bar chart"]` | rewriteWithContext=true但问题已明确组件类型(bar chart) → Step3不注入; allowContextInjection激活但注入条件不满足（问题已明确）|
| C17 | How do I merge the current year sales data table with the previous year sales data table using union? | worksheet | false | `union tables` | `["union tables"]` | union合并表 → union tables术语转换; 业务实体名（sales data table）不进改写; 单操作→不分解 |
| C18 | **[History]** "如何在仪表板中添加折线图？" → answered. **[Current]** 然后如何给折线图添加数据标签？ | dashboard | true | `add data labels to line chart` | `["add data labels to line chart"]` | 步骤追问(然后) + 历史有流程 → 续步骤改写; rewriteWithContext=true + 历史优先 → 使用历史流程上下文; 单操作→不分解 |
| C19 | I want to show total revenue and average order count aggregated by product category in a freehand table, with subtotals for each group. | freehand | false | `aggregate data in freehand table` | `["aggregate data in freehand table"]` | total/average/subtotal同属aggregate语义 → 共享同一操作不拆分; 业务实体名（product category）不进改写; 指标名（revenue/order count）不进改写 |
| C20 | 如何在数据表中对华东区和华北区的销售额进行同比分析，并筛选出 ROI 大于 200% 的记录？ | table | false | `date comparison in table and filter data in table` | `["date comparison in table", "filter data in table"]` | 同比 → date comparison（明确对比意图）; 筛选+阈值 → filter data; 业务实体名（华东/华北）不进改写; 业务指标（ROI）不进改写; and连接 → 分解2条 |
| C21 | 在 Enterprise Manager 中，为什么无法访问某些报表？如何重置用户密码并重新分配访问权限？ | em | false | `reset user password and assign user permissions` | `["reset user password", "assign user permissions"]` | EM操作改写不含可视化词（dashboard/chart/table等）; 业务实体名不进改写; and连接 → 分解2条 |
| C22 | 如何先设置交叉表的行列表头，然后应用百分比计算，最后将结果导出？ | crosstab | false | `configure crosstab headers and apply percentage calculation in crosstab and export crosstab` | `["configure crosstab headers", "apply percentage calculation in crosstab", "export crosstab"]` | 先...然后...最后 → 按步骤分解3条; 每条子查询保留crosstab对象词; 子查询数量合理（≤3条）|
| C23 | How do I configure a schedule task to first generate a worksheet report and then automatically archive it to a network storage folder? | scheduleTask | false | `configure schedule task to generate report and configure archive destination for schedule task` | `["configure schedule task to generate report", "configure archive destination for schedule task"]` | first...then → 按步骤分解; 分解后子查询保留schedule task对象词; 业务实体名（network folder）不进改写 |
| C24 | **[History]** "How do I create a sales analysis dashboard?" → discussed chart and filter features. **[Current]** How do I configure the portal layout and set up the navigation menu? | dashboardPortal | false | `configure portal layout and configure navigation menu in portal` | `["configure portal layout", "configure navigation menu in portal"]` | 历史中的dashboard/chart内容不影响当前portal问题的分解（分解隔离性）; and连接 → 分解2条; 两条子查询保留portal |
| C25 | Where can I find the report subscription settings and how do I configure email notification preferences in the portal? | portal | false | `configure report subscription in portal and configure email notification preferences in portal` | `["configure report subscription in portal", "configure email notification preferences in portal"]` | and连接不同操作 → 分解2条; 分解后两条子查询保留portal; 业务实体名不进改写 |
| C26 | How do I improve dashboard loading speed? | dashboard | false | `improve dashboard loading speed` | `["improve dashboard loading speed"]` | 优化目标类查询 → 不展开为具体功能列表; 单目标→不分解 |
| C27 | What is a freehand table in StyleBI? | freehand | false | `freehand table` | `["freehand table"]` | 单概念查询→不分解; 改写仅保留核心功能术语 |
| C28 | How do I sort the data displayed in a chart? | chart | false | `sort data in chart` | `["sort data in chart"]` | rewriteWithContext=false → allowContextInjection=false; allowContextInjection=false + 模块含chart + 问题模糊 → Step3不注入; 单操作→不分解 |
| C29 | What are the available user role types in Enterprise Manager? | em | false | `user roles` | `["user roles"]` | EM操作改写结果不含dashboard/chart等可视化词; 单概念→不分解 |
| C30 | **[History]** 无相关历史流程。**[Current]** 下一步是什么？ | worksheet | true | `configure worksheet` | `["configure worksheet"]` | 步骤追问 + 无历史 + allowContextInjection=true → 使用模块上下文（contextType=worksheet）改写; 对比T3-3：若allowContextInjection=false则不注入 |
| C31 | How do I sort the data? *(dashboard 模块含 chart 组件，rewriteWithContext=false)* | dashboard | false | `sort data in chart` | `["sort data in chart"]` | rewriteWithContext=false时，仪表板模糊操作+模块含chart+动作与模块匹配 → allowContextInjection自动激活; 上下文注入chart对象词; 非步骤追问不拼接历史 |
| C32 | What's the next step? | crosstab | false | `next step` | `["next step"]` | 步骤追问 + allowContextInjection=false → 仅基于原始输入，禁止拼接模块或历史上下文; 改写结果不引入任何上下文词 |
| C33 | How do I configure the settings? *(rewriteWithContext=true，模块为 scheduleTask)* | scheduleTask | true | `configure schedule task settings` | `["configure schedule task settings"]` | allowContextInjection=true但模块非chart/crosstab/freehand table → Step3四条件不满足，不注入; 单操作→不分解 |
| C34 | How do I filter the Q1 revenue data by product line and add a reference line showing the annual target on the chart? | chart | false | `filter data in chart and add target line in chart` | `["filter data in chart", "add target line in chart"]` | 分解阶段唯一输入是rewritten_query（Q1/revenue/product line等原始业务词不影响分解）; chart模块上下文不影响分解逻辑; 子查询保留chart对象词 |
| C35 | 我想把 Excel 文件中的数据导入到工作表中进行分析，应该怎么操作？ | worksheet | false | `Excel data source` | `["Excel data source"]` | Excel数据/文件 → Excel data source术语转换; 单操作→不分解 |
| C36 | 如何对商品目录和促销活动表做笛卡尔积关联？ | worksheet | false | `Crossjoin tables` | `["Crossjoin tables"]` | 笛卡尔积 → Crossjoin术语转换; 业务实体名（商品目录/促销活动表）不进改写; 单操作→不分解 |
| C37 | How can I compare the sales performance between the East and West regions for the same quarter? | chart | false | `data comparison in chart` | `["data comparison in chart"]` | 对比/比较（非时间维度对比）→ data comparison（非date comparison）; 业务实体名（East/West regions）不进改写; 业务场景词（sales performance/quarter）不进改写; 单操作→不分解 |
| C38 | **[History]** "How do I add color themes to a dashboard?" → answered. **[Current]** How do I export this dashboard as a PDF file? | dashboard | true | `export dashboard as PDF` | `["export dashboard as PDF"]` | 非步骤追问（无next/then/continue等关键词）+ allowContextInjection=true → 不拼接历史上下文; rewriteWithContext=true仅授权Step2步骤追问和Step3组件注入，不强制注入历史; 单操作→不分解 |
| C39 | How do I show the top 10 products by sales volume but only include those with profit margin above 20%? | chart | false | `view data ranking in chart` | `["view data ranking in chart"]` | ranking与filter共存时ranking优先（chart模块，非dashboard）; Top N优先级高于阈值过滤; 业务字段名（sales volume/profit margin）不进改写; 单逻辑输出→不分解 |
| C40 | How do I display monthly sales trends for the last 12 months? | dashboard | false | `display time series in dashboard` | `["display time series in dashboard"]` | 按月展示+趋势词但无明确对比意图 → display time series（非date comparison）; 业务场景词（last 12 months）不进改写; "trends"词汇不转为date comparison（缺对比目标）; 单操作→不分解 |
| C41a | I want to create a bar chart and add data labels to the chart. | chart | false | `create bar chart and add data labels to bar chart` | `["create bar chart", "add data labels to bar chart"]` | 分解隔离性验证part-a：chart模块，按步骤分解，子查询保留bar chart; rewritten_query与分解结果一致 |
| C41b | I want to create a bar chart and add data labels to the chart. | dashboard | false | `create bar chart and add data labels in chart` | `["create bar chart", "add data labels in chart"]` | 分解隔离性验证part-b：dashboard模块（同rewritten_query不同contextType），分解结果应一致（仅对象词位置不同）; 证明contextType不影响分解逻辑 |
| C42 | How do I filter to only show values above the 50K target benchmark line? | chart | false | `add target line in chart and filter data in chart` | `["add target line in chart", "filter data in chart"]` | Target line ≠ 过滤（两者分开处理）; 阈值（50K）作为过滤条件被剥离，不改变target line转换; "above the target"表述中target line优先被识别; 业务指标名（50K benchmark）不进改写; and隐含 → 分解2条 |
| C43 | How do I sort the data in this chart next? | dashboard | false | `sort data in chart` | `["sort data in chart"]` | 仪表板模糊操作(sort)+步骤追问关键词(next)+模块=dashboard含chart → allowContextInjection自动激活; rewriteWithContext=false但仍注入chart（仪表板模糊操作条件优先）; 非步骤追问单独处理时不拼接历史 |
| C44 | How do I group sales by product category and also group the results by sales region? | worksheet | false | `group data by product category and group data by sales region` | `["group data by product category", "group data by sales region"]` | 多个独立group操作（不同维度）→ 分解2条（vs C14的多参数同动词不拆）; and连接 → 分解2条; 业务实体名（product category/sales region）不进改写; 两条子查询均含group data语义 |
| C45 | In Enterprise Manager, how can I manage the users who created this dashboard and audit their permissions? | em | false | `manage user permissions and audit user access` | `["manage user permissions", "audit user access"]` | EM操作改写结果不含dashboard/chart等可视化词（即使原问题提了dashboard）; 业务实体名不进改写; 关键词"created this dashboard"被完全剥离; and连接 → 分解2条 |
| C46 | **[History]** \"How do I create a dashboard?\" → answered with 5 turns of chart/filter discussion. \"How do I configure the portal layout?\" → answered. \"How do I set up notifications?\" → answered. **[Current]** How do I create a bar chart? | dashboard | false | `create bar chart` | `["create bar chart"]` | 长多轮对话后接完全新问题（非步骤追问）→ 不拼接历史（分解隔离性）; 改写结果不包含dashboard/portal/notification等前序问题词汇; rewriteWithContext=false + 非步骤追问 → 严禁上下文注入; 单操作→不分解 |
| C47 | How do I \"highlight\" the top 3 products and also apply \"special formatting\" to the chart? | chart | false | `view data ranking in chart and apply special formatting in chart` | `["view data ranking in chart", "apply special formatting in chart"]` | 特殊字符（引号）处理：转义后进改写，不影响逻辑; 输出JSON格式正确，包含转义的引号; Top N → ranking（引号不改变转换逻辑）; and连接 → 分解2条 |
| C48 | 下一步应该怎么做？ | em | false | `下一步` | `["下一步"]` | 步骤追问(下一步) + EM模块 + allowContextInjection=false → 仅基于原始输入，禁止注入任何上下文（模块词/历史词）; 改写结果不含dashboard/chart/table等可视化词; 中文问题处理一致性; 单操作→不分解 |
---

## 规则覆盖索引

| 规则 | 描述 | 覆盖的 Case |
|------|------|-----------|
| 字段名剥离 | 改写结果不含具体字段名 | C01, C08, C14, C19, C20 |
| 实体名剥离 | 改写结果不含业务实体名 | C03, C05, C09, C10, C11, C17, C20, C21, C23, C25, C36, C37 |
| 指标名剥离 | 业务指标（ROI/转化率等）→ 通用操作词 | C08, C19, C20, C37 |
| 场景词剥离 | 业务场景描述不进改写 | C05, C14, C37 |
| Top N → view data ranking（非filter） | C01, C13 |
| ranking与filter共存时ranking优先（dashboard）| C13 |
| 过滤/筛选 → filter data（非ranking）| C08, C20 |
| 均值线/目标线/基准线 → target line | C01, C04, C34 |
| 按时间展示（无对比意图）→ display time series（非date comparison）| C08 |
| 同比/环比/year-over-year → date comparison（明确对比意图）| C04, C20 |
| 对比/比较（非时间维度）→ data comparison | C37 |
| group by 多参数同动词 → 单条 group 查询（不拆分）| C14 |
| join 表 → join tables | C03 |
| union 表 → union tables | C17 |
| 笛卡尔积 → Crossjoin | C36 |
| 自定义布局表格 → freehand table | C05 |
| Excel数据/文件 → Excel data source | C35 |
| aggregate（total/average/subtotal共享语义）→ aggregate data（不拆分）| C19 |
| group components（UI组件）vs group data（数据字段）| C05 |
| 步骤追问 + 历史有流程 → 续步骤改写，不直接回答 | C06, C07, C18 |
| 步骤追问 + 无历史 + allowContextInjection=true → 模块上下文改写 | C30 |
| 步骤追问 + allowContextInjection=false → 仅原始输入，不拼接上下文 | C32 |
| 非步骤追问 + allowContextInjection=true → 不拼接历史上下文 | C38 |
| allowContextInjection=true + 模块=chart + 问题模糊 → Step3注入 in chart | C15 |
| allowContextInjection=true + 问题已明确组件类型 → Step3不注入 | C16 |
| allowContextInjection=false + 问题模糊 → Step3不注入 | C28 |
| allowContextInjection=true + 模块非chart/crosstab/freehand → Step3不注入 | C33 |
| rewriteWithContext=true → allowContextInjection 激活 | C06, C07, C15, C16, C18, C30, C33, C38 |
| rewriteWithContext=false + 其他条件不满足 → allowContextInjection=false | C28 |
| rewriteWithContext=false + 仪表板模糊操作+匹配模块 → allowContextInjection自动激活 | C31 |
| rewriteWithContext=true + 步骤追问 + 有历史流程 → 优先历史流程上下文 | C06, C18 |
| rewriteWithContext=true + 问题已明确组件类型 → Step3不注入 | C16 |
| rewriteWithContext=true + 非步骤追问 → 不拼接历史上下文（仅授权）| C07, C15, C38 |
| 优化目标类查询 → 不展开为功能列表 | C26 |
| 问题只提一个操作 → 不引入额外功能 | C27 |
| EM 操作改写不含 dashboard/chart/table 等可视化词 | C10, C21, C29 |
| 单操作/单概念 → final_queries 只有1条 | C06, C07, C13, C14, C15, C16, C17, C18, C19, C26, C27, C28, C29, C30, C31, C32, C33, C35, C36, C37, C38 |
| and连接两个独立功能 → 拆为2条子查询 | C01, C03, C04, C05, C09, C10, C11, C12, C20, C21, C23, C24, C25 |
| group by 多参数同动词 → 不拆（保守原则）| C14 |
| 优化目标类查询 → 不拆，不扩展 | C26 |
| first...then / 先...然后 → 按步骤拆分 | C02, C03, C22, C23 |
| 分解后子查询保留关键对象词（如 chart、dashboard）| C01, C02, C04, C05, C11, C22, C23, C34 |
| 分解后两条子查询均含父对象（如 portal、dashboard）| C09, C12, C24, C25 |
| 分解后每条子查询独立可理解 | C22 |
| 历史含额外信息 → 分解结果不受历史影响 | C24 |
| 原始问题含业务词 → 分解只基于 rewritten_query | C34 |
| 模块上下文不影响分解结果 | C34 |
| ranking与filter共存时ranking优先（非dashboard模块）| 在chart/table等其他模块验证ranking优先级 | C39 |
| 时间序列与趋势词的灰色地带 | "trends"词不转date comparison（缺明确对比意图） | C40 |
| 分解隔离性：contextType不影响分解 | 同一rewritten_query在不同模块的分解一致性 | C41a + C41b |
| Target line ≠ 过滤（明确示例） | 阈值条件与目标线分别处理 | C42 |
| 仪表板模糊操作 + 步骤追问 | 两个条件同时满足的处理 | C43 |
| 多group操作的拆分判断 | 多维度group vs 多参数同动词 | C44 |
| EM操作与可视化词污染防控 | EM问题中的dashboard引用被完全剥离 | C45 |
| 长多轮对话的隔离性验证 | 不相关多轮对话后的新问题不拼接历史 | C46 |
| 特殊字符处理和JSON转义 | 引号、符号等特殊字符的格式稳定性 | C47 |
| 步骤追问在非dashboard模块 | EM/scheduleTask等模块的步骤追问规则 | C48 |
---

## 附：各 contextType 的 Case 分布

| contextType | Case IDs |
|-------------|---------|
| dashboard | C01, C07, C13, C18, C24（history）, C26, C31, C38 |
| worksheet | C03, C14, C17, C30, C35, C36 |
| freehand | C05, C19, C27 |
| table | C08, C20 |
| chart | C02, C06, C15, C16, C28, C34, C37 |
| crosstab | C04, C22, C32 |
| portal | C09, C25 |
| em | C10, C21, C29 |
| scheduleTask | C11, C23, C33 |
| dashboardPortal | C12, C24 |
| dashboard | C40, C41b, C43, C46 |
| chart | C39, C41a, C42, C47 |
| em | C45, C48 |
| worksheet | C44 |

---

*文件生成时间：2026-03-12*
*规则来源：检索策略Prompt规则分析与测试维度.md*
