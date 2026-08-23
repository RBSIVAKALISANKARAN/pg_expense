Part 1 — **SQL** Editor: Exact Behavior & Requirements

The **SQL** Editor should be a real PostgreSQL query interface inside the Django application, not a simulated analytics/search box. Its purpose is to let me write **SQL** against my finance database, execute it, inspect the result, understand errors, and use the real data for **SQL** practice.

## SQL Editor Page

The page should contain these major areas:

┌─────────────────────────────────────────────────────────────┐ │ **SQL** **PLAYGROUND** │ ├─────────────────────────────────────────────────────────────┤ │ Database: Finance PostgreSQL │ │ │ │ [Tables] [Saved Queries] [History] [Examples] │ │ │ │ ┌─────────────────────────────────────────────────────────┐ │ │ │ **SQL** **EDITOR** │ │ │ │ │ │ │ │ **SELECT** category, │ │ │ │ **SUM**(amount) AS total_spent │ │ │ │ **FROM** transactions │ │ │ │ **WHERE** transaction_type = '**EXPENSE**' │ │ │ │ **GROUP** BY category │ │ │ │ **ORDER** BY total_spent **DESC**; │ │ │ │ │ │ │ └─────────────────────────────────────────────────────────┘ │ │ │ │ [▶ Run] [Format] [Clear] [Save Query] │ ├─────────────────────────────────────────────────────────────┤ │ **RESULT** / **ERROR** │ │ │ │ ... │ └─────────────────────────────────────────────────────────────┘

---

## SQL Editor

The editor should behave like a proper code editor.

Required features

**SQL** syntax highlighting

Line numbers

Automatic indentation

Bracket/quote matching

Multi-line queries

Basic autocomplete

Table/column suggestions

**SQL** formatting

Clear button

Run button

Keyboard shortcut such as Ctrl + Enter to execute

Preserve the query while viewing results

Display execution status

Display execution time

For example, while typing:

**SELECT** * **FROM** tran

the editor should be able to suggest:

transactions

And after:

**SELECT** t. **FROM** transactions t

it should be able to suggest available columns.

---

## Database Explorer Inside SQL Editor

The **SQL** editor should have a collapsible sidebar showing the database structure.

**DATABASE**

▾ Tables

    ▾ transactions
    transaction_id
    date
    time
    amount
    type
    wallet_id
    category_id
    item_id
    ...

    ▾ wallets
    wallet_id
    wallet_name
    wallet_type
    ...

    ▾ categories
    category_id
    category_name
    ...

    ▾ items
    item_id
    item_name
    ...

    ▾ people
    person_id
    person_name

Clicking a table should show its columns.

Ideally, clicking a column should insert its name into the editor.

For example:

transactions
    amount

click → inserts:

transactions.amount

This makes the schema easier to learn.

---

## Query Execution

When I press Run, the flow should be:

Browser ↓ Django backend ↓ Validate **SQL** ↓ PostgreSQL ↓ Execute query ↓ Return result/error ↓ Django ↓ Browser

The browser should never directly connect to PostgreSQL.

PostgreSQL credentials must remain on the Django server.

---

## Query Results

For a **SELECT** query, results should appear in a table.

Example:

**RESULT** — 5 rows

┌──────────────┬──────────────┐ │ category │ total_spent │ ├──────────────┼──────────────┤ │ Food │ ₹4,**250** │ │ Transport │ ₹1,**840** │ │ Household │ ₹**920** │ │ Education │ ₹**450** │ └──────────────┴──────────────┘

Rows: 5 Execution time: 18 ms

The result renderer should automatically adapt to the returned columns.

It should not assume that every query returns the same structure.

---

## SQL Errors Must Be Displayed

Errors should not be hidden.

If I write:

**SELECT** category **SUM**(amount) **FROM** transactions;

the UI should show something like:

❌ **QUERY** **ERROR**

syntax error at or near *SUM*

**LINE** 1:
**SELECT** category **SUM**(amount)
                 ^

Also show:

PostgreSQL error message

Error type/code where available

Line number where available

Column position where available

Execution time

The original **SQL** should remain in the editor so I can correct it.

---

## Empty Results

A valid query returning zero rows is not an error.

Example:

**SELECT** * **FROM** transactions **WHERE** amount > **100000**;

The UI should say:

✓ Query executed successfully

0 rows returned.

No matching records.

It should not display an **SQL** error.

---

## Query History

Every successfully executed query should optionally be stored in history.

Example:

**QUERY** **HISTORY**

Today ────────────────────────────

11:42 AM Weekly coffee spending

11:35 AM Monthly transport spending

10:50 AM Total savings

Yesterday ────────────────────────────

...

Clicking a history item should load the **SQL** back into the editor.

History should store:

query executed_at execution_status execution_time

For errors, optionally store the error message too.

---

## Saved Queries

History and Saved Queries should be different.

History

Automatically records what I executed.

### Saved Queries

Queries I intentionally want to keep.

Example:

**SAVED** **QUERIES**

☕ Food
    Weekly coffee spending
    Monthly tea spending
    Junk food spending

🚍 Transport
    Weekly bus spending
    Monthly transport spending

💰 Savings
    Monthly savings
    Savings by wallet

📊 General
    Total spending
    Highest spending items

Each saved query should have:

Name Description **SQL** Created date Updated date

---

## Query Examples / SQL Practice

Because this application is also intended for **SQL** learning, there should be an Examples section.

Organize it by difficulty:

**SQL** **EXAMPLES**

Beginner ├── **SELECT** all transactions ├── Total spending ├── Total income ├── Filter expenses ├── **ORDER** BY amount └── **LIMIT** 10

Intermediate ├── **GROUP** BY category ├── **GROUP** BY wallet ├── Monthly spending ├── **JOIN** transactions + categories ├── **HAVING** └── **CASE**

Advanced ├── Subqueries ├── Correlated subqueries ├── **CTE** ├── Window functions ├── Running totals └── Ranking

Clicking an example should load the **SQL** into the editor, but should not automatically execute it.

That allows me to study it first.

---

## Query Safety

This is extremely important because this is the real finance database.

Initially, the playground should be read-only.

Allowed:

**SELECT** **WITH** **EXPLAIN**

Potentially allowed later in a controlled practice environment:

**INSERT** **UPDATE** **DELETE** **CREATE** **ALTER** **DROP**

But never allow destructive **SQL** against the production finance database by default.

For example:

**DROP** **TABLE** transactions;

should be blocked.

The ideal architecture eventually becomes:

PostgreSQL
│
├── finance database
│ └── **REAL** **PERSONAL** **DATA**
│
└── sql practice database
      └── disposable practice data

Then advanced **SQL**/**DML**/**DDL** practice can happen safely.

---

## Query Result Export

Useful but secondary.

The result could eventually support:

[Copy] [Download **CSV**]

For example, if I execute:

**SELECT** * **FROM** transactions;

I should be able to copy or export the returned table.

---

## Query Performance Information

For every query, display:

Status: **SUCCESS** Rows: 42 Execution time: 14 ms

Later, an optional:

# EXPLAIN QUERY PLAN

feature can help me learn PostgreSQL performance.

---

## Important Design Principle

The **SQL** Editor should not create separate analytical databases or duplicate transaction data.

There should be exactly one source of truth:

PostgreSQL
    │
    ┌───────┴───────┐
    │ │
    Finance UI **SQL** Editor
    │ │
    └───────┬───────┘
    │
    Same database

The normal UI inserts/updates data.

The **SQL** Editor queries that same data.

Therefore:

> Whatever I enter through the finance UI should immediately be available to my **SQL** queries.

And whatever query I write should reflect the current database state.

---

Part 2 — Application UI Pages

The application should stay relatively simple. We don't need the enormous number of analytical pages from the previous Sheets architecture.

I would start with these pages:

# PERSONAL FINANCE APPLICATION

## Dashboard

## Add Transaction ## Transactions ## Wallets ## Categories & Items ## SQL Playground ## Database Schema ## Saved Queries / Query History ## Settings

## Dashboard

A simple overview, not an enormous analytics engine.

Show things such as:

### Current Balance

Today's Income Today's Expense Today's Savings

### Recent Transactions

### Wallet Balances

### Quick Actions

[Add Transaction] [**SQL** Playground]

The dashboard should remain lightweight.

---

## Add Transaction

This is the primary data-entry page.

Something like:

**DATE** **TIME**

**ITEM** **AMOUNT** **WALLET**

**TYPE** **CATEGORY** **SUBCATEGORY**

**PERSON** **PAYMENT** **METHOD**

**DESCRIPTION**

[ **SAVE** **TRANSACTION** ]

The fields should dynamically change based on what is selected.

For example, selecting a food item can expose the food-specific attributes we eventually define.

---

## Transactions

A searchable transaction table:

Transactions

Date | Time | Item | Type | Amount | Wallet | Category | ...

Features:

Search

Date filter

Category filter

Wallet filter

Type filter

Edit

Delete

View details

This is the actual transaction management page.

---

## Wallets

Manage wallets:

Wallets

**UPI** Cash Bank Savings ### Travel Card ...

Each wallet can contain attributes such as:

Wallet ID Name ### Wallet Type ### Opening Balance Active

The exact wallet model should be finalized separately before development.

---

## Categories & Items

This is where the classification system we are currently designing belongs.

For example:

**FOOD** ├── Breakfast ├── Lunch ├── Dinner ├── Snacks └── Drinks

**TRANSPORT** ├── Bus ├── Metro ├── Train └── Cab

**HOUSEHOLD** ├── Bathing ├── Washing └── Cleaning

But we should not finalize this hierarchy yet. We are still discussing your actual requirements.

---

## SQL Playground

This is the major learning feature.

**SQL** Editor ### Database Explorer ### Query Result Errors History ### Saved Queries Examples

All against PostgreSQL.

---

## Database Schema

A visual database map.

It should automatically show:

**TABLE**
    │
    ├── PK
    ├── columns
    └── FK
    │
    ▼
    **RELATED** **TABLE**

For example:

transactions
    │
    ├──── wallet_id ────► wallets
    │
    ├──── category_id ──► categories
    │
    ├──── item_id ──────► items
    │
    └──── person_id ────► people

This page is particularly useful for learning relational database design.

---

## Saved Queries / History

This can either be a separate page or a section inside **SQL** Playground.

