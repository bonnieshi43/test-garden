## prompts-library

用于管理和存储各种 Prompt，包括：
- **日常使用的 Prompt**：如写作、翻译、代码辅助、产品需求等
- **专项优化的 Prompt**：针对某一类任务不断迭代调优的版本
- **调试与实验用 Prompt**：用于测试不同提示策略、结构和参数的效果

### 仓库克隆方式

使用 `git clone` 将仓库克隆到本地：

```bash
git clone https://github.com/bonnieshi43/prompts-library.git
```

克隆完成后进入项目目录：

```bash
cd prompts-library
```

### 主要用途

- **统一管理 Prompt**：集中管理不同场景下使用的 Prompt，方便复用与分享  
- **Prompt 调试与测试**：记录不同版本 Prompt 的实验过程和效果对比  
- **知识沉淀**：把在 Prompt 设计、调试过程中得到的经验、案例和最佳实践固化到仓库中，方便后续查阅和迭代

---

### 推荐仓库结构（针对 bug / 功能分析与 inetsoft 知识）

**思路**：按「用途（bug 分析 / 功能分析）」+「对象（inetsoft 及模块）」来组织；Prompt 与知识分开存放，但路径和命名保持强关联。

#### 目录结构示例

```text
prompts-library/
  README.md

  prompts/
    bug-analysis/
      generic/                    # 通用 bug 分析 Prompt（与具体产品无关）
        bug_root_cause.md
        bug_reproduction_steps.md
      inetsoft/
        overview.md               # inetsoft 专用 bug 分析说明与入口
        ui_bugs.md
        backend_bugs.md
        performance_bugs.md
        data_issue_bugs.md

    feature-analysis/
      generic/
        requirement_clarify.md
        impact_analysis.md
        api_design_helper.md
      inetsoft/
        dashboard_feature_analysis.md
        data_modeling_feature_analysis.md
        permission_feature_analysis.md

  knowledge/
    inetsoft/
      product-overview.md         # 产品整体介绍
      architecture.md             # 架构/模块划分
      modules/
        dashboard.md
        data_modeling.md
        permissions.md
        reporting.md
      troubleshooting/
        common_issues.md          # 常见问题及解决方案
        performance_tuning.md
        deployment_notes.md

  experiments/
    bug-analysis/
      2026-02-inetsoft-bug-session-1.md   # 某次调试/实验记录
    feature-analysis/
      2026-02-new-dashboard-design.md
```

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
