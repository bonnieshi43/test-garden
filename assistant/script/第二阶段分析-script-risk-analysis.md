## subjectAreas 中 script 识别规则与代码逻辑的潜在测试风险点

### 1. script 判定高度依赖 LLM 语义理解，易出现误判

- **风险描述**  
  - `querySubjectAreas.prompt` 中的 `Script Determination Rules` 全部是自然语言规则，由 LLM 自行判断是否满足 7 条触发条件中的任意一条。  
  - 对边界语义（如 “写一个公式” vs “设置一个条件”）的理解可能存在不稳定性，容易出现 **false positive / false negative**。  
- **可能影响**  
  - 相同或相似的用户输入在不同对话、不同温度、不同模型版本下，得到的 `script` 判定结果不一致，导致脚本流程、UI 流程在不同轮次切换，影响用户体验和可复现性。  
- **建议测试方向**  
  - 设计一组 **语义相近但措辞变化较大** 的用例（含中英混合），验证同一意图下脚本判定的一致性。  
  - 针对每条脚本触发规则（1–7）分别设计 **强触发样例** 与 **弱/模糊样例**，观察是否存在明显误判。  
  - 在不同模型配置（如 thinkMode / 温度）下重复执行同一批用例，检查结果稳定性。  

### 2. “function” 关键词语义歧义导致的误判风险

- **风险描述**  
  - 规则中将“提到 function”视为脚本触发条件之一，但从业务语义上，用户也可能以“function/功能”指代普通产品功能，而非代码函数。  
  - 例如：“这个功能（function）怎么用？”、“这个导出功能是做什么的？” 可能被 LLM 识别为脚本场景。  
- **可能影响**  
  - 非脚本问题被错误标记为 `script = true`，从而被误路由到脚本解答链路，回答风格偏向代码/表达式，降低可读性。  
- **建议测试方向**  
  - 设计一批包含单词 “function” 但明确是 **产品功能/特性** 含义的用例，验证是否会被误识别为脚本。  
  - 对比：  
    - “写一个自定义函数 function()…”（应为 script=true）  
    - “这个导出功能（export function）怎么用？”（应为 script=false）  
  - 覆盖中英文、以及“功能 / 函数 / 函式”等同义词，观察 LLM 判定鲁棒性。  

### 3. “编程语言” 识别与泛指描述的边界风险

- **风险描述**  
  - 规则中只要提到具体语言（JavaScript、Python 等）就会偏向 `script = true`，但用户可能只是 **泛指技术栈**，而非真正编写脚本。  
  - 例如：“系统是不是用 JavaScript 写的？”、“这个功能底层是不是 Python 实现的？” 实际上并不需要脚本支持。  
- **可能影响**  
  - 引导用户对话走入与脚本无关的技术实现细节，甚至影响 SubjectArea 与工具路由。  
- **建议测试方向**  
  - 设计包含编程语言名称但表达 **非编码意图** 的用例，确认不会被稳定地误判为 script=true。  
  - 同时设计真正需要编写脚本的用例（例如 “写一个 JavaScript 脚本实现...”），对比两者在多轮对话中的判定差异。  

### 4. “复杂逻辑” 与 “自定义函数” 判断标准模糊

- **风险描述**  
  - Prompt 中用“多层条件、循环”等概念粗略定义“复杂逻辑 / 自定义函数”，但在自然语言中，用户经常以模糊表达方式描述复杂业务逻辑。  
  - LLM 对“复杂程度”的主观判断容易波动。  
- **可能影响**  
  - 逻辑看似复杂但可以通过内置功能完成的场景，可能被判为 script=true，导致系统优先给出脚本解决方案，而不是推荐内置图形化功能。  
  - 反之，真正需要脚本才能实现的复杂场景有可能被判为 script=false，错失脚本建议。  
- **建议测试方向**  
  - 设计一批 **可通过 GUI 实现但描述略显复杂** 的场景，验证是否错误归类为脚本。  
  - 设计一批 **必须借助脚本才能完成** 的场景，检查是否总能稳定触发 script=true。  
  - 在多语言（中/英）和多表达风格（口语化、专业术语）下进行对比。  

### 5. `runquery` 触发规则覆盖不全的风险

- **风险描述**  
  - 规则以“涉及 runquery 使用”为脚本触发条件，但用户可能会以多种方式提及：  
    - 使用缩写 / 错拼：`runQuery`、`run query`、`run-query` 等。  
    - 中文描述：“运行查询结果”、“执行查询返回的数据”等，并未显式出现 `runquery` 字样。  
- **可能影响**  
  - 依赖 `runquery` 的脚本场景可能被漏判为 script=false，后续回答偏向 GUI 或概念说明，而没有给出脚本层面的指导。  
- **建议测试方向**  
  - 设计多种大小写、错拼、分词（runquery / run query / runQuery 等）以及中英混合表达的用例。  
  - 设计纯中文但语义上“基于运行查询结果编写表达式”的场景，观察是否仍能触发 script=true。  

### 6. `gui_required` 与 `script` 组合逻辑的风险（`isScriptModule`）

- **风险描述**  
  - 代码中最终脚本标记依赖：`isScriptModule(gui_required, script) => !gui_required && script`。  
  - 这意味着一旦 prompt 判定 `gui_required = true`，即使 `script = true`，最终也会被归一化为 **非脚本场景**。  
