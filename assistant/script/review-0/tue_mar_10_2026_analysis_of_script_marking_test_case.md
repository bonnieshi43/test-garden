# Copilot Chat Conversation Export: Analysis of script marking test case

**User:** @bonnieshi43
**Thread URL:** https://github.com/copilot/c/52cc4035-9ab1-4a03-967f-e8dd5942fa2e

## @bonnieshi43

分析附件中的文件,是assistant里subjectArea识别中script的逻辑判断以及case. 分析已经生成的case, 是否有遗漏的情况.
特别是prompt没有覆盖时的情况. 

## Copilot

现在我已经掌握了足够的信息，可以进行全面分析了。

---

## 分析：Script 标记识别的遗漏测试用例

基于对 prompt 规则、代码逻辑和现有用例的深入分析，以下是现有 case 集的**遗漏情况**，尤其聚焦在 **prompt 未覆盖的边界**。

---

## 一、现有用例覆盖情况总结

| 维度 | 现有覆盖 |
|---|---|
| 7 条正向规则（P01~P07） | ✅ 全部覆盖 |
| 明确负向（CALC函数、UI配置、概念性问题） | ✅ TC-N01~N06 |
| gui_required 覆盖 | ✅ 1 个（TC-G01） |
| 多轮对话 | ✅ 3 个（TC-M01~M03） |
| **contextType 差异** | ❌ 全部用 `dashboard`，特殊 context 未覆盖 |
| **prompt 规则歧义边界** | ❌ 多处缺失 |
| **LLM 输出异常/格式错误** | ❌ 完全未覆盖 |

---

## 二、具体遗漏分析

### 🔴 类别 A：`contextType` 相关遗漏（高优先级）

从 `contextMapping` 可以看到，有 `viewsheetScript`、`worksheetScript`、`chartScript`、`crosstabScript` 这几个**"Script 专属 context"**，但**所有现有 case 的 `contextType` 都是 `dashboard`**。这是最大的遗漏。

| 新 Case ID | contextType | 用户问题示例 | 预期 script | 遗漏原因 |
|---|---|---|---|---|
| **TC-CTX01** | `viewsheetScript` | What is the correct syntax for setting a component's visible property in a script? | `true` | 当 context 本身就是脚本环境时，script 应为 true。但 prompt 中没有规则说明 context 如何影响 script 判断，依赖 LLM 自行推断 |
| **TC-CTX02** | `worksheetScript` | How do I iterate over rows in a worksheet script? | `true` | 同上 |
| **TC-CTX03** | `chartScript` | What variables are available by default in a chart script? | `true` | 提问本身没有明确"写脚本"，但 context 决定了这就是脚本场景 |
| **TC-CTX04** | `viewsheetScript` | How do I add a new column to a table? | ❓ | **风险最高**：问题本身是 UI 操作，但 context 是脚本编辑器，prompt 没有明确指导这种"context 与 query 意图冲突"时的行为 |

**核心问题**：`querySubjectAreas.prompt` 的 Script Determination Rules **只看 query 内容**，完全没有提及 `current module` 对 script 判断的影响。当用户在 `viewsheetScript` 环境下提问但问题本身不含脚本关键词时，LLM 行为不可预期。

---

### 🔴 类别 B：规则 7（"Function Mention"）的边界模糊

规则 7 是最模糊的规则：`Query mentions "function"` 触发 `script=true`。现有用例 TC-P07 和 TC-N05 只覆盖了两个极端，中间有大量灰色地带：

| 新 Case ID | 用户问题 | 预期 script | 遗漏的边界 |
|---|---|---|---|
| **TC-F01** | What functions are supported in the Formula Editor? | `false` | "functions" 指产品内置函数列表，是**查询文档**而非**调用函数**。当前规则会误判为 `true` |
| **TC-F02** | How does the SUM function work in calculated fields? | `false` | CALC 函数的使用方法咨询，GUI 操作，不涉及脚本编写 |
| **TC-F03** | How do I use the IF function in an expression to return different values? | ❓ `true` | IF 是表达式语法，涉及表达式编写，**但** TC-N01 排除了 CALC 函数场景。这个灰色地带 prompt 描述不清 |
| **TC-F04** | What is the difference between the NOW() function and TODAY() function? | `false` | 纯概念性提问，"function" 出现了但完全是概念比较 |

**核心问题**：规则 7 的触发条件是 `mentions "function"` + `function-based operations`，但什么叫"function-based operations"在 prompt 中没有对比 TC-N05 的判定边界做清晰区分。

---

### 🟡 类别 C：多轮对话遗漏场景

