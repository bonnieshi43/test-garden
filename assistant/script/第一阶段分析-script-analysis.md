## subjectAreas 中 script 标记逻辑分析

### 1. script 在哪些情况下为 true / false

- **来源 1：`querySubjectAreas.prompt` 中的主判断（最终影响代码中的 `result.script`）**  
  - **script = true** 仅当满足以下任一条件（满足任一即可）  
    1. **显式脚本/代码相关**：用户明确提到编写、创建或编辑脚本、代码或自定义表达式  
    2. **提到编程语言**：如 JavaScript、Python 等  
    3. **需要复杂逻辑控制**：包含多层嵌套条件、循环等复杂控制结构  
    4. **自定义函数**：需要定义新的函数或算法，而不是用内置功能  
    5. **Admin Console 操作**：用户提到 “admin console” 或必须在管理控制台里完成的操作  
    6. **涉及 `runquery`**：任何与 `runquery` 结果使用或处理相关的查询  
    7. **显式提到 “function”**：如使用函数、调用函数、基于函数的操作  
  - **script = false**：除上述所有条件以外的所有情况，统一视为 `script = false`。  
  - **对应代码读取位置**：  
    - `querySubjectAreas.prompt` 中的 **Script Determination Rules** 最终输出一个顶层字段 `script: <true|false>`，被 `getSimpleSubjectArea` 解析并传入后续逻辑。  

- **来源 2：`completeQueryByHistory.prompt` 中的历史脚本标记（仅用于补全 query，不影响最终 `result.script`）**  
  - 在该 prompt 中，每条历史 SubjectArea 都有一个内部的 `script` 标志，用于区分：  
    - **script = true**：该轮问题主要是关于表达式 / 公式 / 脚本（字段引用、相对行、表达式列、函数与计算逻辑等）。  
    - **script = false**：该轮问题主要是关于 UI 操作路径 / 菜单设置 / 权限 / 功能用法 / 概念性说明等。  
  - 这个标记只用于在 **Phase 2 Completion Algorithm** 里重写 `replaced_query`（决定补全后的 query 是 “表达式导向” 还是 “操作导向”），**不会回传到 TypeScript 中的 `SubjectAreasOutput.script` 字段**。  

- **最终在代码中的综合判定（真正影响 ChatState 的脚本标记）**  
  - 在节点 `determineSubjectAreas` 中，最终脚本标记是：  
    - `const script = isScriptModule(result.gui_required, result.script);`  
    - `isScriptModule(gui_required, script)` 的实现为：  
      - `return !gui_required && script;`  
  - 因此：  
    - **最终 `script = true` 条件**：  
      - `querySubjectAreas.prompt` 判定为 `script: true` **且** `gui_required` 不为 `true`。  
    - **最终 `script = false` 条件**：  
      - `querySubjectAreas.prompt` 判定为 `script: false`；**或**  
      - `gui_required = true`（即使 `script=true` 也会被强制视为 “非脚本场景”，因为需要 GUI）。  

### 2. script=true / script=false 影响的逻辑分支

- **在 subjectAreas 检索阶段（`getSubjectArea.ts`）**  
  - `script` 的值从 prompt 解析后一路保留，并在以下路径中透明传递：  
    - `getSimpleSubjectArea` → `SubjectAreasOutput.script`  
    - `getEnhancedSubjectAreas` → 根据历史和上下文增强后，仍保留 `script` 字段（不做任何修改）。  
  - 在这个阶段，`script` **不会改变 SubjectArea 的筛选与排序逻辑**，仅作为一个随结果返回的标记。  

- **在 chat agent 的 subjectAreas 节点（`subjectAreas.ts`）**  
  - 关键代码：  
    - `const script = isScriptModule(result.gui_required, result.script);`  
  - 逻辑效果：  
    - 如果 `gui_required` 为 `false` / `undefined` 且 `result.script` 为 `true`：  
      - **当前对话轮会被下游视为 “脚本/表达式问题” 场景**。  
    - 如果 `gui_required` 为 `true`，即使 `result.script = true`：  
      - `isScriptModule` 仍返回 `false`，标记为非脚本问题，偏向 GUI 操作场景。  
  - `determineSubjectAreas` 返回的 `script` 字段会写入 `ChatState`，随后可能被：  
    - 路由到 **脚本相关的 agent / 工具链**（如表达式编写助手、脚本检查等）；  
    - 或在后续对话中被 prompt 用作条件，用以区分 “脚本回答模式” vs “操作/功能使用回答模式”。  
  - 当前仓库里，`script` 只在 `subjectAreas` 节点层面对外暴露，下游更具体的使用需要结合其他模块（本分析以 subjectAreas 相关代码为界）。  

