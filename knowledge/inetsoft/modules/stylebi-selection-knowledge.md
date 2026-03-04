# Knowledge Extraction - StyleBI Selection Components

## Overview

The **Selection component family** in StyleBI provides interactive controls for filtering and refining data displayed in views.  
When used in a view, these components can trigger **linked filtering** on other `DataView` components and can **persist or export the current selection state**.

---

## Component Types

### Selection List

- **Definition**: A list-based selection control.
- **Characteristics**: Well-suited for one-dimensional, flat filtering scenarios.

### Selection Tree

- **Definition**: A tree-structured selection control.
- **Characteristics**: Supports multi-level hierarchies, ideal for data with parent-child or categorized structures.

---

## Selection Modes

### Single Selection / Multiple Selection

- The components support both **single-select** and **multi-select** modes.
- In the browser, users can use **Alt + Click** as a shortcut to quickly switch selection behavior between single and multiple (a platform interaction feature).

---

## Display Modes

- **Normal mode**: Standard-sized display, suitable for common view layouts.
- **Enlarge mode**: Enlarged display, useful when more screen space is needed for user interactions.

---

## Container Structure

### Selection Container

- A container component that can host multiple:
  - `Selection List`
  - `Selection Tree`
- Used to compose multiple filter controls into a unified filtering area.

---

## Usage Context

### Devices

Selection components can be used in the following environments:

- **Standard web browsers (Web)**
- **Mobile devices (Mobile)**

---

## Interaction Behavior

### Data Filtering

- User selections in `Selection List` / `Selection Tree` drive **linked filtering** on other `DataView` components.
- By adjusting selection criteria, the user influences what data is displayed in related views.

### Popup Interaction

- `Selection List` and `Selection Tree` can also be used as **popup components** attached to Text or Image elements in a view.
- When the user clicks the text or image, the corresponding Selection component is displayed as a popup, allowing the user to make a selection.
- After the selection is confirmed in the popup, it triggers the same behaviors as normal Selection components: **linked filtering**, **bookmark state persistence**, and **export state preservation**.

### Bookmark State

- The `Bookmark` feature needs to **persist the current Selection state**.
- When a user returns to a view via a bookmark, the system should restore:
  - Previously selected items in the Selection components
  - The associated linked filtering conditions

### Export

- When **exporting a view** (Export), the current Selection state must be preserved:
  - Ensures that exported content (e.g., PDF/Excel) matches the active filter conditions.
- The exported data should be consistent with what the user currently sees in the view.

---

## Structural Relationships

- `Selection Container` → **may contain** → `Selection List` / `Selection Tree`
- `Selection` components → **act on** → `DataView` to implement linked data filtering
- `Bookmark` / `Export` features → **must preserve** → the current Selection state

---

## Terminology

- **Selection List**: List-based filtering control.
- **Selection Tree**: Tree-structured filtering control.
- **Selection Container**: A container component that holds multiple selection controls.
- **Normal / Enlarge Mode**: Display mode configuration (standard / enlarged).
- **DataView**: Data view component that reflects the results of Selection-based filtering.
- **Bookmark**: Saves the view state for later restoration (including Selection state).
- **Export**: Exports view data (e.g., PDF / Excel) based on the current filter conditions.

---

## Rules / Constraints

- **Filtering linkage rules**:
  - Selections made in Selection components affect data display in other view components.
- **State persistence rules**:
  - Bookmarks must include the current Selection state.
  - Export operations must also be based on the current Selection state.

---

## Functional Capabilities

### Selection Filtering

- By selecting items via list/tree controls:
  - Triggers corresponding linked filtering logic.
  - Controls the dataset and content displayed in target DataViews.

### State Preservation

- The Selection state remains consistent in the following scenarios:
  - Bookmark saving and restoration.
  - View export (Export), where exported data mirrors the current on-screen state.

---

> Note: The above structured knowledge is derived from the StyleBI official documentation **"Use Filter Components"**.

