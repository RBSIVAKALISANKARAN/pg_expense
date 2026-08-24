from django.test import TestCase

from .models import MoneyLocation, MoneyLocationType


class WalletDomainModelTests(TestCase):
    def test_travel_card_and_change_cash_are_wallet_location_types(self):
        travel = MoneyLocation.objects.get(name='Travel Card')
        change = MoneyLocation.objects.get(name='Change Cash')

        self.assertEqual(travel.location_type, MoneyLocationType.TRAVEL_CARD)
        self.assertEqual(change.location_type, MoneyLocationType.CHANGE_CASH)
