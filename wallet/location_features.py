from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import MoneyLocation
from .pagination import StandardResultsSetPagination


@api_view(["GET"])
def enhanced_money_locations(request):
    defaults = [
        ("rbsankaran_acc", "bank"),
        ("Appa Cash", "cash"),
        ("Amma Cash", "cash"),
        ("Travel Card", "travel_card"),
        ("Change Cash", "change_cash"),
    ]
    for name, location_type in defaults:
        MoneyLocation.objects.get_or_create(
            name=name, defaults={"location_type": location_type, "active": True}
        )
    locations = MoneyLocation.objects.filter(active=True).order_by("name")
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(locations, request)
    data = [
        {
            "id": str(x.id),
            "name": x.name,
            "location_type": x.location_type,
            "active": x.active,
        }
        for x in page
    ]
    return paginator.get_paginated_response(data)
