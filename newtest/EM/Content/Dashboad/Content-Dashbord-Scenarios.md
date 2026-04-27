---
module: Content-Dashboard / Regression Scenarios
source: Content-Dashboard-Overview.md, Content-Dashboard-GlobalDashboard.md, Content-Dashboard-UserPortalDashboard.md
last-updated: 2026-04-27
---

> P3 scenarios are excluded. Items marked _(inferred)_ are expanded from context.
> Items marked [NEEDS CLARIFICATION] require manual review.

## Feature Summary

### 功能简述
Content-Dashboard covers Global Dashboards managed from EM and User Dashboards created
from the Portal Dashboard tab. The core business objects are dashboard repository
resources, their bound viewsheet/dashboard assets, visibility state, ordering, owner
metadata, and access permissions. The primary users are Site Admins, Org Admins,
authorized EM users, and Portal users who consume or manage their own dashboards.

### 规则与注意点

#### 通用规则
- Global Dashboards are created and edited in EM, persisted as repository resources,
  and displayed read-only in Portal when their saved Enable/security state allows it.
- User Dashboards are created from Portal, stored under the owning user's dashboard
  scope, and remain editable through the supported EM and Portal management surfaces.
- Dashboard name, description, bound asset, order, Enable state, and delete results must
  persist after reload and synchronize across the relevant EM and Portal views.

#### 权限与可见性
- With `security=true`, Global Dashboard Portal visibility requires both dashboard
  resource ACCESS and Dashboard access permission.
- EM repository visibility depends on ADMIN access to the relevant dashboard repository
  path and dashboard resource.
- A permitted non-admin creator receives access to the Global Dashboard they create;
  other users require explicit grants.
- Global Dashboards remain read-only in Portal; Portal users must not mutate their
  metadata, binding, order, or resource state.

#### 多租户与资源归属
- Site Admin creation through Org filter must assign dashboard resource ownership and
  access ownership to the target org, not Host-Org.
- Org Admin and permitted internal user creation uses the currently logged-in tenant
  user as owner.
- Clone Org clones dashboard resources but not per-user Enable state; cloned-org Enable
  state is managed independently and must sync with Site Admin's Org filter view.
- User Dashboard storage and edits are tenant-scoped and must not leak across orgs.

#### 特殊情况 / 已知风险
- Bug #69387 covers wrong owner/access assignment after Site Admin switches org with Org
  filter.
- Bug #69347 covers cloned org user Enable state behavior and depends on Bug #69387.
- Bug #69468 covers private asset binding visibility, including cross-org User
  Dashboard cases.
- Security mode switching is low priority; cover only basic visibility behavior.
- Missing bound assets should fail clearly with `sheet not found` without corrupting
  other dashboard state.

#### 生成取舍
- User/role/group and ADMIN/ACCESS matrix combinations are represented by grant/deny or
  owner-focused cases; exhaustive permission matrix coverage is deferred to Security.
- UI-only checks such as dialog open, button enabled state, scrollbars, default
  selection, and generic toolbar "work correctly" behavior are excluded as P3.
- Toolbar actions are not generated here unless they create or mutate dashboard-owned
  business state; concrete outcomes belong to related modules such as Scheduler, Mail,
  Export, or Composer.

## Scenario Overview

| ID(s) | Priority | Area | Scenario | Key Business Assertion |
|-------|----------|------|----------|------------------------|
| CD-CRUD-001 - CD-CRUD-006 | P1/P2 | CRUD | Dashboard lifecycle persistence and synchronization | Create, edit, arrange, delete, and validation flows preserve correct repository, Portal, binding, order, and identity state. |
| CD-PERM-001 - CD-PERM-005 | P1/P2 | Permissions | Dashboard permission and visibility integration | ACCESS/ADMIN permissions, creator grants, read-only Portal behavior, and binding authorization control what users can see or persist. |
| CD-MT-001 - CD-MT-005 | P1/P2 | Multitenant | Tenant ownership, clone behavior, and cross-surface sync | Dashboard resources, owners, Enable state, and User Dashboard edits remain scoped to the selected org and synchronized across tenant views. |
| CD-EDGE-001 | P2 | Edge Cases | Private asset binding restriction | Users cannot expose or persist another user's private dashboard asset through User Dashboard binding, including cross-org cases. |
| CD-EDGE-002 - CD-EDGE-003 | P2 | Edge Cases | Security mode switch visibility behavior | Basic visibility follows explicit ACCESS after enabling security and EM-side Enable after disabling security. |
| CD-EDGE-004 | P2 | Edge Cases | Missing bound asset handling | Broken bindings fail clearly with `sheet not found` and do not corrupt unrelated dashboard state. |

