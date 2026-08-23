from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, MoneyLocation, Owner


class StandardWalletSetupTests(TestCase):
    def test_standard_wallets_are_available_after_migrations(self):
        expected = {
            'rbsankaran_acc': 'bank',
            'Amma Cash': 'cash',
            'Appa Cash': 'cash',
            'Change Cash': 'change_cash',
            'Travel Card': 'travel_card',
        }
        for name, location_type in expected.items():
            account = Account.objects.select_related('money_location').get(name=name)
            self.assertEqual(account.money_location.name, name)
            self.assertEqual(account.money_location.location_type, location_type)
            self.assertTrue(Allocation.objects.filter(account=account, type='spendable').exists())
            self.assertTrue(Allocation.objects.filter(account=account, type='savings').exists())

    def test_old_tmb_location_is_not_used_for_the_standard_bank_wallet(self):
        self.assertFalse(MoneyLocation.objects.filter(name='TMB Bank').exists())
        self.assertTrue(MoneyLocation.objects.filter(name='rbsankaran_acc', location_type='bank').exists())

    def test_standard_wallet_transfer_moves_the_same_amount_between_wallets(self):
        source = Account.objects.get(name='rbsankaran_acc')
        destination = Account.objects.get(name='Travel Card')
        owner = Owner.objects.get(name='Me')

        deposit = self.client.post(
            reverse('account-deposit', args=[source.id]),
            {'amount': '1000'},
            content_type='application/json',
        )
        self.assertEqual(deposit.status_code, 200, deposit.content)

        transfer = self.client.post(
            reverse('wallet-transfer'),
            {
                'source_account': str(source.id),
                'destination_account': str(destination.id),
                'owner': str(owner.id),
                'amount': '250',
            },
            content_type='application/json',
        )
        self.assertEqual(transfer.status_code, 201, transfer.content)

        source.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(source.total_balance, Decimal('750.00'))
        self.assertEqual(destination.total_balance, Decimal('250.00'))
