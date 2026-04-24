# Java Unit Test Generation Prompt

> **All test code and comments must be written in English.**

---

## 执行顺序总览

每次生成测试，严格按以下顺序执行，不得跳步或乱序：

| 步骤 | 内容 | 参见 | 条件 |
|------|------|------|------|
| 1 | 意图 vs 实现分析，记录 suspects | 第 0 节 | 必做 |
| 2 | 建方法清单 + 标注 tier | 第 0.5 节 第一、二步 | 必做；无 private 逻辑时快速确认即可 |
| 3 | 文件拆分决策 | 第 0.5 节 第三步 | 仅当清单中 ≥2 种 tier 且每种有逻辑方法 ≥3 个 |
|   | ↳ 输出拆分方案表，等待用户确认，**不写任何代码** | | |
| 4 | 覆盖对应关系 + deferred 记录 | 第 0.5 节 第四步 | 必做 |
| 5 | 分类选策略 | 第 1 节 → 第 2 / 2B / 2C / 2D 节 | 必做 |
| 6 | 写测试 + 聚合 @ParameterizedTest + Risk 过滤 | 第 3、4 节 | 必做 |

---

## 0. 动笔前：意图 vs 实现分析

选择测试策略前，先回答四个问题，记录每条差距为 suspect：

```
1. 作者想实现什么？  → 读接口/抽象类契约、方法名、Javadoc
2. 代码实际做了什么？→ 读实现，不要相信方法名，相信代码
3. 两者有差距吗？    → 每个差距 = suspect = 必须有对应测试
4. 有哪些边界/遗漏？ → null、空集合、未 override 的父类 no-op、
                       集合类型不匹配（Set<A>.remove(B) 永不匹配）、
                       不同合法输入是否映射到同一内部 key / 标识、
                       catch 后吞异常但继续返回”成功形态”结果、
                       无 try-catch 的 dispatch loop → 单个 listener 抛异常截断后续通知、
                       switch/if-else 无 default → 未处理类型被静默丢弃（无异常无日志）、
                       n 个重载委托同一 private 方法 → 各重载传入的默认参数值是否正确、
                       boolean 标记 × 历史状态是否存在 的组合分支
```

仅当意图与实现存在不一致时，才将该差距写入测试类文件头；若无差距则不写。每条 suspect 对应一个 enabled 或 `@Disabled` 测试：

```java
/*
 * Intent vs implementation suspects
 *
 * [Suspect 1] setPermission(identity, null) → intent: remove entry
 *             actual: removePermission(IdentityID) not overridden → no-op in base class
 * [Suspect 2] authenticationChanged → intent: rewrite/strip grants for oldID
 *             actual: Set<PermissionIdentity>.remove(IdentityID) → equals() never matches
 */
```

`@Disabled` message 三段式：现象 + 根因（精确到行）+ 修复建议：
```java
@Disabled("Suspect N: <symptom> — <ClassName>:<line>; Fix: <one-liner>")
```

---

## 0.5 方法清单与测试文件规划

**执行步骤（按顺序，不得合并）：**

**第一步 — 建方法清单表**

列出类中 **所有** 方法（含 public / protected / private），填入下表：

```
| 方法签名（简写）        | 可见性    | 有逻辑？ | 测试入口                     |
|------------------------|-----------|----------|------------------------------|
| copyThemes(...)        | private   | ✓        | via public copyOrganization  |
| clearScopedProperties  | protected | ✓        | 直接调用（同包）              |
| addUser(User)          | public    | ✗ no-op  | 跳过                         |
```

判断规则：
- **✗ no-op** = 空方法体 / `return null` / `return new T[0]` / 仅 `return field` → 跳过，不写测试
- **✓ 有逻辑** = 含 if / switch / loop / 赋值 / 异常抛出 → 纳入测试

对所有 **✓ 有逻辑** 的 `private` 方法，调用链必须追到第一个 `public` 或 `protected` 入口并写入"测试入口"列。若调用链中有多个层级，只写最终公开入口（`via: publicFoo()`）。

**第二步 — 标注可测性**

对所有 ✓ 有逻辑的方法，在"测试入口"列追加以下三档标记之一：

