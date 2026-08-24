# Phase 5 — Savings Tracking & Savings Analytics Foundation

## Source of truth
Savings analytics are derived from `Transaction` rows, not from a separate savings ledger. This prevents a second source of truth and keeps savings reporting aligned with the financial transaction history.

## Savings movements
- Deposit allocated to the Savings allocation → savings inflow.
- Transfer with `direction=to_savings` → savings inflow.
- Allocation with `to=savings` → savings inflow.
- Transfer with `direction=to_spendable` → savings withdrawal/outflow.
- Allocation with `from=savings` → savings outflow.
- Expense charged to the Savings allocation → savings outflow.

Each transaction is classified once, so the same movement is not counted twice.

## Analytics
`GET /api/savings/analytics/` provides:
- total savings inflow
- total savings outflow
- cumulative net savings movement
- savings rate against deposits in the selected period
- savings activity ledger
- movement-type analysis
- wallet/source analysis
- money-location analysis
- monthly period summaries
- optional `date_from` and `date_to` filters

The endpoint requires an authenticated session.

## UI
`/api/savings/page/` provides period filtering, overview cards, monthly summaries, wallet analysis, movement analysis, and the transaction-based savings activity ledger.

## No schema change
Phase 5 uses the existing Allocation and Transaction models. No migration is required.
