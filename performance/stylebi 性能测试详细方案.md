# StyleBI 性能测试详细方案

> 版本：1.0  
> 日期：2026-03-19  
> 适用版本：StyleBI Enterprise（含 Community 子模块）

---

## 目录

1. [测试目标与范围](#1-测试目标与范围)
2. [测试环境](#2-测试环境)
3. [测试工具选型](#3-测试工具选型)
4. [测试数据准备](#4-测试数据准备)
5. [测试模块与用例](#5-测试模块与用例)
   - 5.1 [查询引擎](#51-查询引擎)
   - 5.2 [物化视图（MV）](#52-物化视图mv)
   - 5.3 [图表与报表渲染](#53-图表与报表渲染)
   - 5.4 [Viewsheet 仪表盘](#54-viewsheet-仪表盘)
   - 5.5 [WebSocket / STOMP 实时通信](#55-websocket--stomp-实时通信)
   - 5.6 [Ignite 分布式集群](#56-ignite-分布式集群)
   - 5.7 [REST API 层](#57-rest-api-层)
   - 5.8 [多租户隔离](#58-多租户隔离)
   - 5.9 [数据连接器](#59-数据连接器)
   - 5.10 [安全与认证](#510-安全与认证)
   - 5.11 [存储层](#511-存储层)
   - 5.12 [前端 Angular 应用](#512-前端-angular-应用)
6. [监控指标体系](#6-监控指标体系)
7. [验收标准汇总](#7-验收标准汇总)
8. [测试执行流程](#8-测试执行流程)
9. [风险与注意事项](#9-风险与注意事项)

---

## 1. 测试目标与范围

### 1.1 测试目标

| 目标类型 | 说明 |
|----------|------|
| **性能基线建立** | 确定各核心模块在标准负载下的响应时间、吞吐量基准值 |
| **容量上限探测** | 识别系统在什么负载量级下开始出现性能拐点或错误 |
| **瓶颈定位** | 确认 CPU、内存、I/O、网络中哪个是首要瓶颈 |
| **集群稳定性验证** | 验证 3 节点 Ignite 集群在高并发下的亲和路由正确性和故障转移能力 |
| **回归保护** | 为后续版本迭代提供可对比的性能基准，防止性能退化 |

### 1.2 测试范围

**纳入范围：**

- 核心 BI 引擎：查询引擎（`uql/`）、物化视图（`mv/`）、图表渲染（`graph/`）、报表引擎（`report/`）
- Viewsheet 运行时：仪表盘加载、组件联动、实时推送（`web/viewsheet/`）
- 分布式集群：Ignite 亲和路由、缓存、故障转移（`sree/internal/cluster/`）
- REST API：Portal、Composer、EM 各端点（`web/` 各 controller）
- 数据连接器：JDBC（MySQL、PostgreSQL、Snowflake）、MongoDB、Elasticsearch、REST
- 安全认证：登录并发、权限检查、LDAP/SSO
- 前端应用：首屏加载、大数据表格、内存泄漏
- 多租户：多组织并发、`OrganizationContextHolder` 上下文开销

**不纳入范围：**

- 第三方 SaaS 数据源（Google Analytics GA4、Salesforce）的外部 API 性能
- 单元级别的算法微基准（使用 JMH 单独覆盖）
- UI 自动化功能回归测试

---

## 2. 测试环境

### 2.1 环境规格

| 环境级别 | 用途 | 规格 |
|----------|------|------|
| **最小环境** | 功能验证、冒烟测试 | 单节点，4 CPU / 8GB RAM，单机 PostgreSQL |
| **标准环境** | 性能基线、模块测试 | 2 Server 节点 × 8 CPU / 16GB RAM，1 Scheduler 节点，PostgreSQL 主从 |
| **生产级环境** | 容量测试、集群测试 | 3 Server 节点 × 8 CPU / 32GB RAM，1 Scheduler 节点，MinIO + MongoDB |

### 2.2 基于现有 Docker Compose 的集群环境

项目已在 `docker/src/test/sessions/docker-compose.yaml` 中提供了完整的 3 节点集群配置，包含：

- `server1` / `server2` / `server3`：各分配 4GB 内存（JVM `-Xms3g -Xmx3g`），调试端口 5005/5006/5007
- `proxy`：HAProxy 2.9 负载均衡，监听 80 端口，管理界面 9000 端口
- `mongodb`：MongoDB 7.0 作为 KV 存储与审计存储
- `postgres`：PostgreSQL 17 作为业务数据库
- `storage`：初始化容器，负责首次存储配置
- Ignite 集群发现：Multicast 模式（`224.2.2.3:54327`）

**在此基础上需额外添加：**

- Prometheus（抓取各节点 `/actuator/prometheus` 端点，由 `inetsoft-integration-prometheus` 模块提供）
- Grafana（实时监控仪表盘）
- 压测执行容器（k6 或独立压测机）

### 2.3 网络拓扑

```
压测客户端
    │
    ▼
HAProxy :80  ←→  HAProxy Admin :9000
    │
    ├── server1 :8080 (debug :5005)
    ├── server2 :8080 (debug :5006)
    └── server3 :8080 (debug :5007)
         │
         ├── MongoDB :27017  (KV + Audit)
         ├── PostgreSQL :5432 (业务数据)
         └── MinIO / 共享文件系统 (Blob Storage)

Prometheus :9090 ←── scrape ── server1/2/3 :8081/actuator/prometheus
Grafana :3000    ←── query  ── Prometheus
```

---

## 3. 测试工具选型

| 工具 | 版本 | 用途 | 备注 |
|------|------|------|------|
| **k6** | 0.50+ | HTTP/WebSocket 压测主力，脚本化场景，CI 集成友好 | 推荐首选 |
| **Apache JMeter** | 5.6+ | 复杂场景录制、GUI 调试、传统团队使用 | 备选 |
| **Gatling** | 3.x | Scala DSL 高并发场景，HTML 报告精美 | 备选 |
| **Locust** | 2.x | Python 脚本，已有 `/api/public/login` + `/api/public/viewsheets/open` 使用经验 | 已有基础可扩展 |
| **Playwright** | 1.43+ | 浏览器级端到端性能测试，测量真实加载时间 | 前端测试 |
| **Lighthouse CI** | 12+ | 前端 FCP/LCP/TTI 自动化检测 | 前端测试 |
| **async-profiler** | 3.x | JVM 火焰图，识别 CPU/内存热点 | JVM 剖析 |
| **JProfiler** | 14+ | 堆分析、线程分析、Ignite off-heap 监控 | JVM 剖析 |
| **Prometheus + Grafana** | 最新稳定版 | 实时指标采集与可视化，已有 `inetsoft-integration-prometheus` 模块支持 | 监控 |
| **Chrome DevTools** | 内置 | 前端内存泄漏检测、帧率分析 | 前端剖析 |

---

## 4. 测试数据准备

### 4.1 数据库测试数据集

在项目已有 `docker/src/test/sessions/orders.sql` 基础上，扩展为三个量级：

| 数据集 | 行数 | 用途 |
|--------|------|------|
| `orders_small` | 1,000 行 | 热身、功能验证 |
| `orders_medium` | 100,000 行 | 标准性能基线 |
| `orders_large` | 1,000,000 行 | 大数据量压测、MV 测试 |
| `orders_xl` | 10,000,000 行 | 极限容量测试（按需） |

字段设计需覆盖：数值字段（用于聚合）、文本字段（用于分组/筛选）、日期字段（用于时间维度分析）、枚举字段（用于下钻）。

### 4.2 Viewsheet 资产准备

测试前需在系统中预创建以下仪表盘（通过 Composer 设计或导入）：

| 资产名称 | 组件数量 | 数据量 | 用途 |
|----------|----------|--------|------|
| `Dashboard_Simple` | 5 个组件 | orders_small | 基线测试 |
| `Dashboard_Medium` | 15 个组件 | orders_medium | 标准压测 |
| `Dashboard_Complex` | 30 个组件（含图表、表格、筛选器、KPI卡片） | orders_large | 复杂场景压测 |
| `Dashboard_MV` | 10 个组件 | orders_large（有 MV） | MV 加速比对比 |
| `Report_Large` | 分页报表 | orders_large | 报表导出测试 |

### 4.3 多租户测试数据

- 预创建 10 / 50 / 100 个组织（`orgId`）
- 每个组织分配独立的 Viewsheet 资产和用户
- 各组织用户数量：10 人/组织（共 100~1000 用户）

---

## 5. 测试模块与用例

---

### 5.1 查询引擎

**对应代码**：`community/core/src/main/java/inetsoft/uql/`（`XEngine`、`XHandler`、`TabularExecutor`、`DataSourceRegistry`）

#### 测试用例 QE-01：JDBC 查询基准测试

| 项目 | 内容 |
|------|------|
| **目标** | 建立各主流 JDBC 数据库在不同数据量下的查询响应时间基线 |
| **场景** | 简单查询（SELECT + WHERE）、聚合查询（GROUP BY + COUNT/SUM）、多表 JOIN |
| **数据量** | 1K / 10K / 100K / 1M 行 |
| **并发用户** | 1 / 10 / 25 / 50 / 100 |
| **持续时间** | 每组场景 5 分钟稳态 |
| **覆盖数据库** | MySQL、PostgreSQL、Oracle、SQL Server、Snowflake |
| **验收标准** | 1K行 P95<500ms；100K行 P95<3s；1M行 P95<15s；错误率<1% |

#### 测试用例 QE-02：非 JDBC 连接器查询测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证 MongoDB、Elasticsearch、REST 连接器在并发场景下的查询性能 |
| **场景** | MongoDB 聚合管道、Elasticsearch 全文搜索、REST 接口分页拉取 |
| **并发用户** | 10 / 25 / 50 |
| **持续时间** | 每组 5 分钟 |
| **验收标准** | P95 < 5s；错误率 < 1% |

#### 测试用例 QE-03：连接池压力测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证连接池耗尽时的排队等待行为和超时处理 |
| **场景** | 并发用户数超过连接池上限（默认 20），持续施压 |
| **关注点** | 连接等待时间、连接泄漏检测、超时后是否正确报错 |
| **验收标准** | 连接等待 P95 < 5s；无连接泄漏；超时后返回明确错误信息 |

#### 测试用例 QE-04：并发查询资源竞争测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证多用户同时发起不同查询时的资源调度能力 |
| **场景** | 50 用户同时执行不同 SQL（轻量/重量混合），持续 10 分钟 |
| **关注点** | CPU 峰值、JVM 堆内存、线程池队列深度、GC 停顿时间 |
| **验收标准** | CPU < 80%；GC 停顿 P99 < 200ms；无 OOM |

---

### 5.2 物化视图（MV）

**对应代码**：`community/core/src/main/java/inetsoft/mv/`（`MVManager`、`MVExecutor`、`MVCreator`、`MVIncremental`、`MVAnalyzer`、`LocalMVExecutor`）

#### 测试用例 MV-01：MV 构建性能测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量不同数据量下 MV 初始构建（full build）的耗时 |
| **场景** | 基于 orders_medium（100K）、orders_large（1M）分别构建 MV |
| **并发** | 单线程构建（串行）；5 个 MV 并发构建 |
| **关注点** | 构建耗时、构建期间对在线查询的影响（性能干扰度） |
| **验收标准** | 100K 行 MV 构建 < 2 分钟；1M 行 < 15 分钟；构建期间在线查询响应时间劣化 < 50% |

#### 测试用例 MV-02：MV 查询加速比对比测试

| 项目 | 内容 |
|------|------|
| **目标** | 量化 MV 命中时的查询加速效果 |
| **场景** | 相同查询分别在「无 MV」和「MV 命中」两种状态下执行，各 50 并发，各 5 分钟 |
| **关注点** | 平均响应时间比值（加速倍率）、MV 命中率 |
| **验收标准** | MV 命中后查询速度提升 ≥ 5 倍；MV 命中率 ≥ 90%；MV 命中时 P95 < 500ms |

#### 测试用例 MV-03：MV 增量刷新测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证增量数据更新时 MV 局部刷新的性能 |
| **场景** | 向源数据表插入 1 万行新数据，触发 MV 增量刷新（`MVIncremental`），同时保持 30 并发查询 |
| **关注点** | 增量刷新耗时、刷新期间查询的数据一致性、在线查询响应时间抖动 |
| **验收标准** | 增量刷新（1万行）< 60 秒；刷新期间查询无数据错误；响应时间抖动 < 2 倍基线 |

#### 测试用例 MV-04：MV 并发访问测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证高并发下多用户同时命中同一 MV 的性能 |
| **场景** | 100 并发用户同时访问同一个 MV 支持的仪表盘，持续 5 分钟 |
| **关注点** | 锁竞争情况、`MVDispatcher` 的分发效率、`XMapTaskPool` 任务队列深度 |
| **验收标准** | P95 < 500ms；P99 < 1s；错误率 < 0.5% |

---

### 5.3 图表与报表渲染

**对应代码**：`community/core/src/main/java/inetsoft/graph/`（`VGraph`、`GGraph`、`Plotter`、各 `*VO` 视觉对象）；`community/core/src/main/java/inetsoft/report/`

#### 测试用例 GR-01：大数据量图表服务端渲染测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量图表引擎在大数据点下的服务端渲染耗时 |
| **场景** | 折线图（1万/5万/10万数据点）、散点图（5万点）、地理图（全国省份 + 数值）、树形图 |
| **并发** | 1 / 10 / 30 并发渲染请求 |
| **关注点** | 渲染时间、CPU 占用率、内存峰值、渲染线程池饱和情况 |
| **验收标准** | 1万点 P95 < 2s；5万点 P95 < 5s；10万点 P95 < 10s；30并发下无 OOM |

#### 测试用例 GR-02：报表导出性能测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量大型报表生成与导出的耗时 |
| **场景** | PDF 导出（100页/500页/1000页）；Excel 导出（1万行/10万行）；CSV 导出（100万行） |
| **并发** | 1 / 5 / 20 并发导出请求 |
| **关注点** | 导出耗时、内存峰值、导出队列等待时间（`VSExportService`） |
| **验收标准** | 100页 PDF < 30s；10万行 Excel < 60s；100万行 CSV < 120s；20并发无 OOM |

#### 测试用例 GR-03：并发渲染资源竞争测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证高并发渲染请求下的线程安全与资源管理 |
| **场景** | 50 用户同时请求不同类型图表渲染，持续 10 分钟 |
| **关注点** | CPU 饱和点、堆内存增长趋势、Full GC 频率 |
| **验收标准** | CPU 峰值 < 85%；无 Full GC 停顿 > 1s；10 分钟内内存无持续增长趋势 |

---

### 5.4 Viewsheet 仪表盘

**对应代码**：`community/core/src/main/java/inetsoft/web/viewsheet/`（`VSLifecycleService`、`RuntimeViewsheetManager`、`CommandDispatcher`、`VSSelectionService`、`VSOutputService`）

#### 测试用例 VS-01：仪表盘冷加载端到端测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量不同复杂度仪表盘的端到端首次加载时间 |
| **场景** | 简单（5组件）/ 中等（15组件）/ 复杂（30组件）仪表盘，清除缓存后冷加载 |
| **并发用户** | 1 / 10 / 50 / 100 / 200 |
| **测量范围** | 从用户点击仪表盘链接到所有组件数据渲染完成（含 WebSocket 握手、数据推送） |
| **验收标准** | 简单 P95 < 2s；中等 P95 < 4s；复杂 P95 < 8s；200并发下错误率 < 1% |

#### 测试用例 VS-02：筛选器联动响应测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量筛选器变更触发级联组件更新的端到端响应时间 |
| **场景** | 下拉框筛选器变更触发 10 个关联组件（图表 + 表格 + KPI）同步刷新 |
| **并发用户** | 50 |
| **关注点** | `VSSelectionService.applySelection` 执行时间、`CommandDispatcher` 广播延迟 |
| **验收标准** | P95 < 1.5s；P99 < 3s |

#### 测试用例 VS-03：仪表盘并发用户压测

| 项目 | 内容 |
|------|------|
| **目标** | 确定系统能稳定支持的最大仪表盘并发用户数 |
| **场景** | 逐步增加并发用户（50→100→200→300→500），每个用户保持一个活跃 Viewsheet，持续操作 |
| **关注点** | `RuntimeViewsheetManager` 中活跃 RuntimeViewsheet 数量、Ignite off-heap 增长、GC 频率 |
| **验收标准** | 找到 P95 响应时间开始超过 10s 的临界用户数；确认该阈值下无 OOM |

#### 测试用例 VS-04：Composer 设计器操作性能测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量 Viewsheet Composer 在设计复杂仪表盘时的后端 API 响应性能 |
| **场景** | 模拟设计过程：添加组件、修改绑定、保存仪表盘（各 API 顺序调用），30 并发设计用户 |
| **关注点** | `AutoSaveService` 的自动保存频率与延迟、大型 Viewsheet 序列化时间 |
| **验收标准** | 保存操作 P95 < 3s；30 并发下错误率 < 1% |

---

### 5.5 WebSocket / STOMP 实时通信

**对应代码**：`community/web/projects/shared/stomp/`（`StompClientService`、`StompClientConnection`）；后端 `WebSocketConfig.java`、`StompLoggingInterceptor.java`、`web/messaging/`

#### 测试用例 WS-01：WebSocket 大规模并发连接测试

| 项目 | 内容 |
|------|------|
| **目标** | 测试服务器在大量并发 WebSocket 连接下的稳定性 |
| **场景** | 逐步建立 100 / 200 / 500 / 1000 个并发 WebSocket（STOMP）连接，每连接保持 60 秒 |
| **关注点** | 连接建立时间、服务器内存增长（每连接内存开销）、连接建立成功率 |
| **验收标准** | 1000 连接建立 P95 < 1s；每连接服务端内存开销 < 2MB；连接成功率 > 99% |

#### 测试用例 WS-02：消息推送吞吐量测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量高频数据更新下 STOMP 消息推送的吞吐量与延迟 |
| **场景** | 500 个已连接客户端，后端每秒触发 Viewsheet 数据更新，测量消息从服务端发出到客户端收到的延迟 |
| **关注点** | 消息端到端延迟（`CommandDispatcher` 广播时间）、消息丢失率 |
| **验收标准** | 消息延迟 P95 < 500ms；P99 < 1s；消息丢失率 < 0.1% |

#### 测试用例 WS-03：断线重连恢复测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证网络中断后客户端重连和状态恢复的速度 |
| **场景** | 200 并发连接中随机断开 20% 连接，模拟网络抖动，观察 `StompClientConnection` 重连逻辑 |
| **关注点** | 重连成功率、重连耗时、重连后 Viewsheet 状态是否正确恢复 |
| **验收标准** | 重连成功率 > 98%；重连后状态恢复 P95 < 5s |

---

### 5.6 Ignite 分布式集群

**对应代码**：`inetsoft.sree.internal.cluster`（`Cluster`、`IgniteCluster`）；`@ClusterProxy` / `@ClusterProxyMethod` 注解体系；`IgniteSessionRepository`（`web/session/`）；集群配置参考 `claude/cluster.md`

#### 测试用例 CL-01：Ignite 分布式缓存读写吞吐测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量 Ignite 分布式缓存在高并发读写下的吞吐量 |
| **场景** | 纯读（80%）+ 纯写（20%）混合，50 并发，持续 10 分钟；覆盖 Partitioned Cache 和 Replicated Cache |
| **关注点** | 缓存 IOPS、读写延迟、`TotalAllocatedPages`、`OffHeapAllocatedSize`（通过 JMX 采集） |
| **验收标准** | 读 P95 < 50ms；写 P95 < 100ms；off-heap 增长趋势平稳 |

#### 测试用例 CL-02：@ClusterProxy 亲和路由延迟测试

| 项目 | 内容 |
|------|------|
| **目标** | 量化 `@ClusterProxyMethod` 跨节点亲和路由引入的额外延迟 |
| **场景** | 在 3 节点集群中，打开 Viewsheet 后故意让后续操作路由到非本地节点（远程 affinityCall），与本地调用对比 |
| **测量方法** | 对比直连各节点（绕过 HAProxy）与通过 HAProxy 的响应时间差异 |
| **关注点** | 序列化/反序列化开销、网络往返时间、`AffinityCallable` 执行开销 |
| **验收标准** | 跨节点路由额外延迟 P95 < 200ms |

#### 测试用例 CL-03：节点故障转移测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证集群节点宕机后服务的自动恢复能力 |
| **场景** | 200 并发用户正常使用时，通过 `docker compose stop server2` 模拟节点宕机，观察 HAProxy 切流和 Ignite 数据重均衡过程 |
| **关注点** | 请求失败窗口时长（RTO）、HAProxy 健康检查切换时间（health check 间隔 20s）、Session 数据是否从 Replicated Cache 正确恢复 |
| **验收标准** | 故障切换后请求失败时间 < 30s；Session 不丢失（用户无需重新登录）；节点恢复后流量自动回归 |

#### 测试用例 CL-04：集群 Off-Heap 内存压力测试

| 项目 | 内容 |
|------|------|
| **目标** | 量化不同访问模式对 Ignite off-heap 内存的影响（基于已有 Locust 压测经验） |
| **场景 A** | 高并发打开不同 Viewsheet（对应 `viewsheets/open`），持续 30 分钟，模拟「大量小对象写入」 |
| **场景 B** | 反复更新同一批仪表盘资产（大 JSON 配置），模拟「大对象高频更新」 |
| **场景 C** | 并发触发复杂查询（多索引、GROUP BY、ORDER BY），模拟「查询型 off-heap 压力」 |
| **监控指标** | `DataRegionMetrics.TotalAllocatedPages`、`OffHeapAllocatedSize`、`PagesFillFactor`（JMX）；各 Cache 的 `OffHeapEntriesCount` |
| **验收标准** | 30 分钟稳态运行后 off-heap 无持续线性增长（斜率趋近 0）；单节点 off-heap 上限 < 配置值的 80% |

#### 测试用例 CL-05：分布式 Session 压力测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证 `IgniteSessionRepository`（Replicated Cache）在大量活跃 Session 下的性能 |
| **场景** | 500 用户同时登录并保持活跃 Session，每隔 10 秒发送心跳请求（`SsoHeartbeatController`），持续 30 分钟 |
| **关注点** | Session 读写延迟、Replicated Cache 同步广播开销、节点间网络流量 |
| **验收标准** | Session 读 P95 < 20ms；500 Session 时节点间同步流量 < 100MB/min |

#### 测试用例 CL-06：调度节点（Scheduler Node）任务并发测试

| 项目 | 内容 |
|------|------|
| **目标** | 测试调度节点在高并发任务下的处理能力 |
| **场景** | 通过 API 批量触发 50 个调度任务立即执行（报表生成 + 导出），观察任务队列深度和执行延迟 |
| **关注点** | `XJobPool` 任务队列深度、任务等待时间、Scheduler 节点 CPU/内存占用、`ClusterFileTransfer` 文件传输效率 |
| **验收标准** | 50 并发任务全部在 10 分钟内完成；无任务丢失；Scheduler 节点 CPU < 90% |

---

### 5.7 REST API 层

**对应代码**：`community/core/src/main/java/inetsoft/web/` 各 controller（`portal/`、`composer/`、`binding/`、`adhoc/`、`admin/`、`vswizard/`）

#### 测试用例 API-01：Portal API 并发基准测试

| 项目 | 内容 |
|------|------|
| **目标** | 建立 Portal 核心 API 的并发响应时间基线 |
| **覆盖端点** | 仪表盘列表、资产树查询、用户信息、全局参数获取等高频端点 |
| **场景** | 500 并发用户随机请求上述端点组合，持续 10 分钟 |
| **验收标准** | TPS > 1000；P95 < 500ms；P99 < 1s；错误率 < 0.5% |

#### 测试用例 API-02：Composer API 大 Payload 测试

| 项目 | 内容 |
|------|------|
| **目标** | 测试大型 Viewsheet 定义的保存与加载性能 |
| **场景** | 保存含 50 个组件的复杂 Viewsheet（估计 JSON 大小 500KB~2MB），30 并发，持续 5 分钟 |
| **关注点** | `AutoSaveService` 序列化耗时、BlobStorage 写入延迟、请求超时风险 |
| **验收标准** | 保存 P95 < 5s；加载 P95 < 3s；无 413 / 504 错误 |

#### 测试用例 API-03：Ad-hoc 查询 API 并发测试

| 项目 | 内容 |
|------|------|
| **目标** | 测试即席查询端点在高并发下的响应能力 |
| **场景** | 100 并发用户提交不同即席查询（`adhoc/` controller），持续 10 分钟 |
| **验收标准** | P95 < 5s；错误率 < 1%；服务端线程池无持续饱和 |

#### 测试用例 API-04：EM 管理 API 压测

| 项目 | 内容 |
|------|------|
| **目标** | 验证企业管理界面 API 在批量操作下的响应性能 |
| **场景** | 批量查询用户列表（10000+ 用户）、批量权限变更（100 个角色）、监控数据实时刷新（每 5 秒轮询） |
| **验收标准** | 万级用户列表加载 P95 < 3s；权限批量变更 P95 < 5s；监控轮询 P95 < 1s |

---

### 5.8 多租户隔离

**对应代码**：`enterprise/`；`inetsoft.sree.security.OrganizationContextHolder`、`OrganizationManager`、`OrganizationCache`；参考 `claude/multitenant.md`

#### 测试用例 MT-01：多组织并发访问测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证多租户启用时，多组织并发访问下的性能与数据隔离正确性 |
| **场景** | 10 / 50 / 100 个组织各 10 名用户同时活跃，每用户打开各自组织的仪表盘 |
| **关注点** | `orgId` 前缀缓存键的查找效率、组织间数据不串扰（正确性验证）、总体响应时间与单租户的差距 |
| **验收标准** | 100 组织并发时响应时间相比单租户劣化 < 30%；无跨组织数据泄露（正确性断言） |

#### 测试用例 MT-02：OrganizationContextHolder 上下文开销测试

| 项目 | 内容 |
|------|------|
| **目标** | 量化跨线程/跨节点传递 `orgId` 的额外开销 |
| **场景** | 对比「单租户（host-org）」与「100 个租户并发」下同一 API 的响应时间差异 |
| **关注点** | `OrganizationContextHolder` 在线程池调度时的传递成本、Ignite 分布式调用时的上下文序列化 |
| **验收标准** | 多租户上下文切换额外开销 P95 < 50ms |

#### 测试用例 MT-03：共享资产访问性能测试

| 项目 | 内容 |
|------|------|
| **目标** | 测试 `exposeDefaultOrgToAll=true` 时，非 host-org 访问 host-org 资产的性能 |
| **场景** | 50 个非默认组织用户并发访问 host-org 的共享仪表盘（触发临时组织切换） |
| **验收标准** | 共享资产访问 P95 < host-org 直接访问的 1.5 倍 |

---

### 5.9 数据连接器

**对应代码**：`community/connectors/`（JDBC、MongoDB、Elasticsearch、REST、OData 等）；`enterprise/connectors/`（Google BigQuery、Salesforce、SAP）

#### 测试用例 DC-01：JDBC 连接器对比测试

| 项目 | 内容 |
|------|------|
| **目标** | 横向对比各 JDBC 连接器（同等查询）的性能差异 |
| **覆盖** | MySQL、PostgreSQL、Oracle、SQL Server、Snowflake |
| **场景** | 相同 SQL（聚合查询，100K 行）在各数据库上分别执行，20 并发，5 分钟 |
| **验收标准** | 各连接器 P95 响应时间有基准记录；同等场景下无数据库特定崩溃或超时 |

#### 测试用例 DC-02：MongoDB 聚合管道性能测试

| 项目 | 内容 |
|------|------|
| **目标** | 测试 MongoDB 连接器在复杂聚合管道下的查询性能 |
| **场景** | 多阶段聚合（`$match` + `$group` + `$sort` + `$limit`），数据量 100 万文档，25 并发 |
| **验收标准** | P95 < 5s；无连接超时 |

#### 测试用例 DC-03：REST 连接器限速与重试测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证 REST 连接器在外部 API 限速（Rate Limit）时的重试策略性能影响 |
| **场景** | 模拟外部 REST API 返回 429，观察连接器的重试行为与对上层查询响应时间的影响 |
| **验收标准** | 触发限速时有正确重试；重试期间用户侧错误率 < 5%；重试后最终成功率 > 95% |

#### 测试用例 DC-04：连接器并发连接池测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证各连接器的连接池在并发请求超过池容量时的行为 |
| **场景** | 并发请求数为连接池上限的 2 倍，持续 5 分钟 |
| **关注点** | 连接等待时间、连接泄漏检测、超出等待时间后的错误处理 |
| **验收标准** | 等待时间 P95 < 5s；无连接泄漏；超时后返回明确错误信息而非挂起 |

---

### 5.10 安全与认证

**对应代码**：`community/core/src/main/java/inetsoft/sree/security/`（`SecurityEngine`、`AuthenticationProvider`、`AuthorizationProvider`、`LdapAuthenticationProvider`、`PermissionChecker`）；`community/core/src/main/java/inetsoft/web/security/`

#### 测试用例 SA-01：登录并发压测

| 项目 | 内容 |
|------|------|
| **目标** | 测试系统在高并发登录场景下的认证吞吐量 |
| **场景** | 500 用户同时发起登录，持续 5 分钟 |
| **覆盖认证方式** | 内置数据库认证（`FileAuthenticationProvider`）、LDAP 认证（`LdapAuthenticationProvider`） |
| **关注点** | 认证吞吐量（TPS）、`LdapAuthenticationCache` 命中率、LDAP 连接池（`ContextPool`）压力 |
| **验收标准** | 内置认证 P95 < 500ms；LDAP 认证 P95 < 1s；500 并发下无登录挂起 |

#### 测试用例 SA-02：权限检查性能测试

| 项目 | 内容 |
|------|------|
| **目标** | 量化高频 API 调用中 `PermissionChecker` / `AuthorizationProvider` 的开销 |
| **场景** | 200 并发用户频繁访问需要权限校验的资源，持续 10 分钟 |
| **关注点** | 权限缓存命中率（`CachableProvider`）、单次权限检查耗时、权限缓存失效时的性能抖动 |
| **验收标准** | 权限检查缓存命中时 P95 < 5ms；缓存未命中时 P95 < 100ms |

#### 测试用例 SA-03：Session 生命周期压测

| 项目 | 内容 |
|------|------|
| **目标** | 测试 `SessionLicenseManager` 在大量并发 Session 下的管理性能 |
| **场景** | 1000 用户同时在线，随机进行登录/登出操作，持续 30 分钟 |
| **关注点** | Session 创建/销毁速度、`ViewerSessionService` 的 Session 跟踪开销、许可证并发 Session 计数准确性 |
| **验收标准** | Session 创建 P95 < 200ms；Session 计数无错误；无 `SessionsExceededException` 误触发 |

---

### 5.11 存储层

**对应代码**：`community/core/src/main/java/inetsoft/storage/`（`BlobEngine`、`BlobStorage`）；`community/utils/inetsoft-storage-mapdb/`；`integration/inetsoft-integration-mongo/`

#### 测试用例 ST-01：BlobStorage 读写吞吐测试

| 项目 | 内容 |
|------|------|
| **目标** | 测量 BlobStorage 在不同存储后端（文件系统、MongoDB）下的读写性能 |
| **场景** | 并发读写不同大小的资产：小文件（10KB）、中文件（1MB）、大文件（50MB） |
| **并发** | 20 / 50 并发读写 |
| **验收标准** | 小文件读 P95 < 50ms；写 P95 < 100ms；大文件（50MB）读 P95 < 5s |

#### 测试用例 ST-02：并发文件操作锁竞争测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证多用户并发读写同一资产时的锁机制正确性与性能 |
| **场景** | 50 用户同时读取同一仪表盘定义；20 用户同时更新同一仪表盘定义 |
| **关注点** | 锁等待时间、写操作串行化是否正确、读写并发时的数据一致性 |
| **验收标准** | 无数据损坏；写锁等待 P95 < 1s；读写锁分离验证 |

#### 测试用例 ST-03：MV 块文件存储性能测试

| 项目 | 内容 |
|------|------|
| **目标** | 测试 MV 专用块文件存储（`XBlockSystem`、`BlockFileStorage`）的读写性能 |
| **场景** | 同时读取多个 MV 的数据块，模拟高并发 MV 查询时的 I/O 模式 |
| **验收标准** | 块文件随机读 P95 < 100ms；顺序扫描吞吐 > 500MB/s（本地 SSD 环境） |

---

### 5.12 前端 Angular 应用

**对应代码**：`community/web/projects/portal/`、`community/web/projects/em/`、`community/web/projects/shared/`

#### 测试用例 FE-01：首屏加载性能测试（Portal）

| 项目 | 内容 |
|------|------|
| **目标** | 测量 Portal 首屏关键性能指标 |
| **工具** | Lighthouse CI、Chrome DevTools Performance 面板 |
| **测量指标** | FCP、LCP、TTI、JS Bundle 大小（gzip） |
| **场景** | 清除浏览器缓存（冷加载）和有缓存（热加载）两种情况 |
| **验收标准** | FCP < 1.5s；LCP < 3s；TTI < 4s；主 Bundle < 2MB（gzip） |

#### 测试用例 FE-02：大数据表格渲染帧率测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证虚拟滚动下大数据量表格的渲染流畅度 |
| **工具** | Chrome DevTools Performance 面板 |
| **场景** | 仪表盘中展示 1 万行 / 10 万行数据的表格，进行快速滚动操作 |
| **验收标准** | 滚动期间 FPS > 30；无明显卡顿（单帧耗时 < 50ms） |

#### 测试用例 FE-03：前端内存泄漏检测

| 项目 | 内容 |
|------|------|
| **目标** | 检测 Angular 组件在长时间使用后是否存在内存泄漏 |
| **工具** | Chrome DevTools Memory 面板（Heap Snapshot 对比） |
| **场景** | 循环执行「打开仪表盘 → 操作 → 关闭仪表盘」100 次 |
| **关注点** | RxJS 订阅未销毁、Angular 组件引用未释放、DOM 节点泄漏 |
| **验收标准** | 100 次循环后 JS 堆内存增长 < 50MB；无可观测的内存泄漏趋势 |

#### 测试用例 FE-04：EM 管理界面大列表渲染测试

| 项目 | 内容 |
|------|------|
| **目标** | 验证 EM 用户列表、权限列表在大数量下的渲染性能 |
| **场景** | 加载 10000+ 用户列表，进行翻页和搜索操作 |
| **验收标准** | 列表初始加载 < 3s；翻页响应 < 500ms；搜索过滤响应 < 1s |

---

## 6. 监控指标体系

### 6.1 JVM 指标（通过 Prometheus + `/actuator/prometheus`）

| 指标类别 | 具体指标 | 告警阈值 |
|----------|----------|----------|
| **GC 性能** | `jvm_gc_pause_seconds` | P99 > 500ms 告警 |
| **堆内存** | `jvm_memory_used_bytes{area="heap"}` | 使用率 > 85% 告警 |
| **非堆内存** | `jvm_memory_used_bytes{area="nonheap"}` | 持续增长趋势告警 |
| **线程** | `jvm_threads_states_threads{state="blocked"}` | Blocked 线程 > 20 告警 |

### 6.2 Spring Boot 应用指标

| 指标类别 | 具体指标 | 告警阈值 |
|----------|----------|----------|
| **HTTP 响应时间** | `http_server_requests_seconds`（按 uri、status 分组） | P95 超过模块阈值告警 |
| **HTTP 错误率** | 5xx 状态码占比 | > 1% 告警 |
| **连接池** | `hikaricp_connections_active`、`hikaricp_connections_pending` | Pending > 10 告警 |
| **线程池** | `executor_active_threads`、`executor_queued_tasks` | 队列深度 > 100 告警 |
| **MV 缓存命中率** | `cache_gets_total{result="miss"}` | 命中率 < 80% 告警 |

### 6.3 Ignite 集群指标（通过 JMX）

| 指标类别 | 具体指标 | 告警阈值 |
|----------|----------|----------|
| **Off-Heap 
| 