- **`[unit]`** — 所有依赖均可通过构造函数 / 参数传入，或由 StubXxx 子类实现；纯 JUnit + Mockito，无需 mockStatic
- **`[mockStatic]`** — 依赖通过静态工厂获取（`SreeEnv.getProperties()` / `DataSpace.getDataSpace()` / `XxxManager.getManager()` 等），但无需 Spring 容器；可用 `Mockito.mockStatic` 拦截
- **`[integration]`** — 需要完整 Spring 上下文或无法被 mockStatic 覆盖的容器级单例（`@SreeHome` / `SecurityEngine.getSecurity()` 等）

同一测试文件只放同一 tier 的测试。

**第三步 — 文件拆分决策**

清单中同时出现 ≥2 种 tier 且每种有逻辑方法数 ≥3 时（见执行顺序总览步骤 3），**立即停止，不进入第 1 节写任何测试代码**。先输出拆分方案供用户选择，用户确认后再继续。

拆分优先级：
1. **首选按 infrastructure tier 拆**：每种 tier 一个文件，`@BeforeEach` / `@ExtendWith` setup 均匀，CI 可分层运行（`[unit]` 最快，`[mockStatic]` 次之，`[integration]` 最慢）
2. 若同一 tier 内有逻辑方法数仍 > 20，再按功能域（如：事件系统 / 实体复制 / 存储副作用）细分子文件

输出格式（只输出表格和说明，**不写任何 Java 代码**）：

```
| 文件名                  | 覆盖方法（简写）           | tier            | 估计测试数 | 备注            |
|------------------------|--------------------------|-----------------|------------|-----------------|
| XxxTest                | foo / bar                | 纯 Mockito      | ~N         | 现有文件扩充     |
| XxxStaticDepTest       | baz / qux                | mockStatic(Env) | ~N         | 新建            |
| XxxIntegrationTest     | full flow                | @SreeHome       | —          | deferred，不实现 |
```

表格后附一句推荐理由，然后**等待用户确认**，不得提前写代码。
若用户选择不拆分，在单一文件内以注释块隔离各 tier 的 setup 代码，并在文件头说明原因。

**第四步 — 建立覆盖对应关系**

对每一行 `✓ [unit]` 或 `✓ [mockStatic]` 的方法，后续写的决策树 / 场景表 / 状态转换表中必须有对应条目，测试方法头部注释标注触发路径（`via: publicFoo() → privateBar()`）。

对每一行 `✓ [integration]` 的方法，在测试文件头的 deferred 块中记录缺口：

```java
/*
 * Cases deferred — require integration context:
 *
 * [ClassName] privateBar() — called via publicFoo()
 *             → needs @SreeHome + DataSpace; NOT yet covered
 */
```

**完成标准**：表中每一行 `✓` 方法，要么有对应测试（或 `@Disabled` suspect），要么在 deferred 块中有记录。若两者都没有，视为遗漏，不得跳过。

---

## 1. 先判断被测类的类型

在动笔之前，先判断被测类属于哪种类型，选择对应的测试策略：

| 类型 | 典型特征 | 测试策略 |
|------|---------|---------|
| **数据模型 / 工具类** | 纯 POJO、无外部依赖、方法是 get/set/check/transform | → **决策树路径覆盖**（见第 2 节） |
| **行为编排 / 策略类** | 协调多个依赖、有业务流程、方法名是动词短语 | → **业务场景覆盖**（见第 2B 节） |
| **存储适配器 / Repository 类** | 封装存储后端、CRUD 方法语义、有 key 生成/解析逻辑、有生命周期管理 | → **存储契约 + 状态转换覆盖**（见第 2C 节） |
| **抽象 / 骨架类** | 大量 no-op 空 override 供子类实现、混有少量 concrete 方法、无法直接实例化 | → **跳过所有 no-op；仅对有真实逻辑的 concrete 方法选上述策略；见第 2D 节** |

多种策略可以在同一个测试类里共存：数据模型内部有复杂分支时用决策树，同一个类对外暴露的业务契约用场景，存储层的 CRUD 和 key 映射用存储契约。

