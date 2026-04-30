# Excel → High-Value E2E Scenarios Prompt (Universal)

从碎片化、表格化的 Excel 测试点中，**重构**出高价值、可执行、低冗余的 E2E 场景，并确保每条业务规则都有 P1/P2 场景覆盖。

---

## 一、输入分析

分析输入的 Excel，自动选择处理路径：

### Step 1: 复杂度检测

检测以下特征（任一项为 Yes 则复杂）：

| 特征 | 检测规则 | Yes/No |
|------|---------|--------|
| 外部引用 | 含「请看」「refer to」+ 其他文件名 | [ ] |
| 层级嵌套 | 缩进表示父子关系 | [ ] |
| Bug/Feature 标注 | 含 `Bug #/Feature #` 或 `#Bug` | [ ] |
| 跨组件同步 | 同时涉及 EM、Portal| [ ] |
| 安全变体 | 含 security / multi-tenant / org | [ ] |

### Step 2: 外部引用处理

当检测到外部引用（含 `请看`、`refer to`、`see` + 其他文件名/路径）时：

**决策规则：**
- 主文件 = 当前输入的 Excel
- 引用文件 = 匹配到的外部文件名
- **策略**：引用文件**不生成独立场景**，仅作为主文件相关场景的**补充检查点**

**不补充的内容：**
- 引用文件中与主文件主题词无关的场景
- 引用文件中的独立功能（除非主文件明确要求）
- 引用文件中的基础 CRUD/UI 测试点

---

## 二、场景类型识别与优先级

### Step 1: 场景类型判定

从 Excel 测试点识别场景类型，决定处理策略：

| 类型 | 特征 | 处理 | 默认优先级 |
|------|------|------|------------|
| **CRUD + 关联** | 创建/修改/删除 + 影响其他模块 | 保留，合并为业务叙事 | P1 |
| **权限控制** | 角色、权限、grant、deny、admin | 保留 | P1 |
| **多租户隔离** | 组织、tenant、跨组织、security | 保留 | P1 |
| **跨模块同步** | EM、Portal、Studio、Monitor 间数据一致 | 保留 | P1 |
| **状态持久化** | 刷新后、重新登录后、保存后仍生效 | 保留 | P1 |
| **删除级联** | 删除、cascade、阻止删除、依赖检查 | 保留 | P1 |
| **Bug 修复** | Bug #XXXXX | 融入主线场景 | - |
| **功能增强** | Feature #XXXXX | 融入主线场景 | - |
| **业务边界** | 特殊字符、空值、重名、超长（后端拒绝） | **丢弃** | - |
| **纯 UI** | 滚动条、拖拽、排序、悬浮效果、对话框动画 | **丢弃** | - |
| **纯前端校验** | 密码长度、邮箱格式（仅前端提示） | **丢弃** | - |

### Step 2: Bug/Feature 融入规则

当检测到 Bug/Feature 标注（`Bug #`、`Feature #`、`#Bug`、`#Feature`）时：

**融入策略：**
1. 判断该 Bug/Feature 是否属于**主线业务流程**
2. 若属于 → 融入相关主线场景，在步骤或断言后标注 `(fixes Bug #XXXXX)` 或 `(implements Feature #XXXXX)`
3. 若不属于（独立边缘场景）→ 保留为独立 `P2` 场景，标题 `TC-XXX Bug Regression: {summary}`

**禁止：**
- 为每个 Bug 单独创建场景（除非无法融入任何主线场景）
- 在场景中只验证「Bug 不再出现」而不验证正确的业务行为

### Step 3: 场景命名标注

每个场景标题后标注类型标签：

| 标签 | 含义 |
|------|------|
| `[CRUD]` | 创建/读取/更新/删除核心流程 |
| `[Permission]` | 权限控制验证 |
| `[Cross-Module]` | 跨模块数据同步 |
| `[Multi-Tenant]` | 多租户隔离 |
| `[Feature]` | 可配置 Feature |
| `[Edge]` | 业务边界/异常 |

---

