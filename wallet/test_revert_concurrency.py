from decimal import Decimal
from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import Client, TransactionTestCase
from django.urls import reverse

from .financial_integrity import ensure_account_money_pool
from .models import (Account, Allocation, AllocationType, Transaction,
                     TransactionType)


class ConcurrentTransactionRevertTests(TransactionTestCase):
    reset_sequences = True

    def test_opposite_transfer_reverts_do_not_deadlock(self):
        source = Account.objects.get(name="rbsankaran_acc")
        destination = Account.objects.get(name="Travel Card")
        owner = source.money_pools.first().owner

        for account in (source, destination):
            allocation = Allocation.objects.get(
                account=account, type=AllocationType.SPENDABLE
            )
            allocation.balance = Decimal("1000.00")
            allocation.save(update_fields=["balance"])
            account.total_balance = Decimal("1000.00")
            account.save(update_fields=["total_balance"])
            pool = ensure_account_money_pool(
                account, owner, account.money_location, AllocationType.SPENDABLE
            )
            pool.current_amount = Decimal("1000.00")
            pool.save(update_fields=["current_amount"])

        client = Client()
        first = client.post(
            reverse("wallet-transfer"),
            {
                "source_account": str(source.id),
                "destination_account": str(destination.id),
                "amount": "100",
            },
            content_type="application/json",
        )
        second = client.post(
            reverse("wallet-transfer"),
            {
                "source_account": str(destination.id),
                "destination_account": str(source.id),
                "amount": "100",
            },
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        outgoing = list(
            Transaction.objects.filter(type=TransactionType.TRANSFER)
            .filter(metadata__direction="out")
            .order_by("created_at")
        )
        self.assertEqual(len(outgoing), 2)

        barrier = Barrier(2)
        results = []

        def revert(transaction_id):
            close_old_connections()
            try:
                client = Client()
                barrier.wait(timeout=10)
                response = client.post(
                    reverse("wallet-transaction-revert", args=[transaction_id]),
                    content_type="application/json",
                )
                results.append(response.status_code)
            finally:
                close_old_connections()

        threads = [
            Thread(target=revert, args=(outgoing[0].id,)),
            Thread(target=revert, args=(outgoing[1].id,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertFalse(
            any(thread.is_alive() for thread in threads),
            "Concurrent revert did not complete.",
        )
        self.assertEqual(sorted(results), [200, 200])

        source.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(source.total_balance, Decimal("1000.00"))
        self.assertEqual(destination.total_balance, Decimal("1000.00"))
        self.assertEqual(
            Transaction.objects.filter(
                type=TransactionType.TRANSFER, metadata__reverted=True
            ).count(),
            4,
        )