**动笔前先做基础设施依赖扫描**：若第 0.5 节已完成，直接按已确认的文件方案写对应文件，同一文件只放同一 tier 的测试。

---

## 2. 数据模型/工具类：读源码，画决策树

读被测方法，提取分支节点，用字母标记，写在测试类文件头：

```java
/*
 * check() decision tree
 *  ├─ [A] type is invalid                   → false
 *  ├─ [B] grants.get(action) == null        → false
 *  ├─ [C] identity found by equals()        → true
 *  ├─ [D] found by equalsIgnoreCase() only  → true  (AD/LDAP fallback)
 *  └─ [E] not found by either               → false
 */
```

每个测试方法头部注释格式：`[路径 X]` + 触发条件 + 期望结果

```java
// [Path D] case-insensitive fallback → grants match regardless of case (AD/LDAP compat)
// Condition: exact equals() fails, equalsIgnoreCase() succeeds
@Test
void check_caseInsensitiveFallback_returnsTrue() { ... }
```

---

## 2B. 行为编排/策略类：提取业务场景

不要逐行追踪 if/else，而是站在调用方视角问以下四类问题，每个问题答案就是一个或一组场景：

```
1. 最基本的放行和拒绝是什么？
   → 满足最小授权条件  = allowed
   → 完全没有授权      = denied

2. 有哪些"绕过"路径？（特权身份、快捷通道）
   → 每条绕过路径单独一个场景

3. 授权可以通过哪些方式间接获得？（继承、委托、聚合）
   → 每条间接路径单独一个场景，包括链断裂时的 denied 场景

4. 多条件组合时逻辑是 AND 还是 OR？
   → 枚举关键组合：全满足 / 部分满足 / 全不满足
```

写成场景表（格式：前提 → 结果），然后每行对应一个或一组测试：

```
场景表模板：
  [基本放行]   最小授权条件成立                 → allowed
  [基本拒绝]   无任何授权                       → denied
  [绕过 #1]   特权身份 X                        → allowed（跳过所有检查）
  [间接 #1]   通过 A→B 委托链获得权限           → allowed
  [间接 #2]   委托链中 B 无权限（链断裂）        → denied
  [组合 AND]  条件 P 满足，条件 Q 不满足         → denied
  [组合 AND]  条件 P、Q 均满足                  → allowed
  [空输入]    关键参数为 null / empty            → denied 或 exception（明确哪个）
```

每个测试方法头部注释格式：`[场景]` + 前提 + 期望结果

```java
// [Scenario: indirect #1] user inherits READ via role chain A→B → allowed
// Setup: user has role A; role A inherits role B; role B has READ grant; recursive=true
@Test
void checkPermission_userGrantedViaRoleChain_returnsTrue() { ... }
```

---

## 2C. 存储适配器/Repository 类：覆盖存储契约

不要追踪业务决策逻辑，而是围绕五个维度验证存储行为：

```
1. CRUD round-trip    put(k,v) → get(k) == v
                      put(k,v1) → put(k,v2) → get(k) == v2   (overwrite)
                      put(k,v) → remove(k)  → get(k) == null

2. Key mapping        不同输入类型产生正确 key，list() 能将 key 正确解析回领域对象
                      同时验证不同合法输入不会意外映射到同一 key / 同一存储槽位

3. Bulk / scope       filter 只影响命中条目，不影响其他条目

4. Lifecycle          init 幂等（多次调用不重复初始化）
                      tearDown/close 幂等（storage 已为 null 时安全无抛）
                      若涉及 Future / 异步后端，补失败路径：异常、超时、中断后的行为语义

5. Event mutation     rename 事件 → 引用被重写
                      remove 事件 → 引用被清除

6. State carry-over   当前操作受历史状态影响时，覆盖“有旧状态 / 无旧状态” × 标记位组合
                      验证哪些字段继承旧值，哪些字段必须被本次输入覆盖
```

写成状态转换表（格式：前置状态 + 操作 → 期望后置状态），然后每行对应一个测试：