现有 TC-M01~M03 只覆盖了"确认跟进"、"历史非脚本→当前脚本"、"历史脚本→当前非脚本"三种模式，以下场景未覆盖：

| 新 Case ID | 场景描述 | 预期 script | 遗漏原因 |
|---|---|---|---|
| **TC-M04** | 多轮脚本对话中间插入了一个 UI 问题（如 TC-M03），**再下一轮**继续脚本话题 | `true` | 测试 `completeQueryByHistory` 能否跳过中间非脚本轮，正确找到最近的脚本意图 |
| **TC-M05** | 历史对话含多个 SubjectArea（脚本 + 非脚本混合），当前问题模糊 | 取决于最新匹配 | `completeQueryByHistory` 的 Stack 搜索逻辑（从 index -1 到 0）在混合历史中的行为未测试 |
| **TC-M06** | 对话历史很长（5轮以上），最新的脚本意图在较早的轮次 | `true` | Stack 搜索深度是否有效、older context 是否会被正确利用 |
| **TC-M07** | 用户直接回复一个字段名 `"Sales Amount"` 作为脚本表达式变量确认 | `true` | `completeQueryByHistory` 的 Selection 处理 + 脚本方向保留的组合场景 |

---

### 🟡 类别 D：gui_required 判定不充分

只有 1 个 TC-G01 覆盖 `gui_required=true` 覆盖 `script=true` 的场景，缺少：

| 新 Case ID | 用户问题 | 预期 | 遗漏原因 |
|---|---|---|---|
| **TC-G02** | How do I navigate to the Script Editor panel and write an expression? | `false` | 同 TC-G01 但措辞不同，验证 gui_required 判定的稳定性 |
| **TC-G03** | Where do I find the admin console to run a script? | ❓ | Admin Console 触发规则 5（script=true），但**打开 Admin Console 本身**是 GUI 操作，gui_required 的边界在 prompt 中没有明确定义 |
| **TC-G04** | I want to write a JavaScript expression, can you show me which tab to open first? | `false` | 同时含 JavaScript（规则 2）和 GUI 导航请求，验证 isScriptModule 的覆盖是否稳定 |

**核心问题**：`gui_required` 的判断条件在 `prompts-v2` 版本中有明确规则：`user explicitly emphasizes that the task MUST be done via UI`，但旧版 `prompts/` 中**没有对应的 GUI Determination Rules**。如果系统使用的是旧 prompt，行为会有差异。

---

### 🟡 类别 E：`expression` 关键词的歧义

Prompt 规则 1 包含 "custom expressions"，但 StyleBI 中 "expression" 有双重含义：
- **脚本表达式**（script=true）：在 Script 编辑器写的 `field["Sales"] * 1.1`
- **CALC 表达式/Formula**（script=false）：在 Formula Editor 中通过 GUI 操作的公式

| 新 Case ID | 用户问题 | 预期 script | 遗漏原因 |
|---|---|---|---|
| **TC-E01** | How do I write an expression to calculate the year-over-year growth rate? | ❓ `true` | "expression" + "write" 组合，但可能是 Formula Editor，也可能是脚本。TC-N01 的 CALC 函数排除是否足够？ |
| **TC-E02** | How do I create a calculated field expression in Data Worksheet? | `false` | Formula Editor GUI 操作，但含 "expression"，考验 LLM 是否被误导 |
| **TC-E03** | How do I use field["fieldName"] syntax in an expression? | `true` | `field[...]` 语法是脚本/表达式专属语法，`completeQueryByHistory` 的 script 规则也特别提到此语法 |

---

### 🔵 类别 F：Prompt 未覆盖——LLM 输出格式异常

这是**纯 prompt 无法覆盖的代码层面问题**，在 `getSubjectAreaWithRetrieval.ts` 中有 `is not iterable` 的 fallback 处理，但测试中没有对应用例：

| 场景 | 当前处理 | 测试覆盖 |
|---|---|---|
| LLM 返回 `script` 字段缺失 | `parsed?.script ?? false` 兜底为 `false` | ❌ 未测试 |
| LLM 返回 `gui_required` 字段缺失 | `parsed?.gui_required ?? false` 兜底为 `false` | ❌ 未测试 |
| LLM 返回 YAML 格式错误 | `parseYaml` 异常处理 | ❌ 未测试 |
| `subjectAreas` 为空数组 | 用 `contextType` 填充默认值 | ❌ 未测试 |

---

## 三、优先级汇总