## 三、高价值过滤

### Layer 1 — 纯 UI 噪音（直接丢弃）

**Always discard:**
- scrollbar / drag / resize / 展开/折叠
- dialog 打开/关闭动画 / loading 指示器
- "can select", "can click", "displays correctly"，"pop up prompts"
- 排序 / 滚动条 / 工具栏工作正常

**Discard unless tied to permission/state:**
- 按钮 enabled/disabled（除非验证权限）
- 元素可见/不可见（除非验证权限）
- 选中/未选中状态（除非验证状态持久化）


## 四、关联验证（轻量级）

不强制要求每个 CUD 操作都有关联验证，但鼓励在以下情况添加：

| 操作 | 建议验证点 |
|------|-----------|
| 创建用户/组/角色 | 验证在列表中出现 + 相关引用处可见 |
| 修改权限 | 验证实际权限生效（登录后访问资源） |
| 删除资源 | 验证在所有引用处消失 |

**格式：** 需要关联验证时，使用 `**Verify:**` 标注

---

## 五、规则覆盖检查（轻量级）

### Step 1: 规则提取

从 Excel 中提取以下类型的规则：
- 数据约束（唯一性、必填）
- 状态流转条件
- 权限规则（谁能做什么）
- 级联规则（删除影响）

**不提取**：UI 布局规则、纯前端校验规则。



## 六、安全模式压缩（防止组合爆炸）

当检测到 security / tenant 变体时：

**覆盖策略：**

| 场景 | 覆盖数 |
|------|--------|
| security=false | 1 个代表场景 |
| security=true, single-tenant | 2 个（grant + deny） |
| security=true, multi-tenant | 2 个（同组织 + 跨组织） |

**不生成：** N 种模式 × M 个测试点的全组合

---

## 七、跨端同步合并

检测到多个组件（EM、Portal）时，**合并为 1 个场景**


## Output Format

**Language:** English

```markdown
---
module: {module name}
source: {Excel filename}
Excel-path: [direct | two-phase]
last-updated: YYYY-MM-DD

---

## Filtering Summary

| Category | Count |
|----------|-------|
| Discarded UI scenarios | X |
| Kept P1 | X |
| Kept P2 | X |
| Needs clarification | X |

## Feature Summary

{2-4 sentences: what problem, primary users, core business objects}

## Rules & Notes

### Business Rules
- {从 Excel 提取的核心业务规则}

### Security & Multi-Tenancy (if applicable)
- **security=false:** {baseline}
- **security=true:** {constraints}
- **multi-tenant:** {isolation rules}


## Scenario Overview

| ID | Priority | Area | Scenario | Key Business Assertion |
|----|----------|------|----------|----------------------|
| TC-001 | P1 | CRUD | [summary] | [assertion] |

## Scenarios

#### TC-001 Scenario Name `P1`

**Scope:** {module boundary}
**Validates rule:** {business rule reference}

**Pre-conditions:** {system state / login role / required data}

**Steps:**
1. [action with clear business impact]
2. **Sync check:** [if cross-component]

**Expected:**
- [verifiable business assertion]

---

#### TC-00X Bug Regression `P2`

> **Bug #XXXXX** — {what broke before}

**Regression focus:** {what to verify}
**Pre-conditions:** {required state}
**Steps:** 1. [trigger] 2. [verify fix]
**Expected:** {correct behavior}

---

## Uncovered Rules

> 以下规则没有对应的 P1/P2 场景覆盖。P3 规则已丢弃。

| Rule ID | Rule Description | Priority | Reason / Suggested Fix |
|---------|------------------|----------|------------------------|
| R-001 | {规则原文} | P2 | [NEEDS SCENARIO]: {minimal suggestion} |

---

## Clarification Needed

| Item | Location | Issue |
|------|----------|-------|
| [description] | [sheet/cell] | [what's unclear] |

---

## Related Module Tests

| Related Module | Relationship | Suggested Extension |
|----------------|-------------|---------------------|
| Security | Permission affects visibility | Run after Security tests |