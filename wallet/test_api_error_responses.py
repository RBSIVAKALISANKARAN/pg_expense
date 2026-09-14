from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType, Transaction, TransactionType


class ApiErrorResponseIntegrationTests(TestCase):
    def setUp(self):
        self.account = Account.objects.get(name="rbsankaran_acc")

    def deposit(self, amount):
        return self.client.post(
            reverse("account-deposit", args=[self.account.id]),
            {"amount": str(amount)},
            content_type="application/json",
        )

    def test_negative_deposit_returns_structured_400_without_mutation(self):
        response = self.deposit("-100")

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.json(), dict)
        self.account.refresh_from_db()
        self.assertEqual(self.account.total_balance, Decimal("0.00"))
        self.assertEqual(
            Transaction.objects.filter(
                account=self.account, type=TransactionType.DEPOSIT
            ).count(),
            0,
        )

    def test_transfer_beyond_allocation_returns_400_without_mutation(self):
        response = self.deposit("500")
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.post(
            reverse("account-transfer-to-savings", args=[self.account.id]),
            {"amount": "600"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            ["Insufficient funds in this specific owner's money pool."],
        )
        spendable = Allocation.objects.get(
            account=self.account,
            type=AllocationType.SPENDABLE,
        )
        savings = Allocation.objects.get(
            account=self.account,
            type=AllocationType.SAVINGS,
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.total_balance, Decimal("500.00"))
        self.assertEqual(spendable.balance, Decimal("500.00"))
        self.assertEqual(savings.balance, Decimal("0.00"))
        self.assertEqual(
            Transaction.objects.filter(
                account=self.account, type=TransactionType.ALLOCATION
            ).count(),
            0,
        )

    def test_negative_expense_returns_400_without_mutation(self):
        response = self.deposit("500")
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.post(
            reverse("account-expense", args=[self.account.id]),
            {"amount": "-50", "allocation": AllocationType.SPENDABLE},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.json(), dict)
        self.account.refresh_from_db()
        self.assertEqual(self.account.total_balance, Decimal("500.00"))
        self.assertEqual(
            Transaction.objects.filter(
                account=self.account, type=TransactionType.EXPENSE
            ).count(),
            0,
        )

    def test_invalid_allocation_type_returns_400(self):
        response = self.client.post(
            reverse("account-allocate", args=[self.account.id]),
            {
                "from_type": "invalid",
                "to_type": AllocationType.SAVINGS,
                "amount": "100",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.json(), dict)
        self.assertIn("detail", response.json())