| 优先级 | 类别 | 遗漏 Case 数 | 风险 |
|---|---|---|---|
| 🔴 P0 | **contextType 专属 Script 环境**（viewsheetScript 等）| 4 个 | LLM 在脚本专属 context 下问非脚本问题时行为未定义 |
| 🔴 P0 | **规则 7 "Function" 边界（函数文档查询 vs 函数调用）** | 4 个 | TC-F01/F02/F04 极可能误判为 `true` |
| 🟡 P1 | **gui_required 边界（Admin Console + GUI 导航混合）** | 3 个 | TC-G03 的预期结果本身存在分歧 |
| 🟡 P1 | **多轮对话深度/混合历史** | 4 个 | Stack 搜索逻辑在复杂历史下的行为 |
| 🟡 P1 | **"expression" 关键词双重语义** | 3 个 | Formula Editor 表达式 vs 脚本表达式误判 |
| 🔵 P2 | **LLM 输出格式异常 fallback** | 4 个 | 代码健壮性，非 prompt 问题 |

---

## 四、最高风险的 Prompt 覆盖盲点

以下是 prompt 规则本身**没有明确处理**的情况，属于真正的规则漏洞：

```
1. 规则 7 没有排除"询问函数是什么/有哪些"（查询型 vs 调用型）
   → "What functions are supported?" 应该 = false，但当前规则会判 true

2. 没有任何规则说明当前 contextType 如何影响 script 判断
   → 用户在 viewsheetScript 环境中提问，即使问题本身不含脚本词汇也应该是 true

3. gui_required 规则只在 prompts-v2 中存在，prompts/ 目录没有
   → 两个版本的 prompt 行为不一致，TC-G01 在旧 prompt 下可能失败

4. "expression" 的脚本/GUI 双义性完全未在 script rules 中区分
   → 仅凭 "custom expressions" 措辞不足以区分 Formula Editor 的 GUI 表达式
```

## @bonnieshi43

类别 A：不存在, contextMapping 只是写了. 但是实际上不存在viewsheetScript、worksheetScript、chartScript、crosstabScript 这几个"Script 专属 context"

其他的几个类别, 帮我生成符合原来的格式的case, 方便我直接copy使用. 

## Copilot

好的，了解了格式，直接生成以下所有新 case：

---

## 新增 Test Cases（可直接 copy）

### 类别 B：规则 7 "Function" 关键词边界

```yaml name=SubjectArea-Script.yaml
  # --- Rule 7 "Function" boundary cases ---

  # CaseID: TC-F01
  # 类别: 负向用例（边界）
  # 验证规则: "function" 指内置函数文档查询，非代码调用（TC-P07 的边界）
  # 设计意图: 用户在询问产品中有哪些内置函数可用，是文档检索性质的提问。
  #   "function" 出现了但用户意图是查阅功能列表，而非编写/调用代码。
  #   规则 7 要求 "function-based operations"（使用/调用函数），
  #   纯粹询问函数列表不满足该条件，必须产生 script=false。
  - name: TC-F01
    question: What built-in functions are supported in the StyleBI Formula Editor?
    contextType: dashboard
    expScript: false

  # CaseID: TC-F02
  # 类别: 负向用例（边界）
  # 验证规则: "function" 指 CALC GUI 函数使用说明，非脚本（TC-P07 与 TC-N01 的交叉边界）
  # 设计意图: 用户询问如何在 Formula Editor 中使用 SUM 函数，属于 GUI 辅助的表达式输入，
  #   与 TC-N01 的 CALC 函数场景一致。虽然提到 "function" 但操作路径完全在 GUI 中完成。
  #   必须产生 script=false。
  - name: TC-F02
    question: How does the SUM function work when used in a calculated field in the Formula Editor?
    contextType: dashboard
    expScript: false

  # CaseID: TC-F03
  # 类别: 负向用例（边界）
  # 验证规则: "function" 出现在概念比较问题中，非调用意图（TC-P07 的边界）
  # 设计意图: 用户对两个内置函数进行概念性比较，没有编写、调用或操作任何函数的意图。
  #   "function" 出现多次但全部是名词性引用，无调用语义。必须产生 script=false。
  - name: TC-F03
    question: What is the difference between the NOW() function and the TODAY() function in StyleBI?
    contextType: dashboard
    expScript: false

  # CaseID: TC-F04
  # 类别: 正向用例（边界）
  # 验证规则: "function" 指表达式语法中的函数调用，涉及脚本/表达式编写（TC-P07 类型）
  # 设计意图: 用户询问如何在表达式（expression）中使用 IF 函数实现条件逻辑，
  #   这是脚本/表达式语法层面的操作，属于 "function-based operations" 的范畴。
  #   与 TC-N01 的差异在于用户意图是编写含逻辑的表达式，而非使用 GUI 向导。
  #   必须产生 script=true。
  - name: TC-F04
    question: How do I use the IF function inside an expression to return different text values based on a field condition?
    contextType: dashboard
    expScript: true
```

