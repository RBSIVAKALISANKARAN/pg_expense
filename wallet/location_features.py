from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import MoneyLocation


@api_view(['GET'])
def enhanced_money_locations(request):
    defaults = [
        ('TMB Bank', 'bank'),
        ('Appa Cash', 'cash'),
        ('Amma Cash', 'cash'),
        ('Travel Card', 'travel_card'),
        ('Change Cash', 'change_cash'),
    ]
    for name, location_type in defaults:
        MoneyLocation.objects.get_or_create(name=name, defaults={'location_type': location_type, 'active': True})
    locations = MoneyLocation.objects.filter(active=True).order_by('name')
    return Response([{'id': str(x.id), 'name': x.name, 'location_type': x.location_type, 'active': x.active} for x in locations])