I prefer it as a sidebar within **SQL** Playground initially, so the application doesn't become unnecessarily fragmented.

---

## Settings

Keep this minimal.

Potentially:

Currency Date format Time format Default wallet Theme **SQL** safety settings

---

Overall UI Architecture

The final application could therefore be:

# PERSONAL FINANCE APP

    │
    ┌───────────────────────┼───────────────────────┐
    │ │ │
    **FINANCE** **SQL** **DATABASE**
    **MANAGEMENT** **LEARNING** **STRUCTURE**
    │ │ │
    ┌─────┼─────┐ ┌──────┼──────┐ ┌─────┴─────┐
    │ │ │ │ │ │ │ │
Dashboard Add Transactions Editor History Examples Schema
    │
    Wallets
    │
 Categories/Items
    │
    Settings

    ↓
    PostgreSQL
    **SINGLE** **SOURCE**
    OF **TRUTH**

This is the UI structure I would give the building AI before it writes any Django models or code.

The next step should be Part 3: define exactly what data each page collects and what PostgreSQL tables/relationships are required. That is where we should carefully work through your item list rather than letting the AI invent a schema.Part 3 — **SQL** Playground: How the Backend Should Work

The **SQL** Playground should not just be a text box connected directly to PostgreSQL. It should be a controlled **SQL** learning and analytics environment inside the application.

## Overall Architecture

The flow should be:

User ↓ **SQL** Editor UI ↓ ### Django Backend ↓ **SQL** Validation / Safety Layer ↓ PostgreSQL ↓ Query Result / Error ↓ Django **API** ↓ **SQL** Playground UI

The important point is that PostgreSQL remains the actual source of truth. Django handles authentication, validation, execution, and presentation.

---

## SQL Editor

The main area should contain a proper **SQL** editor.

Example:

**SELECT**
    DATE_TRUNC('week', date) AS week,
    **SUM**(amount) AS total_spent
**FROM** transactions
**WHERE** item = 'Coffee'
  **AND** type = '**EXPENSE**'
**GROUP** BY week
**ORDER** BY week;

The editor should support:

**SQL** syntax highlighting

Line numbers

Proper indentation

Multi-line queries

Clear button

Run button

Keyboard shortcut such as Ctrl + Enter

Query history

Error highlighting where practical

The user should be able to write real PostgreSQL **SQL**, rather than using a simplified custom query language.

---

## Run Query

When the user clicks Run:

**SQL** entered
     ↓
Django receives query
     ↓
Validate query
     ↓
Execute against PostgreSQL
     ↓
Return result

For example:

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** item = 'Coffee';

Output:

sum

₹**850**

The result should appear immediately below the editor.

---

## Query Errors Must Appear in the UI

This is particularly important for your **SQL** practice.

If you write:

**SELECT** name **FROM** transaction;

and the table doesn't exist, the UI should not simply say *Query failed.*

It should display the PostgreSQL error.

For example:

❌ Query Error

relation *transaction* does not exist

Position: 28

And ideally:

Line 2, Column 6

This makes the playground useful for learning **SQL**, not merely viewing analytics.

---

## Result States

The output area should have clear states.

Successful query

✓ Query executed successfully

4 rows returned Execution time: 12 ms

Then the result table.

No rows

✓ Query executed successfully

0 rows returned

**SQL** error

✕ Query failed

column *amout* does not exist

Dangerous/unsupported query

⚠ Query blocked

This operation is not permitted in the **SQL** Playground.

---

## Read-Only SQL Playground

For your personal finance application, I strongly recommend that the normal playground initially allow:

**SELECT**

and analytical operations such as:

**WHERE** **GROUP** BY **ORDER** BY **HAVING** **JOIN** **CASE** **CTE** **WINDOW** **FUNCTIONS** **DATE** **FUNCTIONS** **AGGREGATE** **FUNCTIONS** **SUBQUERIES**

For example:

**SELECT**
    item,
    **SUM**(amount) AS total_spent
**FROM** transactions
**WHERE** type = '**EXPENSE**'
**GROUP** BY item
**ORDER** BY total_spent **DESC**;

This gives you almost everything required for financial analysis without allowing an accidental query to destroy your database.

---

## Why We Should Not Allow DELETE/UPDATE Initially

Suppose you accidentally type:

**DELETE** **FROM** transactions;

That could destroy your financial history.

Similarly:

**DROP** **TABLE** transactions;

could destroy the entire application database.

Therefore the first version should have a read-only transaction/session for the playground.

Allowed:

**SELECT**

Blocked:

**INSERT** **UPDATE** **DELETE** **DROP** **ALTER** **TRUNCATE** **CREATE**

Later, if you specifically want a database-management mode, we can create a separate Admin **SQL** Console.

---

## Multiple Queries

The editor can eventually support:

**SELECT** * **FROM** transactions;

**SELECT** * **FROM** wallets;

**SELECT** * **FROM** categories;

But there should be a clear rule about execution.

For the first version:

> Execute one **SQL** statement at a time.

Later we can add:

### Run Current Query

### Run All Queries

---

## Query History

Every successfully executed query can optionally be stored in a query_history table.

For example:

ID Query Executed At Status Execution Time

1 **SELECT** **SUM**(amount)... 23-Aug-**2026** Success 14 ms 2 **SELECT** ... 23-Aug-**2026** Error 8 ms

Then the UI can have:

### Query History

### Recent Queries

## Weekly coffee spending

## Monthly expense ## Food category analysis ## Savings transfers ## Expenses by wallet

Clicking one can load the query back into the editor.

This would be extremely useful for your **SQL** practice.

---

## Saved Queries

We should also have a Saved Queries concept.

For example:

📁 My Queries

Food ├── Weekly Food Spending ├── Monthly Coffee Spending └── Junk Food Spending

Transport ├── Monthly Bus Expense ├── Metro Expense └── Rapido vs Uber

Finance ├── Monthly Income ├── Monthly Expense └── Savings

A saved query could contain:

Name Description **SQL** ### Created At ### Updated At

Then you can reuse queries instead of rewriting them every day.

---

## Query Result Export

The result table should eventually support:

Copy Download **CSV**

For example:

**SELECT**
    item,
    **SUM**(amount) AS total
**FROM** transactions
**WHERE** type = '**EXPENSE**'
**GROUP** BY item
**ORDER** BY total **DESC**;

Then:

[Copy] [**CSV**]

---

## Query Explanation

Since one of your goals is learning **SQL**, we can add an optional button:

### Explain Query

You write:

**SELECT**
    category,
    **SUM**(amount)
**FROM** transactions
**WHERE** type = '**EXPENSE**'
**GROUP** BY category;

The application can show:

### Query Structure

1. **FROM**
   Reads transactions

2. **WHERE**
   Keeps only **EXPENSE** transactions

## GROUP BY

Groups records by category

4. **SUM**
   Calculates total amount per category

## SELECT

Returns category + total

This should be an optional learning feature, not something that interferes with normal execution.

---

## Schema Explorer Beside the Editor

The **SQL** Playground should have a left-side database explorer.

Example:

**DATABASE**
└── personal_finance
    │
    ├── transactions
    │ ├── id
    │ ├── date
    │ ├── time
    │ ├── item
    │ ├── amount
    │ ├── type
    │ ├── wallet_id
    │ └── ...
    │
    ├── wallets
    │ ├── id
    │ ├── name
    │ └── wallet_type
    │
    ├── categories
    │ ├── id
    │ ├── name
    │ └── ...
    │
    └── ...

Clicking a table should reveal its columns.

Clicking a column could optionally insert it into the editor.

For example:

transactions ↓ amount

could insert:

amount

into the editor.

This makes writing queries much easier on a phone.

---

## Relationship / ER Map

The second important part is the database map you mentioned.

There should be a separate page:

### Database Structure

Something like:

┌──────────────┐
    │ Wallets │
    │──────────────│
    │ id PK │
    │ name │
    │ wallet_type │
    └──────┬───────┘
    │
    │ wallet_id
    │
    ┌──────▼────────┐
    │ Transactions │
    │───────────────│
    │ id PK │
    │ wallet_id FK │
    │ category_id FK│
    │ person_id FK │
    │ amount │
    │ date │
    └───┬──────┬────┘
    │ │
    category │ │ person
    │ │
    ┌──────▼─┐ ┌──▼──────┐
    │Categories│ │ People │
    └─────────┘ └────────┘

The map should be generated from PostgreSQL's actual foreign-key metadata, rather than manually maintaining another copy of the relationships.

That is important because if we change the database later, the diagram automatically reflects the real structure.

---

## Table Detail Page

Clicking:

Transactions

could open:

Transactions

Columns

### Column Type Nullable Key

id **BIGINT** No PK date **DATE** No time **TIME** Yes item **VARCHAR** No amount **NUMERIC** No type **VARCHAR** No wallet_id **BIGINT** No FK

Then:

### Referenced By

    ↓
...

and:

References
    ↓
Wallets
Categories
People

This will help you understand relational database design while actually using your own project.

---

## SQL Autocomplete

A good **SQL** editor should eventually understand the schema.

When you type:

**SELECT** * **FROM** trans

it can suggest:

transactions

After:

**SELECT** t.

it can suggest:

t.id t.date t.time t.item t.amount t.type t.wallet_id ...

This is especially valuable on mobile.

---

## Mobile Layout

Because you specifically want to enter transactions from your phone and practise **SQL** from your phone, the **SQL** Playground must be responsive.

Desktop:

┌─────────────┬──────────────────────────────┐ │ Schema │ **SQL** Editor │ │ Explorer │ │ │ │ **SELECT** ... │ │ Tables │ │ │ Columns │──────────────────────────────│ │ │ Query Result │ └─────────────┴──────────────────────────────┘

Phone:

┌────────────────────────┐ │ **SQL** Playground │ ├────────────────────────┤ │ Tables ▼ │ ├────────────────────────┤ │ **SQL** Editor │ │ │ │ **SELECT** ... │ │ │ ├────────────────────────┤ │ ▶ **RUN** │ ├────────────────────────┤ │ Result / Error │ └────────────────────────┘

---

## Performance & Security

Because the **SQL** editor talks to the real PostgreSQL database, Django should enforce:

Authentication

Authorization

Read-only database role

Query timeout

Result row limit

Statement validation

Maximum query execution time

Protection against multiple destructive statements

Proper PostgreSQL parameter handling where application-generated queries are used