---

### 类别 C：多轮对话遗漏场景

```yaml name=SubjectArea-Script.yaml
  # --- Additional multi-turn conversation cases ---

  # CaseID: TC-M04
  # 类别: 多轮对话
  # 验证规则: 脚本历史中间插入非脚本轮后，继续脚本话题
  # 设计意图: 对话历史中最近一轮是非脚本的 UI 问题（TC-M03 模式），但当前轮重新引入
  #   明确的脚本意图（调用 runQuery）。completeQueryByHistory 使用 Stack 从最新一轮向前搜索，
  #   应识别当前轮自身携带的脚本信号，而非被上一轮的非脚本历史压制。
  #   验证：非脚本历史不会阻止当前轮独立判定为 script=true。
  - name: TC-M04
    question: Can I use runQuery in the same onInit handler to load a second dataset?
    contextType: dashboard
    chatHistory:
      - role: user
        content: How do I write a script in the onInit handler to load data using runQuery and assign the first record's value to a Text component?
      - role: assistant
        content: You can write a script in the onInit handler that calls runQuery() to fetch data, then access the first record and assign its value to the Text component using component.text = result[0].fieldName.
      - role: user
        content: How do I change the font size for the Text component using the Format panel?
      - role: assistant
        content: You can change the font size by selecting the Text component, opening the Format panel on the right, and adjusting the font size in the Font section.
    expScript: true

  # CaseID: TC-M05
  # 类别: 多轮对话
  # 验证规则: 脚本历史中，用户以字段名作为选项确认，script 方向应保留
  # 设计意图: completeQueryByHistory prompt 的 Selection 处理规则规定，当用户回复是一个选项/字段名时，
  #   需要结合历史重建高层意图，并在历史 script=true 时保持脚本导向。
  #   用户回复 "Sales Amount" 本身不含脚本信号，但历史上下文是脚本操作，
  #   replaced_query 必须被重建为表达式/脚本导向（例如"如何在表达式中引用 Sales Amount 字段"）。
  #   验证：字段名确认不会将脚本历史上下文切换为非脚本。
  - name: TC-M05
    question: Sales Amount
    contextType: dashboard
    chatHistory:
      - role: user
        content: How do I write a script to calculate the aggregation of a field and assign the result to a label?
      - role: assistant
        content: You can use sum() or other aggregation functions in the script. Which field would you like to aggregate — Sales Amount, Profit, or Quantity?
    expScript: true

  # CaseID: TC-M06
  # 类别: 多轮对话
  # 验证规则: 较长历史（5 轮），最近一轮为脚本轮，当前轮为模糊跟进
  # 设计意图: 测试 completeQueryByHistory Stack 搜索在较长对话中的稳定性。
  #   历史含多轮交替的脚本与非脚本内容，但最近一轮（index -1）是脚本导向，
  #   当前轮 "What about the second condition?" 是模糊跟进，不含独立脚本信号。
  #   Stack 从最新轮向前搜索，应匹配最近的脚本历史轮并重建脚本导向的 replaced_query。
  #   验证：Stack 搜索能在多轮历史中正确找到最近相关的脚本上下文。
  - name: TC-M06
    question: What about the second condition?
    contextType: dashboard
    chatHistory:
      - role: user
        content: How do I create a new table component on a dashboard?
      - role: assistant
        content: You can drag a Table element from the component panel onto the dashboard canvas.
      - role: user
        content: How do I bind a data field to a table column?
      - role: assistant
        content: Select the table, open the Data Binding panel, and drag the field to the desired column slot.
      - role: user
        content: How do I write a script with nested if-else conditions to set the row background color based on multiple value ranges?
      - role: assistant
        content: You can write a script using nested if-else blocks. For example, if (value > 1000) { color = 'red'; } else if (value > 500) { color = 'yellow'; } else { color = 'green'; } Then assign this color to the row's background property.
    expScript: true
```

---

### 类别 D：`gui_required` 边界扩充