## CRUD - Persistence And Synchronization

#### CD-CRUD-001 Create Global Dashboard Persists Resource State `P1`

**Scope:** EM > Content > Repository > Portal Dashboard
**Validates rule:** Global Dashboards are created from EM and must persist as repository
resources with the correct bound dashboard and Portal availability state.

**Pre-conditions:** A source viewsheet dashboard exists. The actor is Site Admin, Org
Admin, or a user with the required EM and Portal Dashboard Tab permissions.

**Steps:**
1. Create a Global Dashboard in EM with a unique name and a valid bound dashboard.
2. Reload EM and verify the dashboard resource still exists with the same binding.
3. **Sync check:** As an allowed Portal user, open the dashboard and verify the saved
   binding and availability state.

**Expected:**
- The dashboard resource is persisted under the Global Dashboard repository path.
- The saved binding opens the expected dashboard asset.
- EM and Portal show the same persisted name, description, binding, and availability.
- EM does not create a User Dashboard through this Global Dashboard creation flow.

#### CD-CRUD-002 Add User Dashboard Persists To The User Scope `P1`

**Scope:** Portal Dashboard tab and EM User Dashboard repository tree
**Validates rule:** User Dashboards are created from Portal and are managed as the
individual user's dashboards.

**Pre-conditions:** The user can access Portal Dashboard and at least one eligible
dashboard asset is available for binding.

**Steps:**
1. Create a User Dashboard from Portal with a unique name and a valid bound dashboard.
2. Reload Portal and verify the dashboard still opens the selected asset.
3. **Sync check:** As an authorized EM administrator, verify the same User Dashboard
   exists under the user's dashboard repository scope.

**Expected:**
- The User Dashboard is persisted for the owning user.
- Portal and EM resolve the same dashboard resource.
- The saved binding remains intact after reload.

#### CD-CRUD-003 Edit Dashboard Data And Binding Across EM And Portal `P1`

**Scope:** EM and Portal edit paths for Global Dashboards and User Dashboards
**Validates rule:** Dashboard edits must update persisted dashboard data and remain
synchronized across the supported management surfaces.

**Pre-conditions:** A Global Dashboard and a User Dashboard exist. The actor has edit
access through the relevant management surface.

| Condition / Action | Expected Result |
|--------------------|-----------------|
| Rename a Global Dashboard from EM | The new name is persisted and shown consistently in EM and Portal. |
| Change a Global Dashboard description from EM | The new description is persisted and shown consistently in EM and Portal. |
| Change the bound asset for a Global Dashboard | The dashboard opens the newly bound asset in EM and Portal. |
| Rename a User Dashboard from Portal or EM | The new name is persisted and shown consistently in Portal and EM. |
| Change the bound asset for a User Dashboard | The dashboard opens the newly bound asset in Portal and EM. |
| Change binding across global-scope and user-scope assets | The binding is saved and synchronized; exact source marker meaning is [NEEDS CLARIFICATION]. |

#### CD-CRUD-004 Arrange Dashboard Order And Enable State Persist `P1`

**Scope:** EM Global Dashboard arrange flow and Portal Arrange Dashboards
**Validates rule:** Dashboard order changes affect both Portal and EM. Portal Arrange
`Enable` controls Portal display only and must not overwrite EM-side `Enable`.

**Pre-conditions:** Multiple dashboards exist. At least one dashboard is visible in
Portal and manageable from EM.

| Condition / Action | Expected Result |
|--------------------|-----------------|
| Reorder Global Dashboards from EM | Order is persisted and synchronized to Portal, EM repository ordering, and EM Arrange. |
| Reorder dashboards from Portal Arrange | Order is persisted on Portal and reflected on EM Arrange. |
| Disable a dashboard from Portal Arrange | Dashboard is hidden on Portal, while EM-side `Enable` and Security settings are unchanged. |
| Disable a Global Dashboard from EM-side `Enable` | Dashboard is removed from Portal availability and from the EM Arrange page. |

#### CD-CRUD-005 Delete Dashboard Cleans Repository And Portal References `P1`

**Scope:** EM and Portal dashboard delete flows
**Validates rule:** Deleting a dashboard must remove the persisted resource and all
Portal/Arrange references that depend on it.

**Pre-conditions:** A Global Dashboard and a User Dashboard exist.

| Condition / Action | Expected Result |
|--------------------|-----------------|
| Delete a Global Dashboard from EM | The resource is removed from EM, Portal, and Global Dashboard arrange state. |
| Delete a User Dashboard from EM | The resource is removed from EM and Portal for that user. |
| Delete a User Dashboard from Portal | The resource is removed from Portal, EM, and the user's Arrange Dashboards state. |