For example, we can impose:

Maximum execution time: 5 seconds Maximum displayed rows: 1,**000**

The database itself should have a dedicated read-only user for the playground.

---

## The Most Important Principle

The application should have one database.

Not:

### App Database

### Analytics Database **SQL** Playground Database

Instead:

PostgreSQL
    │
    ┌───────────┼───────────┐
    ↓ ↓ ↓
    Main UI Analytics **SQL** Playground
    │ │ │
    └───────────┴───────────┘
    │
    Same source data

So if you enter:

Coffee ₹20

from your phone:

Phone ↓ Django **API** ↓ PostgreSQL

your laptop doesn't need to be running at all.

When you later open the application on your laptop, it reads the same PostgreSQL database.

And your **SQL** query:

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** item = 'Coffee';

reads that same data.

That gives us a very clean architecture:

> One PostgreSQL database → Django application → Transaction UI + **SQL** Playground + Database Explorer + Reports.

And importantly, we should finish defining the actual data model and business rules before building this. That will prevent us from repeating the spreadsheet problem where functionality kept getting added before the underlying requirements were completely settled.Yes. Before Django/PostgreSQL, let's freeze the requirements properly. We should not start coding yet.

Personal Finance System — Requirements Definition

The goal is a simple personal finance application, not a giant Excel replacement.

The core idea is:

> Record real transactions → store structured information → use PostgreSQL + **SQL** to discover insights.

The application should make entering data easy, while the **SQL** Playground lets you practise **SQL** and answer questions about your own financial data.

---

## Core System

# PERSONAL FINANCE APP

    │
    ┌──────────────┴──────────────┐
    │ │
    Transaction UI **SQL** Playground
    │ │
    └──────────────┬──────────────┘
    ↓
    PostgreSQL
    │
    ┌──────────┴──────────┐
    ↓ ↓
    Financial Data Relationships

Technology

Frontend: responsive web UI

Backend: Django

Database: PostgreSQL

Authentication: user account/login

Deployment: cloud

**SQL** Playground: PostgreSQL queries through Django

Database Explorer: tables, columns, relationships

---

## The Most Important Principle

We will have one source of truth:

transactions

Every actual financial movement gets recorded there.

We should not create separate databases for analytics, savings, reports, dashboard, etc.

Those are derived from transactions.

For example:

Transaction ₹20 Coffee ↓ transactions table ↓ **SQL** query ↓ *How much did I spend on coffee this month?*

---

## What Is a Transaction?

A transaction represents one real-world financial event.

Examples:

₹20 Coffee ₹30 Bus ₹**150** Money received ₹30 **UPI** → Savings ₹**100** **ATM** → Cash

The basic information should be:

Transaction ├── ID ├── Date ├── Time ├── Item ├── Amount ├── Type ├── Wallet ├── Category ├── Subcategory ├── Payment Method ├── Person ├── Description └── optional attributes

But we should not blindly create every possible column yet.

We will define each one properly.

---

## Transaction Type

Initially, keep this very simple:

**INCOME** **EXPENSE** **TRANSFER**

**INCOME**

Money entering your financial system.

Example:

₹**150** received

**EXPENSE**

Money spent.

Example:

₹20 Coffee ₹30 Bus

**TRANSFER**

Money moving between wallets.

Example:

**UPI** → Savings ₹30 **UPI** → Cash ₹**100**

Transfers are not expenses.

This distinction is fundamental.

---

## Expense Detection

Your earlier idea can be simplified:

> If the transaction is **EXPENSE**, it is an expense.

We should not try to infer expenses purely from the item name.

For example:

Coffee → **EXPENSE** Bus → **EXPENSE** Money → **INCOME** **UPI** → Cash → **TRANSFER**

The user selects the transaction type when entering it.

Later, we can make the UI smarter with defaults.

---

## Wallets

Wallets represent where your money currently exists.

Examples:

Cash **UPI** Savings ### Bank Account ### Travel Card

Each wallet should have attributes such as:

Wallet ├── ID ├── Name ├── Wallet Type ├── Opening Balance ├── Active └── Include in Balance calculations

We should decide the exact wallet types later rather than hard-code them unnecessarily.

---

## Transfers

Transfers require two wallets:

### Source Wallet

### Destination Wallet Amount

Example:

₹30

Source: **UPI**

Destination: Savings

Type: **TRANSFER**

This gives us:

**UPI** -₹30 Savings +₹30

But:

Total Expense = ₹0 Total Income = ₹0

This prevents double-counting.

---

## Savings

We don't necessarily need a completely independent *Savings transaction database.*

Savings can be identified from transfers.

For example:

**TRANSFER** **UPI** → Savings ₹30

The database can determine:

Savings contribution = ₹30

Similarly:

Savings → **UPI** ₹50

can represent a savings withdrawal.

This keeps the architecture clean.

---

## Food Classification

This is one area where your requirements are more detailed.

You don't just want:

Food

You want to answer questions such as:

> How much did I spend on junk snacks?

> How much did I spend on healthy drinks?

> How much did I spend on sugary food?

> How much did I spend on breakfast?

Therefore food needs multiple dimensions.

For food items, we can have:

Food ├── Meal ├── Food Group ├── Health Classification ├── Sugary └── Item

Meal

**BREAKFAST** **LUNCH** **DINNER** **SNACK**

Potentially:

**OTHER**

because real life doesn't always fit perfectly.

### Food Group

For example:

MAIN_FOOD **SNACK** **DRINK** **FRUIT** **VEGETABLE**

### Health Classification

**HEALTHY** **JUNK** **NEUTRAL**

Sugary

**YES** NO

Now a transaction can contain:

Coffee Meal: **BREAKFAST** Group: **DRINK** Health: **JUNK** Sugary: **YES**

Then **SQL** becomes extremely powerful.

---

## Your Food Examples

Your existing items can eventually map into structured master data.

For example:

Dosa ├── normal ├── egg dosa ├── onion dosa ├── podi dosa └── special dosa

Similarly:

Bun ├── normal ├── jam bun ├── cream bun ├── paalkova bun └── honey bun

And:

Puffs ├── veg ├── egg ├── chicken ├── mushroom └── paneer

The important architectural decision is:

> Item names should not contain all the classification information.

The database should know the classifications separately.

---

## Other Categories

Your non-food expenses should also be structured.

For example:

Transport

Bus ├── Whiteboard └── **MTC**

Metro

Rapido

Uber

Ola

Train

### Personal Care

Haircut Shave Soap Shampoo ### Bathing Soap

Household

Detergent ### Vim Liquid ### Scrub Bar ### Washing Soap ### Bathing Powder

Education / Stationery

Notebook File Pen Paper Pencil Rubber Scale Xerox

Medical

Medicine ├── Tablet ├── Ointment └── Syrup

with:

### Medicine Name

as a user-entered value.

Religious

Garland ### Incense Sticks Kaanikai ### Pooja Items

Financial / Other

**TMB** Charges ### Travel Card Recharge **UPI** → Cash ### Money Received

---

## Typeable Items

We should not create a database master record for every possible thing in the world.

Some items must remain user-entered.

Examples:

### Cool Drink

Fruit Vegetable Soap Shampoo Medicine Detergent

So the UI should allow:

Select predefined item
        OR
Type a new item

This is important because your original requirement was:

> unexpected expenses can happen.

The system must never force you to choose from a fixed list.

---

## People

We should have a people table.

For example:

People ├── ID ├── Name └── Active

A transaction can optionally belong to a person.

Example:

₹**500** Birthday Cake Contribution Person: Someone

But Person should be optional.

Blank should mean:

Unassigned / Personal

rather than producing an error.

---

## Categories

We should have a hierarchical category structure.

Something like:

Food ├── Main Food ├── Snacks ├── Drinks ├── Fruits └── Vegetables

Transport ├── Bus ├── Metro ├── Cab └── Train

### Personal Care

├── Bathing ├── Hair └── Grooming

Household ├── Cleaning └── Washing

Education └── Stationery

Medical └── Medicine

Religious └── Pooja

Financial └── Charges

Other

But we should not finalize these blindly. We'll review them against your actual two-month data before creating the database.

---

15. Time

Every transaction should have:

Date Time

This allows queries such as:

-- Spending by day -- Spending by week -- Spending by month -- Spending at a particular time -- Morning vs evening spending

We don't need to store:

Day Month Year Week Quarter

as duplicated transaction columns.

PostgreSQL can derive them from date.

---

## Amount

Use PostgreSQL:

**NUMERIC**

not floating-point types.

For money:

**NUMERIC**(12,2)

This avoids financial rounding problems.

---

## Currency

For now:

**INR** / ₹

We don't need a multi-currency system unless you actually need one.

---

## What We Want to Query

This is the reason we're designing the database carefully.

You should eventually be able to write:

Basic

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** type = '**EXPENSE**';

Weekly coffee

**SELECT**
    DATE_TRUNC('week', transaction_date),
    **SUM**(amount)
**FROM** transactions
**WHERE** item = 'Coffee'
**GROUP** BY 1
**ORDER** BY 1;

Junk snacks

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** food_group = '**SNACK**' **AND** health_classification = '**JUNK**';

Healthy drinks

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** food_group = '**DRINK**' **AND** health_classification = '**HEALTHY**';

Sugary food

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** sugary = **TRUE**;

Spending by wallet

**SELECT**
    w.name,
    **SUM**(t.amount)
**FROM** transactions t
**JOIN** wallets w
    ON w.id = t.wallet_id
**WHERE** t.type = '**EXPENSE**'
**GROUP** BY w.name;

This is exactly where your database design starts paying off.

---

## SQL Playground

The **SQL** Playground will use the same database.

Transaction UI
      ↓
PostgreSQL ← **SQL** Playground
    ↑
    │
Dashboard / reports

Therefore you can:

## Enter today's transaction.

## It gets saved to PostgreSQL.

## Open SQL Playground.

## Write a query.

## Immediately see the new transaction in the result.

That gives you a real **SQL** learning environment using your own real dataset.

---

## Pages We Actually Need

For the first functional version, I would keep the application small.

Page 1 — Login

Login Register Logout

Page 2 — Home

Simple overview:

Current balances Today's income Today's expense Today's transfers Today's savings Recent transactions

No huge analytics dashboard initially.

Page 3 — Add Transaction

The most important page.

Date Time Type Item Amount Wallet Category Subcategory ...

