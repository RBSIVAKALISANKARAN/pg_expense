from decimal import Decimal
from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import Client, TransactionTestCase
from django.urls import reverse

from .financial_integrity import ensure_account_money_pool
from .models import (Account, Allocation, AllocationType, Transaction,
                     TransactionType)


class ConcurrentMutationConsistencyTests(TransactionTestCase):
    reset_sequences = True

    def _seed_account(self, name, amount="1000.00"):
        account = Account.objects.get(name=name)
        allocation = Allocation.objects.get(
            account=account, type=AllocationType.SPENDABLE
        )
        allocation.balance = Decimal(amount)
        allocation.save(update_fields=["balance"])
        account.total_balance = Decimal(amount)
        account.save(update_fields=["total_balance"])
        owner = account.money_pools.first().owner
        pool = ensure_account_money_pool(
            account, owner, account.money_location, AllocationType.SPENDABLE
        )
        pool.current_amount = Decimal(amount)
        pool.save(update_fields=["current_amount"])
        return account

    def test_concurrent_deposits_preserve_account_allocation_and_pool_totals(self):
        account = self._seed_account("rbsankaran_acc", "1000.00")
        barrier = Barrier(2)
        results = []

        def deposit():
            close_old_connections()
            try:
                client = Client()
                barrier.wait(timeout=10)
                response = client.post(
                    reverse("account-deposit", args=[account.id]),
                    {"amount": "700"},
                    content_type="application/json",
                )
                results.append(response.status_code)
            finally:
                close_old_connections()

        threads = [Thread(target=deposit), Thread(target=deposit)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertFalse(
            any(thread.is_alive() for thread in threads),
            "Concurrent deposit did not complete.",
        )
        self.assertEqual(sorted(results), [200, 200])

        account.refresh_from_db()
        spendable = Allocation.objects.get(
            account=account, type=AllocationType.SPENDABLE
        )
        savings = Allocation.objects.get(account=account, type=AllocationType.SAVINGS)
        pool = ensure_account_money_pool(
            account,
            account.money_pools.first().owner,
            account.money_location,
            AllocationType.SPENDABLE,
        )
        self.assertEqual(account.total_balance, Decimal("2400.00"))
        self.assertEqual(spendable.balance + savings.balance, Decimal("2400.00"))
        self.assertEqual(pool.current_amount, spendable.balance)
        self.assertEqual(
            Transaction.objects.filter(
                account=account, type=TransactionType.DEPOSIT
            ).count(),
            2,
        )

    def test_concurrent_allocation_transfers_preserve_total_balance_and_pool_totals(
        self,
    ):
        account = self._seed_account("rbsankaran_acc", "1000.00")
        barrier = Barrier(2)
        results = []

        def allocate(from_type, to_type):
            close_old_connections()
            try:
                client = Client()
                barrier.wait(timeout=10)
                response = client.post(
                    reverse("account-allocate", args=[account.id]),
                    {"from_type": from_type, "to_type": to_type, "amount": "600"},
                    content_type="application/json",
                )
                results.append(response.status_code)
            finally:
                close_old_connections()

        threads = [
            Thread(
                target=allocate, args=(AllocationType.SPENDABLE, AllocationType.SAVINGS)
            ),
            Thread(
                target=allocate, args=(AllocationType.SAVINGS, AllocationType.SPENDABLE)
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertFalse(
            any(thread.is_alive() for thread in threads),
            "Concurrent allocation transfer did not complete.",
        )
        # Two opposite transfers of 600 cannot both succeed from the initial
        # state: one necessarily hits the 600-spendable limit after the first
        # committed transfer.
        self.assertEqual(sorted(results), [200, 400])

        account.refresh_from_db()
        spendable = Allocation.objects.get(
            account=account, type=AllocationType.SPENDABLE
        )
        savings = Allocation.objects.get(account=account, type=AllocationType.SAVINGS)
        self.assertEqual(account.total_balance, Decimal("1000.00"))
        self.assertEqual(spendable.balance + savings.balance, Decimal("1000.00"))
        self.assertEqual(
            Transaction.objects.filter(
                account=account, type=TransactionType.ALLOCATION
            ).count(),
            1,
        )
