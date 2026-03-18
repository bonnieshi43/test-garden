---
doc_type: feature-test-doc
product: StyleBI
module: dashboard
feature_id: 70565
feature: Chart Shape SVG Support
pr_link: https://github.com/inetsoft-technology/stylebi/pull/2777
Assignee: Stephen Webster
last_updated: 2026-03-18
version: stylebi-1.1.0

---

# 1 Feature Summary

**核心目标**：在现有的 JPG/PNG/GIF 格式基础上，新增对 **SVG 矢量图形格式**的支持，使用户能够使用 SVG 文件作为图表数据点的自定义标记。

**用户价值**：SVG 格式具有可缩放、高清晰度的特点，相比位图格式在放大时保持清晰度，满足对图表可视化品质有较高要求的用户需求。

---

# 2 Test Focus

## P0 - Core Path

- SVG 文件上传、存储、加载、渲染全流程
- 图表中应用 SVG Shape 并正确显示
- 刷新后 SVG 持久化

## P1 - Functional Path

- 边界情况：空文件、无效文件、超大文件
- 异常输入：伪造 SVG（如重命名的 PNG）、含恶意脚本的 SVG
- 多对象交互：SVG 与位图混用、多数据点批量渲染
- UI 状态变化：图表过滤、钻取、刷选、排除、缩放、导出后 SVG 行为

## P2 - Extended Path（按需测试）

- 性能：复杂 SVG + 大量数据点
- 兼容性：跨浏览器渲染一致性
- 安全：SVG 脚本注入防护
- 本地化：上传错误提示多语言支持
- 文档：Shape 支持格式更新

---

# 3 Test Scenarios

| ID | Scenario | Steps | Expected | Result | Notes |
|---|---|---|---|---|---|
| **P0** |
| TC70565-1 | **SVG 文件基础上传和渲染** | 1. 打开 Dashboard → Point Chart → Edit Shape → Add Shape<br>2. 上传标准 SVG 文件（如 star.svg）<br>3. 验证上传成功，显示在 Shape 库<br>4. 应用该 Shape 到图表<br>5. 保存并刷新 Dashboard | ✅ 上传成功，无错误<br>✅ Shape 库显示预览<br>✅ 图表中正确渲染 SVG<br>✅ 刷新后仍正确显示 | 通过，但存在 Bug #74031 | 🔴 Bug #74031：upload some svg image, show empty |
| TC70565-2 | **SVG 与位图混用渲染一致性** | 1. 上传 SVG 和 PNG 文件<br>2. 在 Chart Editor 中设置 Shape Mapping：不同维度使用不同格式<br>3. 保存并刷新<br>4. 放大/缩小图表 | ✅ 两种格式均正确显示<br>✅ 放大时 SVG 清晰，PNG 像素化（符合预期）<br>✅ 无性能卡顿 | 通过，但存在 Bug #74078 | 🔴 Bug #74078：add and apply shape， background server pop up error |
| **P1** |
| TC70565-3 | **SVG 安全性 - 恶意脚本检测** | 1. 准备含 `<script>alert('XSS')</script>` 的 SVG 文件<br>2. 尝试上传 | ✅ 系统拒绝上传并提示安全警告<br>✅ 或自动清理脚本后上传<br>✅ 图表中仅显示图形，无脚本执行 | 失败（安全设计不支持脚本执行，但上传成功） | 🔴 Bug #74068：The SVG file contains malicious code that was able to be uploaded successfully.<br>🔴 测试分析：我们直接不执行 script 标记，但上传未拦截 |
| TC70565-4 | **SVG 大小极限 - 文件上传限制** | 1. 准备 100KB、5MB、20MB 的 SVG 文件<br>2. 依次尝试上传 | ✅ <限制文件上传成功<br>✅ >限制文件被拒绝并提示<br>✅ 系统资源占用正常 | 通过（无大小限制，20MB 可上传） | |
| TC70565-5 | **SVG 在图表导出中的表现** | 1. 应用 SVG Shape 到图表<br>2. 分别导出为 PDF、PNG、Excel<br>3. 验证导出文件 | ✅ PDF 中 SVG 正确渲染<br>✅ PNG 中栅格化清晰<br>✅ Excel 中图表正常 | 通过 | |
| TC70565-6 | **图表过滤/钻取后 SVG 动态刷新** | 1. 应用 SVG Shape 到图表<br>2. 执行过滤、钻取、刷选、排除、放大等操作 | ✅ 数据和 SVG 同步刷新<br>✅ 无闪烁或延迟<br>✅ 新数据点正确显示 SVG | 通过，但存在 Bug #74065、#74066 | 🔴 Bug #74065：do brush actions, svg shape color is not rightly<br>🔴 Bug #74066：do exclude actions, svg shape can't be exclude |
| TC70565-7 | **SVG 文件格式验证** | 1. 准备标准 SVG、重命名的 PNG、重命名的文本文件<br>2. 分别尝试上传 | ✅ 标准 SVG 成功<br>✅ 伪造文件被拒绝或渲染时报错 | 通过，但存在 Bug #74029 | 🔴 Bug #74029：when upload svg(empty/invalid), show broken image and pop up error on background server |
| **P2** |
| TC70565-8 | **复杂 SVG 渲染性能** | 1. 上传含复杂路径/滤镜的 SVG<br>2. 应用到含 1000+ 数据点的图表<br>3. 记录加载时间和交互响应 | ✅ 加载时间可接受（<2s）<br>✅ 交互流畅<br>✅ 内存/CPU 正常 | 通过 | |
| TC70565-9 | **浏览器兼容性 - SVG 渲染差异** | 1. 在 Chrome、Firefox、Safari、Edge 中打开同一 Dashboard<br>2. 对比 SVG 渲染效果 | ✅ 渲染结果一致或差异可接受<br>✅ 交互功能正常 | 通过，但存在默认尺寸问题 | 🔴 测试分析：default size of svg can't apply（不支持） |
| TC70565-10 | **SVG Shape 在全局 vs 组织级别隔离** | 1. Org-A 上传 SVG 到组织级别<br>2. Org-B 用户尝试访问<br>3. 系统管理员上传全局 SVG | ✅ Org-B 无法访问 Org-A 的 Shape<br>✅ 全局 Shape 所有组织可见 | 通过 | |
| TC70565-11 | **本地化 - 上传错误提示** | 1. 切换不同语言界面<br>2. 触发上传错误（如空文件） | ✅ 错误提示使用当前语言 | 通过，但存在 Bug #74154 | 🔴 Bug #74154：some prompts no localization |