#### CD-CRUD-006 Reject Invalid Dashboard Identity Or Missing Binding `P2`

**Scope:** Dashboard creation and edit persistence rules
**Validates rule:** Dashboard identity and binding constraints protect persisted dashboard
state from invalid or ambiguous records.

**Pre-conditions:** Dashboard creation or edit is being saved from a supported surface.

| Condition / Action | Expected Result |
|--------------------|-----------------|
| Save with an empty dashboard name | Save is rejected and no dashboard resource is created or overwritten. |
| Save with a duplicate dashboard name in the same scope | Save is rejected and the existing dashboard remains unchanged. |
| Save without a required bound dashboard | Save is rejected and no dashboard is created with an unresolved binding. |

## Permissions - Integration Boundaries

#### CD-PERM-001 Global Dashboard Portal Visibility Respects ACCESS `P1`

**Scope:** Portal Dashboard visibility with `security=true`
**Validates rule:** With `security=true`, a user must have dashboard resource access and
Dashboard access permission enabled to see a Global Dashboard.

**Pre-conditions:** `security=true`; a Global Dashboard exists; one representative user
is available for grant and deny checks.

**Steps:**
1. With ACCESS denied, verify the representative user cannot see or open the Global
   Dashboard in Portal.
2. Grant ACCESS for the same user to the Global Dashboard.
3. **Sync check:** Verify the same user can see and open the dashboard in Portal.

**Expected:**
- Without ACCESS, the user cannot see or open the Global Dashboard in Portal.
- With ACCESS, the user can see and open the Global Dashboard in Portal.
- Full user/role/group matrix coverage is deferred to Security module tests.

#### CD-PERM-002 EM Repository Visibility Respects Dashboard ADMIN Access `P1`

**Scope:** EM repository tree visibility for Dashboard resources
**Validates rule:** Dashboard repository visibility must integrate with ADMIN permission
on the relevant repository nodes and dashboard resources.

**Pre-conditions:** `security=true`; a Global Dashboard and a User Dashboard exist; one
representative non-admin actor is available.

| Condition / Action | Expected Result |
|--------------------|-----------------|
| Actor has representative ADMIN access for the dashboard repository path | Dashboard resource is visible and manageable in EM. |
| Actor does not have ADMIN access for the dashboard repository path | Dashboard resource is not visible or manageable in EM. |
| Actor has ADMIN access to their own user dashboard scope | Their own User Dashboard can be managed through the authorized EM path. |

#### CD-PERM-003 Global Dashboard Creator Receives Access `P1`

**Scope:** EM Global Dashboard creation with `security=true`
**Validates rule:** A user with valid EM and Portal Dashboard Tab permission receives
access permission on the Global Dashboard they create.

**Pre-conditions:** `security=true`; a non-admin user has the required creation
permissions.

**Steps:**
1. As the permitted non-admin user, create a Global Dashboard from EM.
2. Verify the saved access state grants the creator access to the new dashboard.
3. **Sync check:** Verify the same user can open the created dashboard in Portal.

**Expected:**
- Dashboard creation succeeds.
- The creator receives access to the newly created Global Dashboard.
- Other users do not receive access unless access is explicitly granted.

#### CD-PERM-004 Global Dashboards Remain Read-Only In Portal `P1`

**Scope:** Portal access to Global Dashboards
**Validates rule:** Global Dashboards are read-only in Portal. All edits are done in EM.

**Pre-conditions:** A Global Dashboard is visible to a Portal user.

**Steps:**
1. Attempt any supported Portal edit or delete path for the Global Dashboard, including direct
   action invocation if available _(inferred)_.
2. Reload EM and Portal to verify the dashboard resource state is unchanged.

**Expected:**
- Portal cannot modify or delete the Global Dashboard.
- No dashboard name, binding, description, order, or resource state is changed by the
  Portal user.

#### CD-PERM-005 Unauthorized Assets Cannot Be Bound To Dashboards `P2`

**Scope:** Dashboard binding from EM and Portal
**Validates rule:** Dashboard binding must not allow a user to persist a reference to a
dashboard asset they are not authorized to use.

**Pre-conditions:** `security=true`; one allowed asset and one denied asset exist for a
representative actor.

| Condition / Action | Expected Result |
|--------------------|-----------------|
| Actor binds to an allowed dashboard asset | Save succeeds and the dashboard opens the selected asset. |
| Actor attempts to bind to a denied dashboard asset | Save is rejected or the denied asset is unavailable; no persisted unauthorized binding is created. |

