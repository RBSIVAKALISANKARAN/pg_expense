# Project Plan – Finance Wallet + SQL Playground

## Core business rule

This project follows the savings model agreed from a.md:

- Savings is an earmarked portion of the same source balance.
- Allocating to savings reduces spendable, instead of creating a duplicate copy.
- Total balance is always: spendable + savings.
- Expenses should default to spendable.
- If an expense is intentionally taken from savings, that portion should also be reduced from the savings bucket.
- Money should be tracked as one real balance, split logically into spendable and savings buckets.

This is the key rule for all models, APIs, and UI flows.

---

## Final product vision

The system is a full personal finance management app with a PostgreSQL-backed database and a built-in SQL playground.

It includes:
- wallet/account tracking
- spendable and savings allocations
- deposits and expenses
- transfer logic between spendable and savings
- categories and items
- transactions history
- reports and summaries
- SQL editor for real PostgreSQL queries
- database explorer
- saved queries and history
- examples and schema browsing
- settings and deployment-ready configuration

---

## Execution strategy

We will build the system in phases, one phase at a time. Each phase must be complete and validated before the next phase begins.

---

## Phase 0 – Foundation and repository readiness

Goal:
- confirm the repo structure, environment, and developer setup are correct
- ensure PostgreSQL, Django, and dependency setup are ready

Tasks:
- verify project folder structure
- verify virtual environment and Python dependencies
- confirm PostgreSQL database connection
- validate Django startup
- confirm .env configuration
- confirm base app structure

Output:
- Working Django app ready to build on

---

## Phase 1 – Finance data model and database schema

Goal:
- define the real database tables and balance logic

Core tables:
- accounts
- allocations
- transactions
- categories
- items
- people / payees (if required)
- query history and saved queries

Rules:
- each account has spendable and savings allocation records
- every financial action is recorded as a transaction
- money is stored using Decimal values
- all balance math must be atomic and consistent

Output:
- working PostgreSQL schema with migrations

---

## Phase 2 – Wallet core logic

Goal:
- implement the real balance engine

Tasks:
- create account
- auto-create allocations for spendable + savings
- deposit money
- expense from spendable by default
- expense from savings when explicitly selected
- transfer from spendable to savings
- transfer from savings to spendable
- validate that total balance remains correct

Critical rules:
- spendable + savings = total balance
- no double-counting
- every financial update must be recorded with a transaction entry
- use database transaction safety for consistency

Output:
- wallet engine that behaves correctly with real money movements

---

## Phase 3 – Transaction, category, and item flows

Goal:
- support realistic finance entries beyond simple balance changes

Tasks:
- add transaction entry forms
- add category model and category UI
- add item model
- attach transaction to category/item/wallet
- support date, amount, type, description, and notes
- filter transactions by wallet/date/type/category

Output:
- usable transaction data capture and listing

---

## Phase 4 – Dashboard and wallet UI

Goal:
- create the main frontend experience for the finance app

Tasks:
- total balance card
- spendable card
- savings card
- recent transactions list
- quick action buttons
- wallet overview page
- dashboard layout
- responsive UI for desktop/laptop use

Output:
- a usable landing dashboard for daily finance tracking

---

## Phase 5 – Reports, summaries, and exports

Goal:
- turn raw transaction data into useful analysis

Tasks:
- monthly summary
- category-wise summary
- wallet-wise summary
- savings summary
- spendable summary
- income vs expense summary
- CSV export for reports
- API endpoints for summary data

Output:
- reporting layer for finance insights

---

## Phase 6 – SQL Playground backend

Goal:
- build a secure PostgreSQL SQL execution environment inside Django

Tasks:
- create SQL execution endpoint
- validate incoming SQL
- block dangerous commands like DROP/DELETE/ALTER/CREATE on non-approved modes
- allow safe SELECT-style query execution
- return rows, metadata, error messages, execution time
- handle empty result sets correctly
- keep PostgreSQL credentials on the backend only

Important rule:
- Browser never talks to PostgreSQL directly.
- Django acts as the secure bridge.

Output:
- backend SQL execution layer that safely executes read-only or controlled queries

---

## Phase 7 – SQL Editor frontend

Goal:
- build the actual SQL editor UI for real query writing

Tasks:
- editor area with multi-line support
- syntax highlighting for SQL
- line numbers
- clear button
- run button
- Ctrl + Enter execution shortcut
- query formatting support
- keep query text while result is displayed
- show success/error status
- show execution time

Output:
- a real SQL editor page inside the app

---

## Phase 8 – Database explorer and schema browsing

Goal:
- make SQL learning easier by exposing the database structure

Tasks:
- list tables in a sidebar
- show columns for each table
- allow click-to-insert column names into the editor
- show table metadata and schema details
- allow quick SQL snippet insertion

Output:
- discoverable database explorer for the project schema

---

## Phase 9 – Query history, saved queries, and examples

Goal:
- support learning, reuse, and experimentation

Tasks:
- auto-store executed queries in history
- show history by date/time
- click a history query to reload it into the editor
- allow saved queries with title and description
- allow load/edit/delete saved queries
- include example SQL snippets for common finance questions

Output:
- reusable SQL learning workflow

---

## Phase 10 – Settings, security, and UX polish

Goal:
- prepare the app for regular use and safer operation

Tasks:
- app settings and configuration
- database safety controls
- user access and auth planning
- UI polish
- validation messages
- result formatting
- timezone and currency setup
- error display quality

Output:
- cleaner and safer app experience

---

## Phase 11 – Testing, validation, and bug fixes

Goal:
- confirm all phases are working together

Tasks:
- wallet logic tests
- API tests
- SQL safety tests
- result rendering tests
- regression checks
- data integrity checks

Output:
- stable and verified system

---

## Phase 12 – Deployment preparation

Goal:
- prepare the app for running in a real environment

Tasks:
- production settings
- environment variables
- secure configuration
- database migration flow
- run instructions
- optional Docker setup
- final readiness checks

Output:
- deployment-ready project

---

## Recommended start order

1. Phase 0 – foundation
2. Phase 1 – schema
3. Phase 2 – wallet core logic
4. Phase 3 – transactions and categories
5. Phase 4 – dashboard UI
6. Phase 5 – reports and exports
7. Phase 6 – SQL backend
8. Phase 7 – SQL editor frontend
9. Phase 8 – schema explorer
10. Phase 9 – history + saved queries
11. Phase 10 – settings and safety
12. Phase 11 – testing
13. Phase 12 – deployment

---

## Final interpretation

This project is not just a savings wallet app.

It is a combined system:
- personal finance tracking
- real PostgreSQL database
- spendable/savings logic
- transaction engine
- SQL playground for learning and querying the app’s own database

The savings behavior is fixed as:
- same balance, split into earmarked buckets
- not a duplicated copy
- total balance must remain consistent at all times

That rule must be respected in every phase of development.