---

# 4 Special Testing

## Security
- **SVG 脚本注入**：上传含 `<script>` 的 SVG，验证是否被拦截或清理。当前行为：上传成功但脚本不执行（Bug #74068）。需确认是否需要增加上传拦截。

## Performance
- **复杂 SVG + 大量数据点**：已验证通过。

## Compatibility
- **跨浏览器**：Chrome、Firefox、Safari、Edge 已验证通过，但 SVG 默认尺寸不支持。

## 本地化
- **上传错误提示**：需验证多语言环境（Bug #74154）。

## 文档/API
- **Shape 支持格式**：需更新官方文档（Documentation #74082）。

## 配置检查
- **文件大小限制**：当前无限制，建议评估是否增加配置项。

---

# 5 Regression Impact（回归影响）

| 模块 | 影响说明 |
|---|---|
| Chart | 核心受影响：渲染、交互、导出 |
| Dashboard | Shape 使用场景 |
| Export | PDF/PNG/Excel 导出 SVG 的兼容性 |
| Content Repository | SVG 文件存储 |
| Admin / Settings | Shape 管理、上传限制配置 |

---

# 6 Bug List

| Bug ID | Description | Status |
|---|---|---|
| Bug #74029 | when upload svg(empty/invalid), show broken image and pop up error on background server | Closed |
| Bug #74031 | upload some svg image, show empty | Closed |
| Bug #74065 | do brush actions, svg shape color is not rightly | Closed |
| Bug #74066 | do exclude actions, svg shape can't be exclude | Closed |
| Bug #74068 | The SVG file contains malicious code that was able to be uploaded successfully. | Rejected |
| Bug #74078 | add and apply shape， background server pop up error | Closed |
| Bug #74154 | some prompts no localization | Resolved |
| Bug #74156 | Some SVGs cannot be displayed fully. | Request Feedback |
| Bug #74194 | use svg shape, data tip view is wrong. | New |
| Bug #74195 | set svg shape, It cannot display that the refresh operation has been completed for quite a while. | New |
| Documentation #74082 | The type of "upload shape" needs to be updated. | New |