### 3. subjectAreas prompt 中所有与 script 判断相关的规则

- **`querySubjectAreas.prompt` 中的 script 规则**  
  - 规则块名：`### 6. Dynamic & Script & GUI Determination Logic`  
  - **Script Determination Rules**：  
    - `script = true` **仅当**满足任一：  
      1. 显式脚本/代码创建或编辑（脚本、代码、自定义表达式）。  
      2. 明确提及编程语言（JavaScript、Python 等）。  
      3. 需要复杂逻辑控制结构（多层条件、循环等）。  
      4. 需要定义新的函数或算法（非内置功能）。  
      5. 涉及 admin console 操作。  
      6. 使用或操作 `runquery` 结果。  
      7. 提到 “function” 并指向函数使用/调用/基于函数的操作。  
    - **否则**：`script = false`。  

- **`completeQueryByHistory.prompt` 中的 script 规则（仅限历史补全）**  
  - 规则块名：`## Script Identification Rule`。  
  - **Per-subjectArea script 标记**：  
    - 对每条历史 SubjectArea：  
      - `script = true`：问题主要围绕表达式/公式/脚本（字段引用、相对行、表达式列、函数/计算逻辑等）。  
      - `script = false`：问题主要是 UI 操作、菜单路径、权限管理、功能用法或概念性解释。  
  - **在 Completion Algorithm 中的作用**：  
    - 当当前 `user query` 是确认/选择类短句（Yes/No、选项、列名等）时：  
      - 如果最近的相关 SubjectArea `script = true`：  
        - `replaced_query` 必须保持 “表达式/脚本导向” 的重写，不允许被改写为纯界面操作问题。  
      - 如果最近 SubjectArea `script = false`：  
        - `replaced_query` 会被重写为操作/配置/功能使用导向的自然语言意图。  
  - 注意：该内部 `script` 标记只参与 query 补全逻辑，不透出到 `SubjectAreasOutput.script`。  

### 4. 所有涉及 script 判断的代码文件与函数

- **1）`chat-app/server/prompts-v2/subjectAreas/querySubjectAreas.prompt`**  
  - **相关内容**：  
    - `### 6. Dynamic & Script & GUI Determination Logic` 中的 `Script Determination Rules`  
    - 定义最终对外 YAML 字段：`script: <true|false>`。  

- **2）`chat-app/server/prompts-v2/subjectAreas/completeQueryByHistory.prompt`**  
  - **相关内容**：  
    - `## Script Identification Rule`  
    - Phase 1 中为历史 SubjectArea 标注 `script`（表达式导向 vs 操作导向）。  
    - Phase 2 Completion Algorithm 根据该 `script` 决定 `replaced_query` 的补全文本风格。  

- **3）`chat-app/server/src/tools/retrieval/getSubjectArea.ts`**  
  - **接口与数据结构**：  
    - `export interface SubjectAreasOutput { ... script?: boolean; gui_required?: boolean; ... }`  
  - **函数及 script 相关逻辑**：  
    - `getSimpleSubjectArea(...)`  
      - 从 `querySubjectAreas.prompt` 的 YAML 中解析：  
        - `const script = parsed?.script ?? false;`  
      - 并将其封装进 `SubjectAreasOutput` 返回。  
    - `getEnhancedSubjectAreas(...)`  
      - 接收 `simpleOutput` 或历史增强结果，保留并透传 `output.script`：  
        - 在所有 `return` 分支里都包含 `script: script`。  
    - `getCompletedQuery(...)`  
      - 使用 `completeQueryByHistory.prompt` 补全 query，但不处理脚本标记，只返回 `replaced_query` 字符串。  
    - `isScriptModule(gui_required?: boolean, script?: boolean)`  
      - 最终脚本模块标记的统一出口：  
        - 实现为 `return !gui_required && script;`。  

- **4）`chat-app/server/src/agents/chatAgent/nodes/subjectAreas.ts`**  
  - **主流程函数**：  
    - `export const determineSubjectAreas = ...`  
  - **script 相关逻辑**：  
    - 调用 `getSubjectArea(...)` 获取 `result.script` 与 `result.gui_required`。  
    - 调用 `isScriptModule` 做最终归一化：  
      - `const script = isScriptModule(result.gui_required, result.script);`  
    - 将归一化后的 `script` 写入 `ChatState`，作为后续 agent/节点判断是否走脚本相关路径的依据。  

---

以上内容即为当前项目中 subjectAreas 场景下所有与 `script` 标记有关的 prompt 规则与代码逻辑的完整梳理，可直接用于测试用例设计与逻辑验证。