```yaml name=SubjectArea-Script.yaml
  # --- Additional gui_required override cases ---

  # CaseID: TC-G02
  # 类别: gui_required 覆盖
  # 验证规则: GUI 导航 + 脚本编写混合，gui_required 覆盖 script（isScriptModule 逻辑）
  # 设计意图: 与 TC-G01 意图相同但措辞不同，用于验证 gui_required 判定的语言稳定性。
  #   "navigate to" 明确是 GUI 操作步骤，即使后半句提到编写表达式，
  #   gui_required=true 必须优先，isScriptModule(true, true) = false。
  #   验证：不同措辞的 GUI 导航请求均能稳定触发 gui_required=true。
  - name: TC-G02
    question: How do I navigate to the Script Editor panel and write an expression to dynamically change the chart title?
    contextType: dashboard
    expScript: false

  # CaseID: TC-G03
  # 类别: gui_required 覆盖（边界）
  # 验证规则: Admin Console 操作（规则 5）与 GUI 导航的叠加——gui_required 覆盖 script
  # 设计意图: "Admin Console" 触发规则 5（script=true），但 "where do I find" 是位置导航提问，
  #   表明用户首先需要通过 UI 界面找到 Admin Console 入口，属于 GUI 操作步骤。
  #   prompt 中 gui_required 规则要求用户"明确强调任务必须通过 UI 完成"，
  #   此处 "find" 暗示了界面导航需求，预期 gui_required=true 覆盖 script=true，最终 script=false。
  #   验证：Admin Console 规则与 gui_required 覆盖的优先级行为。
  - name: TC-G03
    question: Where do I find the Admin Console in the portal to run a server-side script?
    contextType: dashboard
    expScript: false

  # CaseID: TC-G04
  # 类别: gui_required 覆盖
  # 验证规则: 编程语言引用（规则 2）+ GUI 步骤引导请求，gui_required 覆盖 script
  # 设计意图: 查询包含 JavaScript（触发规则 2，script=true），同时用户要求被引导完成"先打开哪个 tab"，
  #   表明需要 GUI 操作步骤，应触发 gui_required=true。
  #   isScriptModule(true, true) 必须返回 false。
  #   验证：规则 2 与 gui_required 覆盖同时触发时，代码层覆盖逻辑正确运行。
  - name: TC-G04
    question: I want to write a JavaScript expression for a component — which tab do I need to open first in the properties panel?
    contextType: dashboard
    expScript: false
```

---

### 类别 E：`expression` 关键词双重语义

```yaml name=SubjectArea-Script.yaml
  # --- "expression" keyword ambiguity cases ---

  # CaseID: TC-E01
  # 类别: 正向用例（边界）
  # 验证规则: "write" + "expression" 组合，脚本语法场景（TC-N01 的边界）
  # 设计意图: "write an expression" 的措辞组合了规则 1 的 "writing" 触发词和 "expression"。
  #   与 TC-N01 的区别在于此处没有提到 CALC 或 Formula Editor，而是指向通用表达式编写，
  #   含有编写意图（"write"），应触发 script=true。
  #   验证：在没有 CALC/Formula Editor 上下文时，"write an expression" 必须判为脚本。
  - name: TC-E01
    question: How do I write an expression to calculate the year-over-year growth rate for a field?
    contextType: dashboard
    expScript: true

  # CaseID: TC-E02
  # 类别: 负向用例（边界）
  # 验证规则: "expression" 出现在 Formula Editor GUI 操作上下文中，非脚本（TC-N01 类型）
  # 设计意图: 用户要在 Data Worksheet 中创建 calculated field，使用 Formula Editor 输入表达式，
  #   这是完全由 GUI 辅助完成的操作。虽然包含 "expression" 一词，但操作路径是 UI 向导，
  #   与 TC-N01 同类。必须产生 script=false。
  - name: TC-E02
    question: How do I create a calculated field expression in the Data Worksheet using the Formula Editor?
    contextType: dashboard
    expScript: false

  # CaseID: TC-E03
  # 类别: 正向用例（边界）
  # 验证规则: field["fieldName"] 语法引用，脚本专属表达式语法
  # 设计意图: field["fieldName"] 是 StyleBI 脚本/表达式中的字段引用语法，只在脚本上下文中出现，
  #   completeQueryByHistory 的 Script Identification Rule 也专门列举了此语法。
  #   用户询问该语法的使用方式，意图明确是理解/编写脚本表达式。必须产生 script=true。
  - name: TC-E03
    question: How do I use the field["fieldName"] syntax to reference a column value in a script expression?
    contextType: dashboard
    expScript: true
```

---

**说明**：
- 所有 case 保持与现有 YAML 完全一致的格式（缩进、字段顺序、注释风格）
- TC-F04 / TC-E01 / TC-E03 是**正向用例**，`expScript: true`，注意不要和纯负向边界混淆
- TC-G03 的 `expScript: false` 有一定 LLM 不确定性（Admin Console 规则 vs GUI 导航），如需保守测试可暂时移除或标注 `# 待验证`
- TC-F04 和 TC-E01 可能存在 LLM 分歧，建议在 CI 首次运行时观察实际结果再决定是否纳入回归
