from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Account


class WalletAccountCreationConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_creation_of_same_account_name_is_serialized(self):
        barrier = Barrier(2)
        results = []

        def create_account():
            close_old_connections()
            try:
                client = APIClient()
                barrier.wait(timeout=10)
                response = client.post(
                    reverse("wallet-account-create"),
                    {
                        "name": "Concurrent Test Wallet",
                        "currency": "INR",
                        "location_type": "cash",
                        "location_name": "Concurrent Test Wallet",
                    },
                    format="json",
                )
                results.append(response.status_code)
            finally:
                close_old_connections()

        threads = [Thread(target=create_account), Thread(target=create_account)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertFalse(
            any(thread.is_alive() for thread in threads),
            "Concurrent wallet creation did not complete.",
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(
            Account.objects.filter(name="Concurrent Test Wallet").count(), 1
        )
        self.assertTrue(all(status in (200, 201) for status in results))