## Multitenant - Tenant Ownership And Isolation

#### CD-MT-001 Site Admin Org Filter Creates Dashboard In Target Org `P1`

**Scope:** EM Global Dashboard creation with Org filter
**Validates rule:** When Site Admin creates a dashboard after switching Org filter, the
dashboard resource and access permission must belong to the target org's admin, not
Host-Org.

**Pre-conditions:** Multi-tenancy is enabled. Site Admin can switch to a target org.
The target org has an Org Admin and at least one dashboard asset for binding.

**Steps:**
1. As Site Admin with Org filter set to the target org, create a Global Dashboard.
2. Verify the dashboard resource owner and access permission owner belong to the target
   org context.
3. **Sync check:** As target Org Admin, verify the created dashboard is manageable.

**Expected:**
- Resource ownership is assigned to the target org context.
- Access permission is assigned to the target org admin.
- Host-Org does not receive resource ownership or access by mistake.

#### CD-MT-002 Org Admin And Internal User Creation Uses Current User Ownership `P1`

**Scope:** EM Global Dashboard creation inside a tenant org
**Validates rule:** When an Org Admin or internal user creates a dashboard, the owner is
the currently logged-in user.

**Pre-conditions:** Multi-tenancy is enabled. An Org Admin and a permitted internal user
exist in the same tenant org.

| Condition / Action | Expected Result |
|--------------------|-----------------|
| Org Admin creates a Global Dashboard | Dashboard owner is the logged-in Org Admin and the resource is stored in that org. |
| Internal user with required permissions creates a Global Dashboard | Dashboard owner is the logged-in internal user and the resource is stored in that org. |
| Site Admin views the same org through Org filter | Dashboard appears under the selected org, not Host-Org. |

#### CD-MT-003 Clone Org Clones Dashboard Resources But Not User Enable State `P2`

**Scope:** Clone Org and dashboard Enable state
**Validates rule:** Dashboard resources are cloned, but per-user Enable state is not
cloned. The cloned org's Enable state is independently managed by its Org Admin and must
sync with Site Admin's Org filter view.

**Pre-conditions:** Source org has dashboard resources and configured Enable state. Bug
#69387 is fixed or not blocking this scenario.

**Steps:**
1. Clone the source org.
2. As the cloned org's Org Admin, verify dashboard resources exist and configure their
   Enable state.
3. **Sync check:** As Site Admin with Org filter set to the cloned org, verify the same
   cloned-org Enable state.

**Expected:**
- Dashboard resources are cloned.
- Per-user Enable state is not blindly copied from the source org.
- Cloned Org Admin and Site Admin Org filter views remain synchronized.

#### CD-MT-004 User Dashboard Storage And Three-Side Sync Are Tenant Scoped `P1`

**Scope:** User Dashboards in Site Admin EM, Org Admin EM, and user Portal
**Validates rule:** In multitenant mode, User Dashboards are stored in the corresponding
org's user portal dashboard folder and changes sync across Site Admin EM, Org Admin EM,
and the user's Portal.

**Pre-conditions:** Multi-tenancy is enabled. A tenant user can create a User Dashboard.
Site Admin, Org Admin, and the user can access their respective views.

**Steps:**
1. Create or edit a User Dashboard as the tenant user in Portal.
2. **Sync check:** Verify the same name, description, binding, and order in Org Admin
   EM and Site Admin EM with Org filter set to the tenant org.
3. Edit the User Dashboard from an EM management surface and verify Portal reflects the
   change.

**Expected:**
- User Dashboard storage is scoped to the owning org.
- All three management surfaces show the same persisted state.
- No dashboard state leaks into another org.

#### CD-MT-005 Site Admin Can Edit Other Org User Dashboard Through Org Filter `P1`

**Scope:** Site Admin EM with Org filter and User Dashboard binding
**Validates rule:** Host-Org via Org filter can read and write other orgs' User Portal
Dashboards when binding global-scope assets.

**Pre-conditions:** Target org has a User Dashboard and an eligible global-scope asset.

**Steps:**
1. As Site Admin with Org filter set to the target org, edit the target user's User
   Dashboard binding to a global-scope asset.
2. **Sync check:** As the target user, verify the User Dashboard opens the new binding.

**Expected:**
- Site Admin can update the target org User Dashboard through Org filter.
- The update is limited to the selected target org and target user.

## Edge Cases

#### CD-EDGE-001 Private Asset Binding Restriction Is Enforced `P2`