Dynamic fields appear depending on transaction type.

Page 4 — Transactions

Search/filter:

Date Item Type Category Wallet Amount

Page 5 — Wallets

Manage:

Cash **UPI** Savings etc.

Page 6 — Master Data

Manage:

Items Categories People Wallets

Page 7 — **SQL** Playground

Your **SQL** learning/analytics environment.

Page 8 — Database Explorer

Tables + columns + relationships.

That's enough for V1.

---

## What We Are NOT Building Yet

This is important.

We are not initially building:

15 different dashboards

complicated **MAB** engine

huge financial reporting engine

automatic budgeting

AI financial advisor

complicated charts

50 validation systems

Excel-like spreadsheet replacement

duplicate analytical databases

First:

> Get the data model right → get transaction entry right → get PostgreSQL right → get **SQL** Playground right.

Then we can add features based on actual usage.

---

## The Database We Are Heading Toward

Conceptually:

users
 │
 └──────────────┐
    │
    ↓
    transactions
    │ │ │
    │ │ ├──────── people
    │ │
    │ ├───────────── wallets
    │
    ├────────────────── items
    │
    └────────────────── categories

Food-specific classification can be represented through the item/category structure rather than stuffing dozens of unrelated fields into every transaction.

---

## One Critical Decision Before Schema Design

Before I write the actual PostgreSQL tables, primary keys, foreign keys, relationships, constraints and Django models, we need to settle one thing:

How should item classification work?

I recommend this model:

**ITEM**
│
├── Item Name
├── Category
├── Subcategory
│
└── optional attributes
    ├── Food Group
    ├── Meal
    ├── Health Classification
    └── Sugary

So Coffee can be classified once in the item master, and every future Coffee transaction automatically gets those classifications.

But if you sometimes classify the same item differently depending on context, we need a slightly different design.

This is the next thing we should settle before touching PostgreSQL.Yes. Let's settle it now so we can move to the database schema without ambiguity.

Final decision: Item Master + Transaction Context

I recommend not storing all food classifications directly in transactions.

Instead, we'll separate:

**ITEM** **MASTER**
     ↓
**TRANSACTION**

The item master defines what an item normally is. The transaction records what actually happened.

## Item Master

Each item gets a reusable definition:

### Attribute Example

### Item Coffee

### Category Food ### Subcategory Drinks ### Food Group Drink ### Health Classification Junk ### Sugary Yes

So Coffee is classified once.

Then every time you enter:

> Coffee ₹20

the application knows its classifications automatically.

---

## But what about different contexts?

This is the important part.

Suppose you have:

> Egg

You might eat an egg as part of breakfast, lunch, or dinner.

Therefore Meal is **NOT** an item-master attribute.

Instead:

### Item Master

Egg Category: Food Food Group: Main Food Health: Healthy Sugary: No

Transaction

Date: **2026**-08-23 Item: Egg Meal: Lunch Amount: ₹20

Another transaction:

Date: **2026**-08-24 Item: Egg Meal: Breakfast Amount: ₹20

Same item, different context.

This gives us much better **SQL** analysis.

---

## Final Food Classification

For food transactions, we'll use:

Item-level attributes

### Food Group

### Health Classification Sugary

Transaction-level attributes

Meal

So:

**ITEM**
    │
    ┌─────────┼─────────┐
    ↓ ↓ ↓
    Food Group Health Sugary
    │
    │
    ↓
    **TRANSACTION**
    │
    ↓
    Meal

---

## Example

Coffee

Item: Coffee Category: Food Subcategory: Drinks Food Group: Drink Health: Junk Sugary: Yes

Transaction:

Date: 23-Aug-**2026** Time: 08:30 Item: Coffee Meal: Breakfast Amount: ₹20

Now you can ask:

Total coffee spending

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** item_id = ...;

Junk drink spending

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** food_group = '**DRINK**' **AND** health_classification = '**JUNK**';

Sugary food spending

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** sugary = **TRUE**;

Breakfast spending

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** meal = '**BREAKFAST**';

Junk drinks consumed during breakfast

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** meal = '**BREAKFAST**' **AND** food_group = '**DRINK**' **AND** health_classification = '**JUNK**';

That's exactly the type of analysis you said you want to practise.

---

## What About Buns, Puffs, Dosa etc.?

We'll treat variants as individual items, not nested spreadsheet-style objects.

For example:

### Egg Dosa

### Onion Dosa ### Podi Dosa ### Normal Dosa ### Special Dosa

### Normal Bun

### Jam Bun ### Cream Bun ### Paalkova Bun ### Honey Bun

### Veg Puff

### Egg Puff ### Chicken Puff ### Mushroom Puff ### Paneer Puff

Each can have its own classification.

For example:

### Jam Bun

Category: Food Subcategory: Snacks Food Group: Snack Health: Junk Sugary: Yes

---

## What About Typeable Items?

We keep the ability to enter something new.

Suppose tomorrow you eat:

> Apple

and Apple isn't yet in the item master.

The UI should allow:

Item: [ Apple ]

Then it can ask for classification:

Category: [ Food ▼ ]

Subcategory: [ Fruits ▼ ]

Food Group: [ Fruit ▼ ]

Health: [ Healthy ▼ ]

Sugary: [ No ▼ ]

Once saved, Apple becomes available for future transactions.

So we get both:

Predefined items + unexpected real-world items.

---

## Important: Classification Should Not Be Forced for Everything

A bus ticket doesn't need:

Meal ### Food Group Health Sugary

Therefore these are nullable/optional attributes.

Example:

Coffee Food → Drinks → Drink → Junk → Sugary

Bus Transport → Bus

The database shouldn't contain meaningless values like:

Bus Food Group = *Not Applicable* Sugary = *No*

Instead, those food-specific fields are simply **NULL**.

---

## Final Item Structure

Conceptually:

items ├── id ├── name ├── category_id ├── subcategory_id ├── food_group ├── health_classification ├── sugary └── active

And transaction:

transactions ├── id ├── date ├── time ├── item_id ├── amount ├── type ├── wallet_id ├── category_id ├── subcategory_id ├── meal ├── person_id ├── payment_method ├── description └── ...

We'll refine this when we create the actual schema.

---

## One More Important Design Decision

I recommend that Category and Subcategory come from the Item Master, rather than asking you to repeatedly select them during every transaction.

So when you choose:

> Coffee

the UI automatically knows:

Category → Food Subcategory → Drinks Food Group → Drink Health → Junk Sugary → Yes

You only enter the things that actually change from transaction to transaction:

Date Time Item Amount Wallet Meal Person ### Payment Method Description

This makes your daily entry much faster.

---

✅ Settled

Our rule is:

> Item Master = what the item is. Transaction = what happened when you used/bought it.

And specifically:

Item-level:

Category

Subcategory

### Food Group

### Health Classification

Sugary

Transaction-level:

Date

Time

Amount

Wallet

Type

Meal

Person

### Payment Method

Description

This is the model I recommend we lock in.

Next, we can define the complete database table-by-table — users, wallets, categories, subcategories, items, people, payment_methods, transactions, and the transfer structure — including every column, data type, PK, FK, relationship, and constraint. Done. We’ll treat the agreed design as settled and proceed from it.

### Finalized System Specification

We are building a personal expense-management + PostgreSQL **SQL**-practice application using:

Backend: Python + Django

Database: PostgreSQL

Frontend: Web UI, responsive for phone and laptop

Primary data source: PostgreSQL

Analytics: Primarily through **SQL** queries

**SQL** Playground: User-written PostgreSQL queries executed against the application's database

Schema Explorer: Tables, columns, keys, relationships, and visual database map

The important principle is:

> Keep the actual financial data model simple and clean. Don't recreate the enormous Excel architecture.

---

Part 1 — Main UI Pages

The application should contain these core pages:

## Dashboard

A simple overview:

Current total balance

Current wallet balances

Today's expense

Today's income

Today's savings

Recent transactions

Quick transaction entry

Quick links to **SQL** Playground and Database Map

The Dashboard should not attempt to contain every possible analysis.

---

## Add Transaction

This is the main data-entry screen.

Fields will dynamically change depending on what is being entered.

Basic fields:

Date Time Amount Wallet ### Transaction Type Item Description

For normal expenses:

Expense ↓ Item Category Subcategory Food attributes where applicable

For transfers:

Transfer ↓ ### From Wallet ### To Wallet

For income:

Income ↓ Source / Description Wallet

---

## Transactions

A complete transaction table.

Features:

Search

Date filtering

Wallet filtering

Category filtering

Type filtering

Edit

Delete

View transaction details

---

## Wallets

Manage wallets such as:

Cash **UPI** Bank Savings ### Travel Card

Each wallet should contain its configuration and current balance.

The exact wallets will be finalized from the requirements we already discussed.

---

## Categories / Items

This is where the structured item classification lives.

For example:

Food ├── Breakfast ├── Lunch ├── Dinner ├── Snacks └── Drinks

Food can additionally have:

Healthy Junk Sugary Non-Sugary

This is important because later you can query things such as:

How much did I spend on junk snacks?

or:

How much did I spend on sugary drinks?

The database should store these attributes rather than relying on the UI to infer them later.

---

Part 2 — **SQL** Playground

This is a first-class feature, not an afterthought.

Page structure

┌──────────────────────────────────────────────┐ │ **SQL** **PLAYGROUND** │ ├───────────────────────┬──────────────────────┤ │ │ │ │ **SQL** **EDITOR** │ **DATABASE** **SCHEMA** │ │ │ │ │ **SELECT** ... │ transactions │ │ │ wallets │ │ │ food_attributes │ │ │ categories │ │ │ ... │ │ │ │ ├───────────────────────┴──────────────────────┤ │ [Run Query] [Clear] [Format] │ ├──────────────────────────────────────────────┤ │ **OUTPUT** │ │ │ │ column1 | column2 | column3 │ │ --------|---------|--------- │ │ ... │ │ │ ├──────────────────────────────────────────────┤ │ Rows: 15 | Execution: 42 ms │ └──────────────────────────────────────────────┘

Query execution flow

User types PostgreSQL query
        ↓
Django receives query
        ↓
Django validates execution
        ↓
PostgreSQL executes query
    ↓
    ├── Success → result set
    │ ↓
    │ UI table
    │
    └── Error → PostgreSQL error
    ↓
    Error panel

Example:

**SELECT**
    **SUM**(amount) AS total_spent
**FROM** transactions
**WHERE** item = 'Coffee';

The UI displays:

## total_spent

₹**450**

If the query is wrong:

**SELECT** abc **FROM** transactions;

The UI should show the actual database error clearly, for example:

**ERROR**

column *abc* does not exist
**LINE** 1: **SELECT** abc
               ^

This makes the application simultaneously become your **SQL** practice environment.

---

Part 3 — Database Explorer / Schema Map

A separate page:

### Database Explorer

It should show:

Tables

transactions wallets categories items food_attributes ...

Clicking a table opens:

transactions

## Column Type

id **BIGINT** date **DATE** time **TIME** amount **NUMERIC** wallet_id **BIGINT** item_id **BIGINT** transaction_type **VARCHAR** ...

It should also identify:

PK FK **UNIQUE** **NOT** **NULL**

---

### Visual Database Map

Something like:

┌──────────────┐
    │ wallets │
    │──────────────│
    │ id PK │
    │ name │
    └──────┬───────┘
    │
    │ FK
    ▼
    ┌──────────────────┐
    │ transactions │
    │──────────────────│
    │ id PK │
    │ wallet_id FK │
    │ item_id FK │
    │ amount │
    │ date │
    │ type │
    └────────┬─────────┘
    │
    │ FK
    ▼
    ┌────────────┐
    │ items │
    └─────┬──────┘
    │
    ▼
    ┌───────────────┐
    │ categories │
    └───────────────┘

Clicking a relationship should make the connection understandable.

This page is especially useful for your **SQL** learning because you can visually understand:

> Which table contains the primary key? Which table contains the foreign key? How do I **JOIN** these tables?

---

Part 4 — **SQL** Learning / Query Workflow

The application should encourage you to actually write queries rather than hiding everything behind predefined analytics.

For example, you could manually write:

Total expense

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** transaction_type = '**EXPENSE**';

Weekly coffee spending

**SELECT**
    DATE_TRUNC('week', date) AS week,
    **SUM**(amount) AS total_spent
**FROM** transactions
**WHERE** item = 'Coffee'
**GROUP** BY week
**ORDER** BY week;

Junk-food spending

**SELECT** **SUM**(t.amount) **FROM** transactions t **JOIN** items i ON t.item_id = i.id **WHERE** i.food_quality = '**JUNK**';

Sugary drinks

**SELECT**
    **SUM**(t.amount)
**FROM** transactions t
**JOIN** items i ON t.item_id = i.id
**WHERE** i.food_category = '**DRINK**'
  **AND** i.is_sugary = **TRUE**;

So instead of building **100** predefined analytics screens, the system gives you:

Data → Database → **SQL** → Result

That is much closer to what you actually want.

---

Part 5 — What We Should **NOT** Do

We should deliberately avoid repeating the previous Excel approach.

We don't need:

14+ spreadsheet phases

Huge preallocated formula ranges

Hundreds of duplicated analytical formulas

Separate sheets for every possible analysis

Hard-coded analytics

Manual reconciliation everywhere

Complex dashboard calculations

Massive helper-column architecture

PostgreSQL will handle the relational work.

Django will handle the application/business logic.

The **SQL** Playground will handle your analytical exploration.

---

Part 6 — Development Order

Now that the concept is settled, the build should proceed in this order:

## Finalize requirements

        ↓
## Finalize database entities
        ↓
## Define every table
        ↓
## Define every column + datatype
        ↓
## Define PK/FK relationships
        ↓
## Define transaction rules
        ↓
## Create Django project
        ↓
## Create PostgreSQL database
        ↓
## Create Django models/migrations
        ↓
## Build transaction entry UI
        ↓
## Build transaction management
        ↓
## Build wallet management
        ↓
## Build category/item management
        ↓
## Build Dashboard
        ↓
## Build SQL Playground
        ↓
## Build Schema Explorer
        ↓
## Build visual DB relationship map
        ↓
## Test everything
        ↓
## Deploy to cloud

And because PostgreSQL is hosted remotely after deployment:

Phone ↓ Internet ↓ Django application ↓ PostgreSQL ↑ Django application ↑ Laptop

So yes: if you enter an expense from your phone, it is saved in the same PostgreSQL database and will be available from your laptop too.

The next step should therefore be database design from scratch—entities → tables → columns → datatypes → PK/FK → relationships → rules. We should not start coding until that model is settled.Yes. Let’s actually do the database design now, from scratch, and keep it deliberately simple.

I’m carrying forward the requirements we already settled: PostgreSQL is the source of truth; Django is the application layer; transactions are the core financial record; items have structured classification; food needs additional attributes; wallets are separate entities; and the **SQL** Playground/Schema Explorer are application features rather than separate databases.

Part 1 — Core Database Architecture

I recommend starting with 8 core tables, not 20+ tables.

users wallets categories items food_details transactions transaction_transfers mab_entries

Then Django's own authentication tables can be added separately.

The most important table is:

transactions

Everything financial ultimately comes back to it.

---

Part 2 — wallets

A wallet represents where the money currently exists.

Examples:

Cash **UPI** ### Bank Account Savings ### Travel Card

Table

Column PostgreSQL Type Rules

id **BIGSERIAL** PK name **VARCHAR**(**100**) **NOT** **NULL**, **UNIQUE** wallet_type **VARCHAR**(30) **NOT** **NULL** opening_balance **NUMERIC**(12,2) **NOT** **NULL**, >= 0 is_active **BOOLEAN** **DEFAULT** **TRUE** created_at **TIMESTAMPTZ** **DEFAULT** **NOW**()

wallet_type

For now:

**CASH** **BANK** **UPI** **SAVINGS** TRAVEL_CARD **OTHER**

Important:

Savings is a wallet type, not a separate money system.

So if ₹30 moves:

**UPI** → Savings

both wallets change, but it is not an expense.

---

Part 3 — categories

This stores the broad classification.

Example:

Food Transport Household ### Personal Care Education Medical Religious Financial Miscellaneous

Table

### Column Type

id **BIGSERIAL** PK name **VARCHAR**(**100**) is_active **BOOLEAN** created_at **TIMESTAMPTZ**

---

Part 4 — items

This is where your long item list belongs.

Instead of putting:

Coffee Bus Idly Dosa Soap Shampoo ...

directly into every transaction, we create an Item Master.

Table

### Column Type Purpose

id **BIGSERIAL** PK name **VARCHAR**(**150**) Item name category_id **BIGINT** FK → categories subcategory **VARCHAR**(**100**) More specific grouping is_food **BOOLEAN** Food or not is_active **BOOLEAN** Active item created_at **TIMESTAMPTZ** Created time

This allows:

Coffee ↓ Food ↓ Drinks

and:

Bus ↓ Transport

---

Part 5 — Food Classification

This is where your earlier idea becomes powerful.

You don't want only:

> *I spent ₹20 on Coffee.*

You want the database to understand:

> Coffee → Food → Drinks → Snack/Drink classification → Healthy/Junk → Sugary/Non-sugary

So food-specific information should be separated from the general item table.

food_details

### Column Type

item_id **BIGINT** PK/FK food_group **VARCHAR**(30) health_class **VARCHAR**(20) is_sugary **BOOLEAN**

food_group

**MEAL** **SNACK** **DRINK** **FRUIT** **VEGETABLE**

health_class

**HEALTHY** **JUNK** **NEUTRAL**

This gives us queries like:

**SELECT** **SUM**(t.amount) **FROM** transactions t **JOIN** items i ON t.item_id = i.id **JOIN** food_details f ON f.item_id = i.id **WHERE** f.food_group = '**SNACK**' **AND** f.health_class = '**JUNK**';

And:

**SELECT** **SUM**(t.amount) **FROM** transactions t **JOIN** items i ON t.item_id = i.id **JOIN** food_details f ON f.item_id = i.id **WHERE** f.food_group = '**DRINK**' **AND** f.is_sugary = **TRUE**;

This is exactly the type of **SQL** practice you wanted.

---

Part 6 — Food Item vs Meal

There is one important distinction.

An item has a general food classification.

But the transaction tells us when/how you consumed it.

For example:

Egg

could be:

Breakfast Lunch Dinner

depending on the transaction.

Therefore, meal should **NOT** be stored permanently in food_details.

It belongs to the transaction.

---

Part 7 — transactions

This is the central table.

Structure

Column PostgreSQL Type Rules

id **BIGSERIAL** PK transaction_id **VARCHAR**(30) **UNIQUE** transaction_date **DATE** **NOT** **NULL** transaction_time **TIME** **NULL** transaction_type **VARCHAR**(20) **NOT** **NULL** amount **NUMERIC**(12,2) > 0 wallet_id **BIGINT** FK → wallets item_id **BIGINT** FK → items description **TEXT** **NULL** meal **VARCHAR**(20) **NULL** created_at **TIMESTAMPTZ** **DEFAULT** **NOW**()

---

Part 8 — Transaction Types

We only need three fundamental types:

**EXPENSE** **INCOME** **TRANSFER**

Expense

Example:

Coffee ₹20

Database:

type = **EXPENSE** amount = 20 wallet = **UPI** item = Coffee

---

Income

Example:

Money received ₹**150**

Database:

type = **INCOME** amount = **150** wallet = **UPI**

No expense item is required.

---

Transfer

Example:

**UPI** → Savings ₹30

Database:

type = **TRANSFER** amount = 30

The source and destination wallets are stored separately.

---

Part 9 — transaction_transfers

Transfers need two wallets.

Therefore:

transactions
    │
    │ 1:1
    ▼
transaction_transfers

Table

### Column Type

transaction_id **BIGINT** PK/FK from_wallet_id **BIGINT** FK to_wallet_id **BIGINT** FK

Example:

Transaction
**TXN000004**
₹30
**TRANSFER**
    │
    ▼
From: **UPI**
To: Savings

Constraint:

from_wallet_id <> to_wallet_id

---

Part 10 — How Savings Is Detected

We don't need a separate savings_transactions table.

The database can determine it.

transaction_type = **TRANSFER**
        +
destination wallet_type = **SAVINGS**
        ↓
**SAVING**

Similarly:

transaction_type = **TRANSFER**
        +
source wallet_type = **SAVINGS**
        ↓
**WITHDRAWAL**

Otherwise:

**TRANSFER**

is simply a normal internal transfer.

This keeps the model clean.

