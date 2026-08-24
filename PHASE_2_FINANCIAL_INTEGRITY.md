# Phase 2 — Financial Integrity & Data Safety

## Scope

Phase 2 hardens the money engine without redesigning the existing financial model.

### Implemented

- MoneyPool identity is account-scoped at the database level.
- Owner + money location + allocation may be reused by different accounts without sharing balances.
- Existing financial operations continue to run inside `transaction.atomic()` and lock the affected account/allocation rows with `select_for_update()`.
- MoneyPool lookups used by the existing endpoints are routed through an account-scoped integrity service.
- Savings/spendable movements continue to preserve total account balance.
- Expense/revert flows continue to reconcile account, allocation, and MoneyPool balances.
- Regression coverage added for account isolation, savings/spendable transfers, expense/revert, insufficient funds, and concurrent overspending.

## Critical invariant

For every account:

`Account.total_balance == sum(Allocation.balance) == sum(Account.money_pools.current_amount)`

A transaction must update the affected account, allocation, money pool, and transaction ledger atomically.

## Migration

`0018_restore_account_scoped_money_pool_identity.py` replaces the previous global `(owner, location, allocation_type)` uniqueness rule with `(account, owner, location, allocation_type)`.

This is required because account balances are independently reconciled. Two accounts using the same owner and physical money location must not share a MoneyPool balance.

## Verification required

Run:

```powershell
python manage.py test
```

The expected suite size after the Phase 2 regression tests is 51 tests, assuming the existing 46-test baseline remains unchanged.

Phase 2 should not be marked complete until the full suite passes and the migration applies successfully on a clean test database.
