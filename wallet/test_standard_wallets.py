from django.test import TestCase

from .models import Account, Allocation, MoneyLocation


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
