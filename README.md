## test-garden

用于管理和存储各种 Prompt，包括：
- **日常使用的 Prompt**：如写作、翻译、代码辅助、产品需求等
- **专项优化的 Prompt**：针对某一类任务不断迭代调优的版本
- **调试与实验用 Prompt**：用于测试不同提示策略、结构和参数的效果

### 仓库克隆方式

使用 `git clone` 将仓库克隆到本地（示例以 HTTPS 为例，可按需改为 SSH）：

```bash
git clone https://github.com/bonnieshi43/test-garden.git
```

克隆完成后进入项目目录：

```bash
cd test-garden
```

### 主要用途

- **统一管理 Prompt**：集中管理不同场景下使用的 Prompt，方便复用与分享  
- **Prompt 调试与测试**：记录不同版本 Prompt 的实验过程和效果对比  
- **知识沉淀**：把在 Prompt 设计、调试过程中得到的经验、案例和最佳实践固化到仓库中，方便后续查阅和迭代

---

### 推荐仓库结构（针对 bug / 功能分析与 inetsoft 知识）

**思路**：按「用途（bug 分析 / 功能分析）」+「对象（inetsoft 及模块）」来组织；Prompt 与知识分开存放，但路径和命名保持强关联。

#### 根目录结构示例

```text
test-garden/
  README.md
  prompts/
  knowledge/
  test-docs/
  experiments/
  features/
  concurrency-test/
  ai-assistant/
```

#### `knowledge/` 与 `test-docs/` 的定位

- **`knowledge/`**：产品/模块知识沉淀（便于 AI 检索与复用），规范见 `knowledge/README.md`
- **`test-docs/`**：测试文档归档（测试用例/测试报告/缺陷记录/环境与数据等），目录说明见 `test-docs/README.md`

#### Prompt 文件内部结构建议

每个 Prompt 使用 `Markdown`，并加简单元信息，方便后续工具化管理：

```markdown
---
type: bug-analysis           # bug-analysis | feature-analysis
scope: inetsoft-dashboard    # 适用范围
level: senior                # 目标使用人群
---

# 使用场景
- ...

# Prompt 模板
你现在是...

# 使用示例
- Input:
- Output:
```

#### inetsoft 知识与 Prompt 的关联方式

- **命名关联**：  
  - `knowledge/inetsoft/modules/dashboard.md`  
  - 对应 Prompt 放在 `prompts/feature-analysis/inetsoft/dashboard_feature_analysis.md`
- **双向链接**：  
  - 在知识文档底部列出相关 Prompt 链接  
  - 在 Prompt 顶部「参考知识」部分列出对应的 `knowledge/inetsoft/...` 链接