```
状态转换表模板：
  [Op: put→get]        空存储 + put(k,v)           → get(k) == v
  [Op: overwrite]      get(k)==v1 + put(k,v2)      → get(k) == v2
  [Op: remove]         get(k)==v  + remove(k)       → get(k) == null
  [Key: type-A]        输入类型 A                   → key 格式正确，list() 解析一致
  [Key: type-B]        输入类型 B（如 IdentityID）   → 使用正确序列化方式
  [Key: collision]     输入 A、B 均合法              → 不会写入同一 key / 不会互相覆盖
  [Bulk: scope-match]  scope=X 的条目               → 被批量操作影响
  [Bulk: scope-other]  scope=Y 的条目               → 不受影响
  [Lifecycle: init×2]  init() 已完成后再次调用       → 状态不变，无副作用
  [Lifecycle: close×2] close() 后再次调用            → 无异常
  [Failure: timeout]   底层写入超时 / 失败            → 返回值、持久化结果、线程状态符合契约
  [Event: rename]      存储含旧引用 + rename 事件    → 引用重写为新名
  [Event: remove]      存储含旧引用 + remove 事件    → 旧引用被清除
  [Carry: flag×history] 标记位变化 + 历史状态存在性   → 继承/覆盖规则正确
```

每个测试方法头部注释格式：`[维度: 操作→断言]` + 前置状态 + 期望后置状态

```java
// [Op: overwrite] second put on same key replaces first value
// Pre: get(k) == v1; Op: put(k, v2); Post: get(k) == v2
@Test
void put_sameKey_replacesExistingValue() { ... }
```

---

## 2D. 抽象/骨架类：实例化策略

**核心规则：只测"仅在抽象类中有实现"的 concrete 方法逻辑。** 被子类 override 的 no-op 桩方法 → 在对应子类的测试文件里测，不在这里写。

在测试类文件头用固定块列出需在子类补充的测试项（标注是否已覆盖）：

```java
/*
 * Cases deferred to subclass tests — do NOT add here:
 *
 * [ConcreteProviderTest] addUser/setUser/removeUser — CRUD round-trips
 *                        → covered by ConcreteProviderTest
 * [ConcreteProviderTest] copyOrganization full flow — requires @SreeHome + DataSpace
 *                        → NOT yet covered; needs integration test
 */
```

**第一步**：区分方法类型。方法体为空 / `return null` / `return new T[0]` → no-op，跳过，不写测试。方法体有 if/switch/loop/状态变更 → 按上述策略测试。

**第二步**：选实例化方式（按优先级）：
1. 代码库中已有具体子类（如 `FileAuthenticationProvider`）→ 复用，不新建
2. 无可复用子类 → 在测试类内创建最小 `static class StubXxx extends AbstractXxx`：只 override 编译必须的抽象方法（全返回 null/false/空数组），额外 override 被测 concrete 方法所调用的查询方法（如 `getUser`/`getGroup`/`getRole`），绝不 override 被测方法本身
3. 被测逻辑与抽象方法完全解耦 → 可改用 `Mockito.spy(new StubXxx())`

**`protected` 方法访问**：测试类与被测类同包时直接调用；不同包时在 StubXxx 里加 package-visible 包装方法暴露；两者都不行则通过可观察副作用间接触发。

---

## 3. `@ParameterizedTest` 聚合规则

- **同一路径节点 / 同一场景类别** + 只是参数不同 → 合并为一个 `@ParameterizedTest`
- `@MethodSource` 里每个 `Arguments.of(...)` 前加一行注释说明变体意图：

```java
private static Stream<Arguments> cases() {
    return Stream.of(
        // ✓ user granted directly
        Arguments.of(userPerm, READ, true),
        // ✓ granted via role (inheritance)
        Arguments.of(rolePerm, READ, true),
        // ✗ no permission granted
        Arguments.of(null, READ, false)
    );
}
```

---

## 4. Risk 过滤（控制 case 数量）

| Risk | 含义 | 生成 |
|------|------|------|
| 3 | 权限绕过、多条件组合、继承链截断、suspect 列表中的每条缺陷 | 必须 |
| 2 | happy path、反向 false case | 每条路径/场景 ≥1 个 |
| 1 | 与已有 case 高度相似的变体 | 跳过 |
