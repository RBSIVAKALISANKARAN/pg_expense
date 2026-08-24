from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AppSetting

DEFAULT_SETTINGS = {
    'app_name': 'Expense Tracking Savings Spendable',
    'currency_default': 'INR',
    'timezone': 'Asia/Kolkata',
    'default_allocation': 'spendable',
    'default_owner': 'Me',
    'default_money_location': 'rbsankaran_acc',
}


def _settings_payload():
    values = DEFAULT_SETTINGS.copy()
    values.update({row.key: row.value for row in AppSetting.objects.all()})
    return values


@api_view(['GET', 'POST'])
def persistent_app_settings(request):
    if request.method == 'GET':
        return Response(_settings_payload())

    allowed = set(DEFAULT_SETTINGS)
    data = request.data if isinstance(request.data, dict) else {}
    unknown = sorted(set(data) - allowed)
    if unknown:
        return Response({'detail': f'Unsupported setting(s): {", ".join(unknown)}'}, status=400)

    if 'default_allocation' in data and data['default_allocation'] not in ('spendable', 'savings'):
        return Response({'detail': 'default_allocation must be spendable or savings.'}, status=400)

    for key, value in data.items():
        value = str(value).strip()
        if not value:
            return Response({'detail': f'{key} cannot be empty.'}, status=400)
        AppSetting.objects.update_or_create(key=key, defaults={'value': value})
    return Response(_settings_payload())


@login_required
def persistent_settings_page(request):
    return render(request, 'settings.html', _settings_payload())
