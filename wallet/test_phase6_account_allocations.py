from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation


class Phase6AccountAllocationTests(TestCase):
    def test_managed_account_starts_with_spendable_and_savings(self):
        response = self.client.post(
            reverse('master-accounts'),
            {'name': 'Phase6 Allocation Account', 'currency': 'INR'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        account = Account.objects.get(name='Phase6 Allocation Account')
        self.assertTrue(Allocation.objects.filter(account=account, type='spendable').exists())
        self.assertTrue(Allocation.objects.filter(account=account, type='savings').exists())