- **可能影响**  
  - 用户表述中同时包含“需要脚本”和“希望在界面上操作”的信息时，可能被偏向 GUI 路径，无法给出脚本级解决方案。  
  - prompt 中对 `gui_required` 的判定稍有偏差，就会完全覆盖掉脚本标记。  
- **建议测试方向**  
  - 设计同时包含 “脚本需求 + 明确 UI 偏好” 的混合表达，例如：“我想用脚本写，但最好能在界面里配置一下”。  
  - 检查在不同措辞下，`gui_required` 与 `script` 的组合结果，以及最终 `isScriptModule` 输出。  
  - 单独验证以下四种组合是否符合预期：  
    - `gui_required=false, script=false`  
    - `gui_required=false, script=true`  
    - `gui_required=true, script=false`  
    - `gui_required=true, script=true`（关键边界）。  

### 7. `completeQueryByHistory` 中历史 script 标记与当前 script 不一致的风险

- **风险描述**  
  - 历史 SubjectArea 的 `script` 标记仅存在于 `completeQueryByHistory.prompt` 内部，用来决定 `replaced_query` 的“表达式导向”或“操作导向”；  
  - 最终对外暴露的 `result.script` 完全来自 **当前轮的 `querySubjectAreas.prompt`** 判断，而不是历史。  
  - 多轮对话中，**历史的脚本/非脚本意图与当前 prompt 判定的脚本意图可能发生冲突**。  
- **可能影响**  
  - 场景：前几轮是脚本问题（history.script=true），当前用户用一句“是的，就那样”确认，但当前轮的 `querySubjectAreas.prompt` 因表达太短将 `script` 判为 false：  
    - `completeQueryByHistory.prompt` 会基于历史脚本意图构造一个脚本导向的 `replaced_query`；  
    - 但 `getSubjectArea` 最终返回的 `result.script` 却是 false，`isScriptModule` 也输出 false，导致回答链路被视为非脚本场景。  
- **建议测试方向**  
  - 设计多轮脚本对话，最后一轮用简短确认/选择语句（“是的”、“选第一个”、“就按你说的那个脚本”），观察：  
    - `replaced_query` 内容是否仍保留脚本语义；  
    - 同时当前轮 `result.script` 是否会错误变成 false。  
  - 对照非脚本对话的同类场景，验证历史为非脚本时不会错误地被补全为脚本导向 query。  

### 8. YAML 解析默认值导致脚本信息丢失的风险

- **风险描述**  
  - `getSimpleSubjectArea` 中解析：`const script = parsed?.script ?? false;`  
  - 当 LLM 输出缺失 `script` 字段或格式不标准时，会被 **静默地归一化为 false**。  
- **可能影响**  
  - 某些本应为脚本场景的用例，如果因 LLM 输出格式异常（漏字段、键名大小写错误）而未包含 `script`，会被错误视作非脚本，且难以从日志中直接发现原因。  
- **建议测试方向**  
  - 构造 LLM 输出异常场景（可以通过代理/Mock 或灰盒测试）：  
    - 缺失 `script` 字段；  
    - 将 `script` 误写为 `Script` 或嵌套到其他对象中。  
  - 验证系统在这两类情况下的处理行为是否可接受，是否需要额外的鲁棒性检查（如与历史脚本标记对比）。  

### 9. 多 SubjectArea 与脚本标记组合的风险

- **风险描述**  
  - `querySubjectAreas.prompt` 中 `script` 是一个全局字段，**并不区分每个 SubjectArea 单元**；  
  - 但在历史补全 prompt 中，`script` 是 per-subjectArea 的标记。  
  - 在一个复杂问题中既包含脚本需求又包含普通配置需求时，全局 `script`=true 可能过度“脚本化”整个回答。  
- **可能影响**  
  - 某些原本只需要简单配置的模块也被错误归入脚本场景，导致回答对普通用户不友好。  
- **建议测试方向**  
  - 设计“混合意图”用例：同一轮问题中同时包含“写表达式”和“设置某个界面选项”。  
  - 观察：  
    - 全局 `script` 是否被判为 true；  
    - 回答是否在所有模块都倾向于给出脚本方案，而非按模块分别选择合适的呈现方式。  

### 10. 上下文类型（contextType）对脚本判定间接影响的风险

- **风险描述**  
  - `getEnhancedSubjectAreas` 会根据 `parsedContext.contextType` 筛选/生成特定 SubjectArea（chart / table / crosstab / freehand / worksheet 等），并保留原有 `script` 标记。  
  - 虽然脚本布尔值不直接依赖 `contextType`，但被筛选/构造出来的 SubjectArea 组合会影响后续节点如何解释脚本场景。  
- **可能影响**  
  - 在 Worksheet / Dashboard 之间切换时，用户对脚本的期望位置（数据准备脚本 vs 视图脚本）可能不同，而当前逻辑仅有一个统一的 script 标记，无法精细区分。  
- **建议测试方向**  
  - 针对不同 `contextType`（chart / table / crosstab / freehand / worksheet）分别设计脚本相关问题，观察：  
    - `subjectAreas` 的结果是否合理；  
    - `script` 标记与具体模块是否匹配用户期望（例如 Worksheet 脚本 vs Dashboard 脚本）。  

---

以上风险点可直接作为设计脚本标记相关测试用例的参考，每个风险建议至少设计：  
- 1 组正向样例（应该触发或不触发脚本）；  
- 1 组边界样例（语义模糊、表达简略或中英混合）。  