---

Part 11 — Food Transaction Example

Suppose you buy:

Egg dosa ₹60 Lunch

The database could contain:

items

name = Egg Dosa category = Food subcategory = Dosa is_food = true

food_details

food_group = **MEAL** health_class = **NEUTRAL** is_sugary = false

transactions

date = **2026**-08-23 time = 13:10 type = **EXPENSE** amount = 60 wallet = **UPI** item = Egg Dosa meal = **LUNCH**

Now **SQL** can answer:

How much did I spend on lunch?

How much did I spend on dosa?

How much did I spend on food?

How much did I spend on junk food?

How much did I spend on sugary food?

etc.

---

Part 12 — Your Item Structure

Your previously supplied items can now be organized approximately like this:

**FOOD**
│
├── Meals
│ ├── Idly
│ ├── Dosa
│ │ ├── Normal
│ │ ├── Egg Dosa
│ │ ├── Onion Dosa
│ │ ├── Podi Dosa
│ │ └── Special Dosa
│ ├── Poori
│ ├── Pongal
│ ├── Tomato Rice
│ ├── Lemon Rice
│ ├── Brinji
│ ├── Chapati
│ ├── Parotta
│ └── Fried Rice
│
├── Snacks
│ ├── Bun
│ │ ├── Normal
│ │ ├── Jam Bun
│ │ ├── Cream Bun
│ │ ├── Paalkova Bun
│ │ └── Honey Bun
│ ├── Puffs
│ │ ├── Veg
│ │ ├── Egg
│ │ ├── Chicken
│ │ ├── Mushroom
│ │ └── Paneer
│ ├── Vada
│ └── Bhajji
│
├── Drinks
│ ├── Tea
│ ├── Coffee
│ ├── Black Tea
│ ├── Sukku Malli Coffee
│ ├── Boost
│ ├── Horlicks
│ ├── Badam Milk
│ └── Cool Drink
│
├── Fruits
│ └── Typable
│
└── Vegetables
    └── Typable

And then:

**TRANSPORT** **HOUSEHOLD** **PERSONAL** **CARE** **EDUCATION** **MEDICAL** **RELIGIOUS** **FINANCIAL** **MISCELLANEOUS**

with their respective items.

We should not create a separate database table for every item type. That's exactly the complexity we're trying to avoid.

---

Part 13 — mab_entries

Because you specifically decided that **MAB** is something you manually observe from your bank/app at night, it should remain manual.

Table

### Column Type

id **BIGSERIAL** PK mab_date **DATE** **UNIQUE** mab_value **NUMERIC**(12,2) notes **TEXT** created_at **TIMESTAMPTZ**

So every night:

Date: **2026**-08-23 **MAB**: ₹1,**720**

You enter it manually.

The system can then calculate:

Monthly Average **MAB** Highest **MAB** Lowest **MAB** **MAB** change **MAB** completeness

But it never calculates your **MAB** and pretends that is the actual bank **MAB**.

---

Part 14 — Relationships

The basic ER structure becomes:

┌──────────────┐
    │ categories │
    └──────┬───────┘
    │
    │
    ┌──────▼───────┐
    │ items │
    └──────┬───────┘
    │
    ┌─────▼──────┐
    │food_details│
    └────────────┘

┌─────────────┐
│ wallets │
└──────┬──────┘
    │
    │
    ▼
┌─────────────────┐
│ transactions │
└──────┬──────────┘
    │
    │
    ▼
┌────────────────────────┐
│ transaction_transfers │
└──────────┬─────────────┘
    │
    └──────► wallets

┌──────────────┐ │ mab_entries │ └──────────────┘

And:

categories
    1
    │
    │
    N
    items
    1
    │
    │
    0..1
food_details

wallets
    1
    │
    │
    N
transactions

items
    1
    │
    │
    N
transactions

---

Part 15 — One Important Design Decision

I recommend not storing calculated balance inside every transaction.

For example, don't do:

transaction ₹20 expense balance_after = ₹1,**450**

That creates duplicated financial state.

Instead:

Transactions
      ↓
**SQL** calculation
      ↓
Wallet balance

The database remains the source of truth.

---

Part 16 — What We Have Now

Our core model is therefore:

PostgreSQL
    │
    ┌───────────┼────────────┐
    │ │ │
    categories wallets mab_entries
    │ │
    ▼ ▼
    items transactions
    │ │
    ▼ ▼
    food_details transfers

And above PostgreSQL:

Django
    │
    ┌──────────────┼───────────────┐
    │ │ │
    ▼ ▼ ▼
    Transaction Dashboard **SQL** Playground
    UI
    │
    ▼
    PostgreSQL
    │
    ▼
    Result
    │
    ▼
    UI

Next: freeze the schema before coding

Before we write Django models, the next thing I would do is produce the complete data dictionary for these tables:

1. wallets
2. categories
3. items
4. food_details
5. transactions
6. transaction_transfers
7. mab_entries

For every single column, we'll define:

exact column name

PostgreSQL datatype

**NULL** / **NOT** **NULL**

**DEFAULT**

PK/FK

**UNIQUE**

**CHECK** constraints

allowed values

example value

why the column exists

how it connects to other tables

That will become our final database blueprint before we touch Django code.Final Database Data Dictionary

We’ll freeze this as the first database blueprint. I’m keeping it simple and avoiding unnecessary tables.

One small refinement from the previous design: for flexible items such as soap name, shampoo name, fruit name, vegetable name, cool drink type, etc., we will use the items table rather than creating separate tables.

---

1. wallets

Stores every place where your money exists.

### Column Type Constraints Example

id **BIGSERIAL** PK 1 name **VARCHAR**(**100**) **NOT** **NULL**, **UNIQUE** **UPI** wallet_type **VARCHAR**(30) **NOT** **NULL** **UPI** opening_balance **NUMERIC**(12,2) **NOT** **NULL**, ≥ 0 **1000**.00 is_active **BOOLEAN** **NOT** **NULL**, **DEFAULT** **TRUE** **TRUE** created_at **TIMESTAMPTZ** **NOT** **NULL**, **DEFAULT** **NOW**() —

Allowed wallet_type

**CASH** **UPI** **BANK** **SAVINGS** TRAVEL_CARD **OTHER**

Example:

1 | Cash | **CASH** | **100**.00 2 | **UPI** | **UPI** | **620**.00 3 | Savings | **SAVINGS** | **1000**.00 4 | Travel Card | TRAVEL_CARD | 50.00

Important rule

A wallet with:

wallet_type = **SAVINGS**

is automatically recognized by the application as a savings wallet.

No separate savings-wallet list is required.

---

2. categories

Stores broad expense classifications.

### Column Type Constraints Example

id **BIGSERIAL** PK 1 name **VARCHAR**(**100**) **NOT** **NULL**, **UNIQUE** Food is_active **BOOLEAN** **DEFAULT** **TRUE** **TRUE** created_at **TIMESTAMPTZ** **DEFAULT** **NOW**() —

Initial categories

Food Transport Household ### Personal Care Education Medical Religious Financial Entertainment Miscellaneous

We can add/remove categories later.

---

3. items

This is the master list of things you actually spend money on.

### Column Type Constraints Example

id **BIGSERIAL** PK 1 name **VARCHAR**(**150**) **NOT** **NULL** Coffee category_id **BIGINT** FK → categories.id 1 subcategory **VARCHAR**(**100**) **NULL** Drinks is_food **BOOLEAN** **NOT** **NULL**, **DEFAULT** **FALSE** **TRUE** is_variable_name **BOOLEAN** **NOT** **NULL**, **DEFAULT** **FALSE** **FALSE** is_active **BOOLEAN** **DEFAULT** **TRUE** **TRUE** created_at **TIMESTAMPTZ** **DEFAULT** **NOW**() —

Why is_variable_name?

Some things shouldn't have a fixed predefined item list.

For example:

Fruit → Banana Fruit → Apple Fruit → Orange

Rather than creating hundreds of fruit master records, the UI can allow a custom item.

Similarly:

Soap → Lux Soap → Dove Soap → Pears

The item name can be typed.

---

4. food_details

Only food items need this additional information.

### Column Type Constraints Example

item_id **BIGINT** PK + FK → items.id 10 food_group **VARCHAR**(30) **NOT** **NULL** **SNACK** health_class **VARCHAR**(20) **NOT** **NULL** **JUNK** is_sugary **BOOLEAN** **NOT** **NULL** **TRUE**

food_group

**MEAL** **SNACK** **DRINK** **FRUIT** **VEGETABLE**

health_class

**HEALTHY** **JUNK** **NEUTRAL**

Example

Coffee

item: Coffee

food_details: food_group = **DRINK** health_class = **NEUTRAL** is_sugary = **TRUE**

Carrot

item: Carrot

food_details: food_group = **VEGETABLE** health_class = **HEALTHY** is_sugary = **FALSE**

Puffs

item: ### Chicken Puffs

food_details: food_group = **SNACK** health_class = **JUNK** is_sugary = **FALSE**

---

5. transactions

This is the most important table in the entire system.

Every financial event is recorded here.

### Column Type Constraints Example

id **BIGSERIAL** PK 1 transaction_id **VARCHAR**(30) **UNIQUE**, **NOT** **NULL** **TXN000001** transaction_date **DATE** **NOT** **NULL** **2026**-08-23 transaction_time **TIME** **NULL** 08:30:00 transaction_type **VARCHAR**(20) **NOT** **NULL** **EXPENSE** amount **NUMERIC**(12,2) **NOT** **NULL**, > 0 30.00 wallet_id **BIGINT** FK → wallets.id 2 item_id **BIGINT** FK → items.id, **NULL** 15 meal **VARCHAR**(20) **NULL** **BREAKFAST** description **TEXT** **NULL** Morning coffee created_at **TIMESTAMPTZ** **DEFAULT** **NOW**() — updated_at **TIMESTAMPTZ** **DEFAULT** **NOW**() —

---

6. transaction_type

Only three fundamental transaction types:

**EXPENSE** **INCOME** **TRANSFER**

**EXPENSE**

Example:

Coffee ₹20 **UPI** **EXPENSE**

**INCOME**

Example:

Money received ₹**150** **UPI** **INCOME**

**TRANSFER**

Example:

₹30 **UPI** → Savings **TRANSFER**

---

7. meal

Only relevant to food transactions.

Allowed values:

**BREAKFAST** **LUNCH** **DINNER** **SNACK** **OTHER**

This is intentionally stored on the transaction, not the item.

Why?

Because:

Egg

could be:

Breakfast today Lunch tomorrow Dinner another day

The item doesn't change; the consumption context does.

---

## Transfer Details

A transfer requires two wallets.

Therefore we use:

transaction_transfers

### Column Type Constraints Example

transaction_id **BIGINT** PK + FK → transactions.id 4 from_wallet_id **BIGINT** FK → wallets.id 2 to_wallet_id **BIGINT** FK → wallets.id 3

Constraint:

from_wallet_id <> to_wallet_id

Example:

transactions

**TXN000004** **TRANSFER** ₹30

and:

transaction_transfers

transaction_id = 4 from_wallet_id = 2 -- **UPI** to_wallet_id = 3 -- Savings

---

## How the Application Detects Expense

This is an important requirement you established.

You don't want to manually specify:

> *Is this an expense?*

for every ordinary purchase.

The application can use this rule:

If transaction_type = **EXPENSE**
        → Expense

If transaction_type = **INCOME**
        → Income

If transaction_type = **TRANSFER**
        → Transfer

The UI can therefore make Expense the default transaction type.

So when you enter:

Coffee ₹20 **UPI**

the application can default to:

**EXPENSE**

You only change it when you're recording income or a transfer.

---

## How Savings Detection Works

No separate savings transaction table.

The application determines it from the transfer.

Saving

transaction_type = **TRANSFER** **AND** to_wallet.wallet_type = **SAVINGS**

Therefore:

**UPI** → Savings ₹30

becomes:

Saving = ₹30

Withdrawal

transaction_type = **TRANSFER** **AND** from_wallet.wallet_type = **SAVINGS**

Therefore:

Savings → **UPI** ₹**100**

becomes:

Withdrawal = ₹**100**

Normal transfer

Cash → **UPI**

Neither wallet is a savings wallet:

Saving = No Withdrawal = No

---

11. mab_entries

Your **MAB** is manually observed from your bank/app.

Therefore:

### Column Type Constraints

id **BIGSERIAL** PK mab_date **DATE** **UNIQUE**, **NOT** **NULL** mab_value **NUMERIC**(12,2) **NOT** **NULL**, ≥ 0 notes **TEXT** **NULL** created_at **TIMESTAMPTZ** **DEFAULT** **NOW**()

Example:

**2026**-08-23 | ₹**1720** **2026**-08-24 | ₹**1680** **2026**-08-25 | ₹**1800**

The system can calculate:

Average **MAB** Highest **MAB** Lowest **MAB** **MAB** change Monthly **MAB** **MAB** completeness

But it will not manufacture **MAB** values from transactions.

---

## Complete Relationship Map

┌─────────────────┐
    │ categories │
    │─────────────────│
    │ id PK │
    │ name │
    └────────┬────────┘
    │
    │ 1:N
    ▼
    ┌─────────────────┐
    │ items │
    │─────────────────│
    │ id PK │
    │ name │
    │ category_id FK │
    │ subcategory │
    │ is_food │
    └────────┬────────┘
    │
    │ 1:0..1
    ▼
    ┌─────────────────┐
    │ food_details │
    │─────────────────│
    │ item_id PK/FK │
    │ food_group │
    │ health_class │
    │ is_sugary │
    └─────────────────┘

┌─────────────────┐
│ wallets │
│─────────────────│
│ id PK │
│ name │
│ wallet_type │
│ opening_balance │
└────────┬────────┘
    │
    │ 1:N
    ▼
┌────────────────────────┐
│ transactions │
│────────────────────────│
│ id PK │
│ transaction_id **UNIQUE** │
│ transaction_date │
│ transaction_time │
│ transaction_type │
│ amount │
│ wallet_id FK │
│ item_id FK │
│ meal │
│ description │
└───────────┬────────────┘
    │
    │ 1:0..1
    ▼
┌────────────────────────────┐
│ transaction_transfers │
│────────────────────────────│
│ transaction_id PK/FK │
│ from_wallet_id FK │
│ to_wallet_id FK │
└────────────────────────────┘

┌─────────────────┐ │ mab_entries │ │─────────────────│ │ id PK │ │ mab_date **UNIQUE** │ │ mab_value │ │ notes │ └─────────────────┘

---

## Example: Your Actual Data

Suppose today you enter:

Coffee ₹20 from **UPI**

transactions

**TXN000001** **2026**-08-23 08:30 **EXPENSE** 20 **UPI** Coffee **BREAKFAST**

Then:

₹30 **UPI** → Savings

transactions

**TXN000002** **2026**-08-23 **TRANSFER** 30 **UPI**

and:

transaction_transfers

**TXN000002** **UPI** Savings

Then:

₹**150** received

transactions

**TXN000003** **2026**-08-23 **INCOME** **150** **UPI**

Your database now has three financial events.

The **SQL** layer can derive:

Income = ₹**150** Expense = ₹20 Transfer = ₹30 Saving = ₹30 Net spending = ₹20

---

## One Important Thing We Still Need to Decide

Before creating the Django models, there is one area I don't want to guess:

Your complete item hierarchy.

For example, you gave:

Dosa ├── Egg Dosa ├── Onion Dosa ├── Podi Dosa ├── Normal └── Special

But we need to decide whether:

Dosa

is itself an item and the variants are sub-items, or whether:

### Egg Dosa

### Onion Dosa ### Podi Dosa ### Normal Dosa ### Special Dosa

are simply individual items.

The same issue exists for:

Bun Puffs Vada Bhajji Detergent Soap Shampoo Medicine Bus

I recommend we settle this item-master structure next, along with the exact category/subcategory hierarchy. Once that is frozen, the PostgreSQL schema can be converted directly into Django models without repeatedly redesigning it.Yes. We can continue from the point where we had reached: the requirements are being defined first, before writing Django code or creating the database.

For the **SQL** Playground/UI architecture, the next part should be the actual functional specification—what happens when you type a query, execute it, get an error, inspect tables, and navigate relationships.

Part 4 — **SQL** Playground Functional Specification

## SQL Editor

The application should have a dedicated **SQL** Playground page.

Main layout:

┌─────────────────────────────────────────────────────────────┐ │ **SQL** **PLAYGROUND** │ ├─────────────────────────────────────────────────────────────┤ │ │ │ Query Editor │ │ ┌───────────────────────────────────────────────────────┐ │ │ │ **SELECT** category, **SUM**(amount) │ │ │ │ **FROM** transactions │ │ │ │ **WHERE** type = '**EXPENSE**' │ │ │ │ **GROUP** BY category; │ │ │ └───────────────────────────────────────────────────────┘ │ │ │ │ [Run Query] [Clear] [Format] │ │ │ ├─────────────────────────────────────────────────────────────┤ │ Result │ │ │ │ category total_spent │ │ Food ₹2,**450** │ │ Transport ₹1,**280** │ │ Personal ₹**750** │ │ │ └─────────────────────────────────────────────────────────────┘

The user should be able to write real PostgreSQL **SQL**.

For example:

**SELECT** **SUM**(amount) **FROM** transactions **WHERE** type = '**EXPENSE**';

The application sends the query to the Django backend.

Django executes it against PostgreSQL and returns the result to the UI.

---

## Query Execution Flow

The architecture should be:

User ↓ **SQL** Editor ↓ React / Frontend ↓ Django **API** ↓ PostgreSQL ↓ ### Query Result ↓ Django **API** ↓ Frontend ↓ ### Result Table

For example:

**SELECT**
    item_name,
    **SUM**(amount) AS total_spent
**FROM** transactions
**WHERE** type = '**EXPENSE**'
**GROUP** BY item_name
**ORDER** BY total_spent **DESC**;

The backend executes it.

The frontend receives something conceptually like:

{
    *success*: true,
    *columns*: [
    *item_name*,
    *total_spent*
    ],
    *rows*: [
    [*coffee*, **450**],
    [*tea*, **320**],
    [*idly*, **280**]
    ]
}

The UI converts that into a table.

---

## SQL Error Display

Errors should not disappear into the browser console.

They should appear directly underneath the editor.

For example:

┌──────────────────────────────────────────┐ │ **ERROR** │ ├──────────────────────────────────────────┤ │ column *ammount* does not exist │ │ │ │ **LINE** 1: **SELECT** ammount **FROM** transactions │ │ ^ │ └──────────────────────────────────────────┘

This is particularly important because you are using this application to practice **SQL**.

The actual PostgreSQL error should be presented in a readable way.

For example:

**ERROR**: column *ammount* does not exist **HINT**: Perhaps you meant to reference the column *amount*.

This makes the application function as a real **SQL** practice environment, not merely an expense application.

---

## Query History

Every successfully executed query should optionally be recorded.

Example:

**QUERY** **HISTORY**

## Total expenses

    **SELECT** **SUM**(amount)...
    10:42 AM

## Coffee spending

    **SELECT** **SUM**(amount)...
    10:38 AM

## Monthly expenses

    **SELECT** DATE_TRUNC...
    10:31 AM

Clicking a previous query should load it back into the editor.

This will be extremely useful for your **SQL** practice.

---

## Saved Queries

There should be a separate concept from history:

### Query History

Automatically generated.

### Saved Queries

Explicitly saved by you.

Example:

### Saved Queries

📁 Food Analysis
    • Coffee spending
    • Tea spending
    • Junk food spending
    • Healthy food spending

📁 Transport
    • Monthly transport
    • Bus spending
    • Metro spending

📁 General Finance
    • Total expenses
    • Monthly income
    • Savings

You can therefore build your own personal collection of **SQL** problems/solutions.

---

## Result Controls

The result area should support:

[Table] [**JSON**] [**CSV**]

Table

Normal readable result.

**JSON**

Useful for understanding what the **API** actually returned.

**CSV**

Useful if you want to export query results.

For large results:

Showing 1–50 of **327** rows

[Previous] [Next]

The backend should preferably limit results rather than loading thousands of rows into the browser unnecessarily.

---

## Database Explorer

There should be another section/page called:

### Database Explorer

This answers:

> *What tables do I have?*

Example:

**DATABASE** │ ├── transactions ├── items ├── food_attributes ├── categories ├── wallets ├── people └── ...

Click:

transactions

and show:

transactions

### Column Type

