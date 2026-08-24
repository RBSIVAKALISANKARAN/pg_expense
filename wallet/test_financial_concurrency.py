from decimal import Decimal
from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import Client, TransactionTestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType, MoneyLocation, Owner, Transaction, TransactionType


class ConcurrentFinancialOperationTests(TransactionTestCase):
    reset_sequences = True

    def test_two_concurrent_expenses_cannot_overspend_one_account(self):
        owner = Owner.objects.get(name='Me')
        location = MoneyLocation.objects.get(name='rbsankaran_acc')
        account = Account.objects.get(name='rbsankaran_acc')
        spendable = Allocation.objects.get(account=account, type=AllocationType.SPENDABLE)
        spendable.balance = Decimal('1000.00')
        spendable.save(update_fields=['balance'])
        account.total_balance = Decimal('1000.00')
        account.save(update_fields=['total_balance'])

        from .financial_integrity import ensure_account_money_pool
        pool = ensure_account_money_pool(account, owner, location, AllocationType.SPENDABLE)
        pool.current_amount = Decimal('1000.00')
        pool.save(update_fields=['current_amount'])

        barrier = Barrier(2)
        results = []

        def spend():
            close_old_connections()
            try:
                client = Client()
                barrier.wait(timeout=10)
                response = client.post(
                    reverse('account-expense', args=[account.id]),
                    {'amount': '700', 'allocation': AllocationType.SPENDABLE},
                    content_type='application/json',
                )
                results.append(response.status_code)
            finally:
                close_old_connections()

        threads = [Thread(target=spend), Thread(target=spend)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertFalse(any(thread.is_alive() for thread in threads), 'Concurrent operation did not complete.')
        self.assertEqual(sorted(results), [200, 400])

        account.refresh_from_db()
        spendable.refresh_from_db()
        pool.refresh_from_db()
        self.assertEqual(account.total_balance, Decimal('300.00'))
        self.assertEqual(spendable.balance, Decimal('300.00'))
        self.assertEqual(pool.current_amount, Decimal('300.00'))
        self.assertEqual(Transaction.objects.filter(account=account, type=TransactionType.EXPENSE).count(), 1)