**Scope:** EM edit binding panel for User Dashboards
**Validates rule:** When a User Dashboard is bound to a private asset, EM can only show
the currently logged-in user's private assets. Other users' dashboards show an empty
bound dashboard instead of exposing a private asset.

**Pre-conditions:** A user owns a private dashboard asset and has a User Dashboard bound
to it. Another authorized EM actor can open the user's dashboard resource.

**Steps:**
1. As the owner, bind the User Dashboard to the owner's private dashboard.
2. Open the same User Dashboard edit binding from another authorized EM actor.
3. Repeat in the cross-org case where applicable.

**Expected:**
- The owner can resolve the private bound asset.
- Other actors do not see or bind the owner's private asset.
- Cross-org behavior follows the same private asset restriction.

#### CD-EDGE-002 Security Switch From `false` To `true` Resets Public Visibility `P2`

**Scope:** Global Dashboard visibility after security mode change
**Validates rule:** After switching to `security=true`, Portal visibility must require
explicit permission grants.

**Pre-conditions:** `security=false`; enabled Global Dashboards are visible in Portal.

**Steps:**
1. Switch `security` to `true`.
2. As a representative regular user, verify dashboards are not visible by default and
   the saved permission state denies access.
3. Grant ACCESS to one dashboard and verify the same user sees only the granted
   dashboard.

**Expected:**
- The user no longer sees dashboards by default after switching to `security=true`.
- Default permission state denies access.
- After ACCESS is granted, the user sees only the granted dashboard.

#### CD-EDGE-003 Security Switch From `true` To `false` Uses EM Enable State `P2`

**Scope:** Global Dashboard visibility after security mode change
**Validates rule:** After switching to `security=false`, EM-side `Enable` controls Portal
availability, and Portal Arrange Enable remains portal-scoped.

**Pre-conditions:** `security=true`; dashboards are visible to a user because access was
granted.

**Steps:**
1. Switch `security` to `false` and verify dashboards with EM-side `Enable=true` are
   available in Portal.
2. Disable one dashboard from Portal Arrange and verify EM-side `Enable` remains
   unchanged.
3. Disable one dashboard from EM-side `Enable`.
4. **Sync check:** Verify that dashboard is no longer available in Portal or EM Arrange.

**Expected:**
- Portal availability follows EM-side `Enable` after switching to `security=false`.
- Portal Arrange Enable does not overwrite EM-side Enable.
- EM-side disable removes the dashboard from Portal availability.

#### CD-EDGE-004 Missing Bound Asset Fails With A Clear Dashboard Error `P2`

**Scope:** Portal opening a dashboard whose bound asset no longer exists
**Validates rule:** A dashboard with a missing bound asset should fail clearly without
corrupting other dashboard state.

**Pre-conditions:** A Portal dashboard exists and is bound to a viewsheet dashboard
asset.

**Steps:**
1. Remove or rename the bound asset so the dashboard binding points to a missing asset.
2. Open the affected dashboard from Portal.
3. Open a different dashboard afterward.

**Expected:**
- Error dialog is shown: `sheet not found`.
- The affected dashboard does not open stale or incorrect content.
- Other dashboards remain usable.

---

## Uncovered Rules

Dashboard toolbar actions are intentionally not generated as P1/P2 because the source
only states that they must "work correctly" and does not define a module-specific
business state. Cover specific toolbar outcomes in related modules when the action
creates or mutates state.

## Clarification Needed

| Item | Reason |
|------|--------|
| Cross-scope dashboard binding marker | Source marks same-scope and different-scope binding cases with `*`, but does not define what the marker means. |

## Related Module Tests

| Related Module | Relationship | Suggested Extension |
|----------------|--------------|---------------------|
| Content-Repository | Dashboards are repository resources and visibility depends on repository permissions. | Cover repository create, delete, owner metadata, node-level ADMIN/READ inheritance, and filtering there. |
| Security | Dashboard visibility and binding depend on Security grants. | Cover full user/role/group, ACCESS/ADMIN, inheritance, and deny matrix in Security tests. |
| Multi-Tenancy | Org filter, tenant storage, clone behavior, and permission ownership are required setup. | Run org creation, clone, and org-switching coverage before dashboard tenant scenarios. |
| Composer | Portal compose flow can create assets used by User Dashboards. | Verify compose-created assets in Composer tests; dashboard regression only needs persisted binding coverage. |
| Scheduler | Dashboard toolbar Schedule action belongs to scheduler workflows. | Verify created schedule tasks in Scheduler tests rather than generic dashboard toolbar smoke. |
| Mail / Export | Email, print, and snapshot actions depend on environment services. | Cover only concrete stateful results in those modules or service-specific tests. |