──────────────────────────── id **BIGINT** transaction_date **DATE** transaction_time **TIME** amount **NUMERIC** wallet_id **BIGINT** item_id **BIGINT** transaction_type **VARCHAR** description **TEXT**

---

## Table Data Viewer

Clicking a table should allow:

transactions

┌────┬────────────┬────────┬─────────┬──────────┐ │ ID │ Date │ Amount │ Type │ Wallet │ ├────┼────────────┼────────┼─────────┼──────────┤ │ 1 │ **2026**-08-23 │ 30 │ **EXPENSE** │ **UPI** │ │ 2 │ **2026**-08-23 │ **150** │ **INCOME** │ **UPI** │ └────┴────────────┴────────┴─────────┴──────────┘

This should be read-only initially.

Your normal transaction entry should happen through the application's proper UI, not by directly editing database tables.

---

## Database Relationship Map

This is the visual *map* you mentioned.

A dedicated page:

### Database Schema

Something like:

┌──────────────┐
    │ categories │
    └──────┬───────┘
    │
    │
┌──────────────┐ ┌────▼─────────┐ ┌──────────────┐
│ wallets │───│ transactions │───│ items │
└──────────────┘ └────┬─────────┘ └──────────────┘
    │
    │
    ┌──────▼───────┐
    │ people │
    └──────────────┘

Clicking a relationship should explain:

transactions.wallet_id
        ↓
wallets.id

Relationship: Many Transactions → One Wallet

So you can visually understand:

Primary key

Foreign key

One-to-many relationships

Which table depends on which

Which columns connect tables

This is particularly valuable for learning **SQL** JOINs.

---

## Schema Details

Clicking a table should also show:

Columns

id **BIGINT** PK wallet_id **BIGINT** FK → wallets.id amount **NUMERIC** transaction_date **DATE**

Constraints

**PRIMARY** **KEY** **FOREIGN** **KEY** **NOT** **NULL** **UNIQUE** **CHECK**

Relationships

Referenced by:
    transactions.wallet_id

References:
    wallets.id

This gives you the information needed to construct **JOIN** queries yourself.

---

## SQL Learning Assistance

I would not automatically generate **SQL** for every question, because one of your goals is to practice writing **SQL** yourself.

Instead, the **SQL** Playground can have:

**SQL** Practice Mode

You type:

> Find how much I spent on coffee every week.

Then you write the query yourself.

The system executes it.

If it works:

✓ Query executed successfully

If it fails:

✗ PostgreSQL Error column *week* does not exist

This gives you genuine **SQL** practice.

Later, we can optionally add:

[Explain Query]

which explains what your query is doing rather than simply replacing it with another query.

---

## Finance Application UI

Separate from the **SQL** Playground, we need the actual everyday interface.

Something like:

Dashboard Transactions ### Add Transaction Wallets Items Categories Savings Reports **SQL** Playground ### Database Explorer Settings

The important architectural distinction is:

**APPLICATION**
    │
    ┌───────────┴───────────┐
    │ │
    Normal Finance UI **SQL** Playground
    │ │
    │ │
    └───────────┬───────────┘
    ↓
    PostgreSQL

Both ultimately work with the same database.

There should not be a separate database for the **SQL** Playground.

---

## Phone → Laptop Synchronization

This is one of the major advantages of using Django + PostgreSQL.

If the application is deployed to a cloud server:

**INTERNET**
    │
    ┌─────────┴─────────┐
    │ │
    **PHONE** **LAPTOP**
    │ │
    └─────────┬─────────┘
    ↓
    **DJANGO** **SERVER**
    ↓
    **POSTGRESQL**

You enter:

₹30 Coffee

from your phone.

It gets stored in the cloud PostgreSQL database.

Then you open the application on your laptop.

The same transaction is already there.

No Excel-file synchronization problem.

No copying files between devices.

---

## Most Important Architectural Rule

We should establish this before writing code:

> PostgreSQL is the single source of truth.

Everything else is an interface or analytical layer.

PostgreSQL
    **SINGLE** **TRUTH**
    │
    ┌─────────────┼─────────────┐
    ↓ ↓ ↓
 Finance UI **SQL** Playground Reports
    ↓ ↓ ↓
    └─────────────┼─────────────┘
    ↓
    User

The Dashboard should not become another database.

The **SQL** Playground should not become another database.

Reports should not store duplicate financial records.

Everything reads from the same underlying relational model.

---

And this is where we should stop and define the database properly

You were right earlier: we shouldn't jump into Phase 1, Phase 2, Phase 3... without having a solid specification.

Before Django implementation, I recommend we settle these in order:

## Items & categories — your large food/non-food list

## Food classification model — breakfast/lunch/dinner/snack, healthy/junk, sugary, etc.

## Wallet model

## Transaction model

## Transfer model

## Savings model

## Other attributes — people, payment methods, recurring, etc.

## Relationships / ER model

## Exact PostgreSQL tables + columns + data types

## Django models

## Application pages

## SQL Playground

## Database Explorer / relationship map

## Cloud deployment architecture

Only after these are settled should we start building.

That will give us a much cleaner system than trying to reproduce the old spreadsheet phase-by-phase.

---

## Final completion notes

The following items were completed in the working project:

- Phase 0: project setup and environment alignment complete
- Phase 1: Django + PostgreSQL project structure and configuration complete
- Phase 2: wallet and accounting model implemented with spendable/savings behavior
- Phase 3: deposit, expense, transfer, and allocation flows built and validated
- Phase 4: transactions, categories, items, reports, and dashboard workflows implemented
- Phase 5: product-style frontend shell with sidebar, navbar, theme toggle, and responsive layout complete
- Phase 6: SQL playground built with read-only PostgreSQL execution, schema explorer, saved queries, and query history
- Phase 7: API documentation and working documentation created
- Phase 8: real-data verification passed for deposits, expenses, storage, SQL execution, and phone-width layout checks

Completed functional checks:
- account creation works
- deposit flow correctly splits between spendable and savings
- expense logic deducted from the selected allocation
- transfer between spendable and savings preserves total balance
- SQL queries execute against the live database in a safe read-only mode
- the dashboard and SQL playground render correctly on small/mobile viewport widths
- documentation in plan.md, a.md, working.md, and api_docs.md reflects the project state

This means the project has reached the implemented and validated stage for the requested finance app and SQL learning environment.

---

## Family Finance Phase Plan (to execute one by one)

The earlier generic wallet build is still valid as a base product, but it must now be corrected to match the family-money model described in the requirements document. The next work must be done in a strict phase order, without skipping ahead.

### Phase A — Finalize the money model and ownership rules
- Define each owner: Me, Appa, Amma
- Define money locations: TMB Bank, Appa Cash, Amma Cash
- Define allocation types: Spendable and Savings
- Confirm the rule: Savings is an allocation, not a separate physical wallet
- Confirm that a spending event defaults to the current user unless an owner is explicitly chosen
- Confirm how own money is reduced when an expense is assigned to Appa or Amma
- Add a money-pool/source model so every amount can be traced to owner + location + allocation

### Phase B — Rework transactions around source tracking
- Store transaction source owner, source location, and allocation
- Keep Expense as the default type for actual spending
- Keep Transfer as a separate movement when money shifts without spending
- Keep Income as an explicit incoming cash event
- Ensure every transaction can explain which pool gained or lost money

### Phase C — Correct savings behavior and internal transfers
- Treat Spendable → Savings as a reclassification of the same money, not a real bank account transfer
- Keep total balance at the location unchanged while changing allocation split
- Record savings movement separately from expense
- Define the rules for moving Savings back to Spendable
- Track the source pool so the app knows which owner and location the savings belongs to

### Phase D — Finalize category, subtype, and item taxonomy
- Create the master categories: Food, Transport, Personal Care, Household, Education, Medical, Religious, Bank Charges, Miscellaneous
- Add subtype support under each category
- Add item support under each subtype
- Allow custom items for unexpected or one-off spends
- Keep generic entry flexible without forcing every item to exist in a master list

### Phase E — Add the food-specific model and attributes
- Add food type: Food or Drink
- Add meal: Breakfast, Lunch, Dinner, Snack, Other
- Add health classification: Healthy, Neutral, Junk, Unclassified
- Add sugary flag: Yes, No, Unknown
- Add food item variants such as Dosa variations and bun variations
- Support one transaction containing multiple food items with quantities
- Keep meal as a transaction/event attribute, not as a permanent property of the food item itself

### Phase F — Add family cash and wallet selection to the UI
- Add owner selector in the transaction form
- Add location selector: bank or cash
- Add allocation selector: Spendable or Savings
- Default to Me + TMB + Spendable unless the user picks something else
- Support transactions such as Amma cash expense, Appa cash expense, Me savings allocation, and transfer between allocations

### Phase G — Correct the database schema to the true business model
- Create models for owner, money location, allocation, money pool, transaction, category, subtype, item, custom item, food event, and food event item
- Add constraints to protect source consistency and prevent invalid allocations
- Normalize the schema so it matches the real family finance data model
- Keep PostgreSQL as the single source of truth

### Phase H — Rebuild the product UI around the corrected model
- Dashboard cards for total, spendable, savings, owner split, and month flow
- Expense form with category, subtype, item, custom item, owner, location, and allocation selectors
- Transaction list filters by owner, location, category, subtype, and allocation
- Reports page for family breakdown and savings tracking
- Settings page for defaults and theme controls

### Phase I — Data validation with real examples
- Create sample data for Me, Appa, and Amma across TMB, Appa Cash, and Amma Cash
- Validate expense deduction, savings allocation, and owner-specific reductions
- Verify transfers between spendable and savings do not alter total balance at the same location
- Check data rendering in the UI and underlying PostgreSQL tables
- Confirm the SQL Playground still queries the correct live data

### Phase J — Optional hardening and future improvements
- Login and user-level permissions
- Goal-based savings tracking
- Reports and charts
- CSV/export support
- Advanced SQL practice environment

Execution order: Phase A first, then Phase B, and so on. Do not skip ahead. The current generic wallet app should remain as the base, but the family finance model must be integrated before the system is considered complete.

### Completion notes
- Phase A to F were implemented and validated in the Django app.
- The family finance model now includes owner, money location, money pool, and allocation-aware transactions.
- The SQL playground, reports, and taxonomy work have been verified against the real database.
- Latest UI finish: light-theme sidebar contrast and hover states were corrected for readability.
