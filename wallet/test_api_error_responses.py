from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.exceptions import APIException

from .exceptions import api_exception_handler
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

    def test_successful_get_returns_resource_shape(self):
        response = self.client.get(reverse("account-list-create"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json().__class__, (list, dict))

    def test_successful_post_returns_created_resource(self):
        response = self.client.post(
            reverse("account-list-create"),
            {"name": "Response Shape Account", "currency": "INR"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsInstance(response.json(), dict)
        self.assertEqual(response.json()["name"], "Response Shape Account")

    def test_negative_deposit_returns_structured_400_without_mutation(self):
        response = self.deposit("-100")

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIsInstance(payload, dict)
        self.assertIn("detail", payload)
        self.assertIn("errors", payload)
        self.account.refresh_from_db()
        self.assertEqual(self.account.total_balance, Decimal("0.00"))
        self.assertEqual(
            Transaction.objects.filter(
                account=self.account, type=TransactionType.DEPOSIT
            ).count(),
            0,
        )

    def test_forbidden_response_uses_normalized_shape(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="response-shape-nonstaff", password="test-password"
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("sql-execute"),
            {"sql": "SELECT 1 AS value"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertIsInstance(payload, dict)
        self.assertIn("detail", payload)
        self.assertIn("errors", payload)

    def test_server_error_response_uses_normalized_shape(self):
        class ServerError(APIException):
            status_code = 500
            default_detail = "Internal test server error."

        response = api_exception_handler(ServerError(), {})

        self.assertEqual(response.status_code, 500)
        payload = response.data
        self.assertEqual(payload["detail"], "Internal test server error.")
        self.assertIn("errors", payload)

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
            {
                "detail": "Insufficient funds in this specific owner's money pool.",
                "errors": [
                    "Insufficient funds in this specific owner's money pool."
                ],
            },
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
