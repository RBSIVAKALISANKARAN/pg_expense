# Frontend Product Plan

## Goal
Build a proper finance management website experience that feels like a real app, not just a backend dashboard. The frontend should support the wallet logic, SQL playground, categories, transactions, reports, and settings in a clean UI shell.

---

## Phase F1 – App shell and layout foundation

### Goal
Create the base website shell used across pages.

### Requirements
- left sidebar navigation
- top navbar
- page content area
- responsive layout for desktop and smaller screens
- brand/title header
- user menu/action area
- theme toggle button
- consistent spacing, colors, cards, and typography

### Deliverables
- base layout template
- reusable CSS file
- sidebar sections: Dashboard, Accounts, Transactions, Categories, SQL Playground, Reports, Settings
- navbar with search/actions
- default light and dark theme styling

---

## Phase F2 – Home page / dashboard UI

### Goal
Build the main landing page for the finance app.

### Requirements
- summary cards: Total Balance, Spendable, Savings, This Month
- recent transactions list
- quick actions panel
- account overview cards
- spending category highlights
- “Add Expense”, “Add Deposit”, “Transfer” actions
- simple charts or colored blocks for visual balance summary

### Deliverables
- dashboard homepage layout
- summary cards
- account cards with spendable/savings split
- finance overview design

---

## Phase F3 – Accounts page

### Goal
Create a dedicated accounts management page.

### Requirements
- create account form
- account list with balance details
- spendable and savings numbers shown per account
- account card actions
- add deposit action
- transfer between spendable and savings form
- account status display

### Deliverables
- accounts page UI
- account creation flow
- balance display
- action controls

---

## Phase F4 – Transactions page

### Goal
Create the transaction management experience.

### Requirements
- transaction table with columns: date, type, account, category, amount, allocation, status
- search and filter controls
- add expense form
- add deposit flow
- transfer actions
- empty state if no data
- quick actions for delete/view if needed

### Deliverables
- transactions page UI
- filtering/search
- forms for expense/deposit entry

---

## Phase F5 – Categories and items page

### Goal
Support category-based payment tracking.

### Requirements
- list of categories
- add category form
- list of items under each category
- add item form
- category and item selection in transaction forms
- visual distinction between parent/child classification

### Deliverables
- categories page UI
- item management UI
- linked transaction usage

---

## Phase F6 – Reports page

### Goal
Turn data into business insights.

### Requirements
- summary cards: income, expense, net, savings rate
- monthly report cards
- category-wise breakdown
- wallet comparison cards
- export button
- plain report table

### Deliverables
- reports page UI
- summary blocks
- analytics layout

---

## Phase F7 – SQL Playground integrated into app shell

### Goal
Fit the SQL Playground into the website instead of leaving it as an isolated page.

### Requirements
- use app shell layout
- sidebar entry for SQL Playground
- query editor area
- schema panel
- saved queries/history panel
- result table area
- dark SQL editor styles
- consistent color theme

### Deliverables
- app-integrated SQL page
- better SQL editor UX

---

## Phase F8 – Settings page and profile section

### Goal
Provide configuration and account preferences.

### Requirements
- general settings form
- default currency
- timezone
- preferred allocation default
- dark/light mode setting
- preferences save flow
- profile and security section placeholders

### Deliverables
- settings page UI
- preferences panel
- visual polish

---

## Phase F9 – Final UX polish and product feel

### Goal
Make the app look and feel like a finished product.

### Requirements
- consistent color system
- clean spacing and shadows
- hover effects
- table style improvements
- better empty states
- improved mobile responsiveness
- consistent buttons and forms
- dashboard polish

### Deliverables
- final polished app interface
- product-quality frontend UX

---

## Execution order

1. F1 – App shell and layout foundation
2. F2 – Home page / dashboard UI
3. F3 – Accounts page
4. F4 – Transactions page
5. F5 – Categories and items page
6. F6 – Reports page
7. F7 – SQL Playground integrated into app shell
8. F8 – Settings page and profile section
9. F9 – Final UX polish

---

## Notes
- This frontend phase will be implemented on top of the existing backend logic.
- We are not rebuilding the data model again.
- We are improving the visible product experience and navigation.
- The final website should feel like a finance management SaaS dashboard, not a backend debug page.
