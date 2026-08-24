from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Account, AppSetting, Category, Item, MoneyLocation, Owner, SubCategory


DEFAULTS = {
    'app_name': 'Expense Tracking Savings Spendable',
    'currency_default': 'INR',
    'timezone': 'Asia/Kolkata',
    'default_allocation': 'spendable',
    'default_owner': 'Me',
    'default_money_location': 'rbsankaran_acc',
}


def _body(request):
    return request.data if isinstance(request.data, dict) else {}


def _name(data, field='name'):
    value = str(data.get(field, '')).strip()
    if not value:
        raise ValueError(f'{field} is required.')
    return value


def _status_response(obj):
    return {'id': str(obj.id), 'name': obj.name, 'active': obj.active}


@api_view(['GET', 'POST'])
def master_accounts(request):
    if request.method == 'GET':
        return Response([
            {'id': str(a.id), 'name': a.name, 'currency': a.currency,
             'money_location': str(a.money_location_id) if a.money_location_id else None,
             'location_name': a.money_location.name if a.money_location_id else None,
             'total_balance': str(a.total_balance), 'active': a.active}
            for a in Account.objects.select_related('money_location').all()
        ])
    data = _body(request)
    try:
        name = _name(data)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
    if Account.objects.filter(name=name).exists():
        return Response({'detail': 'An account with this name already exists.'}, status=400)
    location_id = data.get('money_location')
    location = get_object_or_404(MoneyLocation, id=location_id, active=True) if location_id else None
    account = Account.objects.create(name=name, currency=str(data.get('currency', 'INR')).strip() or 'INR', money_location=location)
    return Response({'id': str(account.id), 'name': account.name, 'currency': account.currency, 'active': account.active}, status=201)


@api_view(['PATCH', 'POST'])
def master_account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk)
    data = _body(request)
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'detail': 'Account name is required.'}, status=400)
        if Account.objects.exclude(pk=account.pk).filter(name=name).exists():
            return Response({'detail': 'An account with this name already exists.'}, status=400)
        account.name = name
    if 'currency' in data:
        currency = str(data.get('currency', '')).strip()
        if not currency:
            return Response({'detail': 'Currency cannot be empty.'}, status=400)
        account.currency = currency
    if 'money_location' in data:
        location = get_object_or_404(MoneyLocation, pk=data.get('money_location'), active=True)
        account.money_location = location
    account.save()
    return Response({'id': str(account.id), 'name': account.name, 'currency': account.currency,
                     'money_location': str(account.money_location_id) if account.money_location_id else None,
                     'active': account.active})


@api_view(['POST'])
def master_account_status(request, pk):
    account = get_object_or_404(Account, pk=pk)
    active = _body(request).get('active')
    if not isinstance(active, bool):
        return Response({'detail': 'active must be true or false.'}, status=400)
    if not active and account.total_balance != 0:
        return Response({'detail': 'An account with a non-zero balance cannot be archived.'}, status=400)
    account.active = active
    account.save(update_fields=['active', 'updated_at'])
    return Response(_status_response(account))


@api_view(['GET', 'POST'])
def master_categories(request):
    if request.method == 'GET':
        return Response([
            {'id': str(c.id), 'name': c.name, 'description': c.description, 'active': c.active,
             'subcategory_count': c.subcategories.filter(active=True).count(),
             'item_count': c.items.filter(active=True).count()}
            for c in Category.objects.all()
        ])
    data = _body(request)
    try:
        name = _name(data)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
    category = Category.objects.create(name=name, description=str(data.get('description', '')).strip())
    return Response({'id': str(category.id), 'name': category.name, 'description': category.description, 'active': category.active}, status=201)


@api_view(['PATCH', 'POST'])
def master_category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    data = _body(request)
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'detail': 'Category name is required.'}, status=400)
        category.name = name
    if 'description' in data:
        category.description = str(data.get('description', '')).strip()
    category.save()
    return Response({'id': str(category.id), 'name': category.name, 'description': category.description, 'active': category.active})


@api_view(['POST'])
def master_category_status(request, pk):
    category = get_object_or_404(Category, pk=pk)
    active = _body(request).get('active')
    if not isinstance(active, bool):
        return Response({'detail': 'active must be true or false.'}, status=400)
    if not active and (category.transactions.filter().exists()):
        # Historical transactions keep the FK; archiving is safe.
        pass
    category.active = active
    category.save(update_fields=['active', 'updated_at'])
    if not active:
        SubCategory.objects.filter(category=category).update(active=False)
        Item.objects.filter(category=category).update(active=False)
    return Response(_status_response(category))


@api_view(['GET', 'POST'])
def master_subcategories(request):
    if request.method == 'GET':
        qs = SubCategory.objects.select_related('category')
        return Response([{'id': str(s.id), 'category': str(s.category_id), 'category_name': s.category.name,
                          'name': s.name, 'description': s.description, 'active': s.active} for s in qs])
    data = _body(request)
    category = get_object_or_404(Category, pk=data.get('category'), active=True)
    try:
        name = _name(data)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
    if SubCategory.objects.filter(category=category, name=name).exists():
        return Response({'detail': 'This subcategory already exists in the selected category.'}, status=400)
    sub = SubCategory.objects.create(category=category, name=name, description=str(data.get('description', '')).strip())
    return Response({'id': str(sub.id), 'category': str(category.id), 'category_name': category.name, 'name': sub.name, 'active': sub.active}, status=201)


@api_view(['PATCH', 'POST'])
def master_subcategory_detail(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    data = _body(request)
    if 'category' in data:
        sub.category = get_object_or_404(Category, pk=data.get('category'), active=True)
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'detail': 'Subcategory name is required.'}, status=400)
        sub.name = name
    if 'description' in data:
        sub.description = str(data.get('description', '')).strip()
    sub.save()
    return Response({'id': str(sub.id), 'category': str(sub.category_id), 'name': sub.name, 'active': sub.active})


@api_view(['POST'])
def master_subcategory_status(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    active = _body(request).get('active')
    if not isinstance(active, bool):
        return Response({'detail': 'active must be true or false.'}, status=400)
    sub.active = active
    sub.save(update_fields=['active', 'updated_at'])
    if not active:
        Item.objects.filter(subcategory=sub).update(active=False)
    return Response(_status_response(sub))


@api_view(['GET', 'POST'])
def master_items(request):
    if request.method == 'GET':
        qs = Item.objects.select_related('category', 'subcategory')
        return Response([{'id': str(i.id), 'category': str(i.category_id), 'category_name': i.category.name,
                          'subcategory': str(i.subcategory_id) if i.subcategory_id else None,
                          'subcategory_name': i.subcategory.name if i.subcategory_id else None,
                          'name': i.name, 'description': i.description, 'is_custom': i.is_custom, 'active': i.active} for i in qs])
    data = _body(request)
    category = get_object_or_404(Category, pk=data.get('category'), active=True)
    sub = None
    if data.get('subcategory'):
        sub = get_object_or_404(SubCategory, pk=data.get('subcategory'), category=category, active=True)
    try:
        name = _name(data)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
    if Item.objects.filter(category=category, subcategory=sub, name=name).exists():
        return Response({'detail': 'This item already exists in the selected hierarchy.'}, status=400)
    item = Item.objects.create(category=category, subcategory=sub, name=name,
                               description=str(data.get('description', '')).strip(),
                               is_custom=bool(data.get('is_custom', False)))
    return Response({'id': str(item.id), 'category': str(category.id), 'subcategory': str(sub.id) if sub else None,
                     'name': item.name, 'active': item.active}, status=201)


@api_view(['PATCH', 'POST'])
def master_item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    data = _body(request)
    if 'category' in data:
        item.category = get_object_or_404(Category, pk=data.get('category'), active=True)
    if 'subcategory' in data:
        value = data.get('subcategory')
        item.subcategory = get_object_or_404(SubCategory, pk=value, category=item.category, active=True) if value else None
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'detail': 'Item name is required.'}, status=400)
        item.name = name
    if 'description' in data:
        item.description = str(data.get('description', '')).strip()
    item.save()
    return Response({'id': str(item.id), 'category': str(item.category_id), 'subcategory': str(item.subcategory_id) if item.subcategory_id else None, 'name': item.name, 'active': item.active})


@api_view(['POST'])
def master_item_status(request, pk):
    item = get_object_or_404(Item, pk=pk)
    active = _body(request).get('active')
    if not isinstance(active, bool):
        return Response({'detail': 'active must be true or false.'}, status=400)
    item.active = active
    item.save(update_fields=['active', 'updated_at'])
    return Response(_status_response(item))


@api_view(['GET', 'POST'])
def master_owners(request):
    if request.method == 'GET':
        return Response([_status_response(o) for o in Owner.objects.all()])
    data = _body(request)
    try:
        name = _name(data)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
    if Owner.objects.filter(name=name).exists():
        return Response({'detail': 'An owner with this name already exists.'}, status=400)
    owner = Owner.objects.create(name=name)
    return Response(_status_response(owner), status=201)


@api_view(['PATCH', 'POST'])
def master_owner_detail(request, pk):
    owner = get_object_or_404(Owner, pk=pk)
    data = _body(request)
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'detail': 'Owner name is required.'}, status=400)
        if Owner.objects.exclude(pk=owner.pk).filter(name=name).exists():
            return Response({'detail': 'An owner with this name already exists.'}, status=400)
        owner.name = name
    owner.save()
    return Response(_status_response(owner))


@api_view(['POST'])
def master_owner_status(request, pk):
    owner = get_object_or_404(Owner, pk=pk)
    active = _body(request).get('active')
    if not isinstance(active, bool):
        return Response({'detail': 'active must be true or false.'}, status=400)
    owner.active = active
    owner.save(update_fields=['active', 'updated_at'])
    return Response(_status_response(owner))


@api_view(['GET', 'POST'])
def master_locations(request):
    if request.method == 'GET':
        return Response([{'id': str(l.id), 'name': l.name, 'location_type': l.location_type, 'active': l.active} for l in MoneyLocation.objects.all()])
    data = _body(request)
    try:
        name = _name(data)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
    location_type = str(data.get('location_type', 'bank')).strip()
    allowed = {'bank', 'cash', 'travel_card', 'change_cash'}
    if location_type not in allowed:
        return Response({'detail': 'Invalid money location type.'}, status=400)
    if MoneyLocation.objects.filter(name=name).exists():
        return Response({'detail': 'A money location with this name already exists.'}, status=400)
    location = MoneyLocation.objects.create(name=name, location_type=location_type)
    return Response({'id': str(location.id), 'name': location.name, 'location_type': location.location_type, 'active': location.active}, status=201)


@api_view(['PATCH', 'POST'])
def master_location_detail(request, pk):
    location = get_object_or_404(MoneyLocation, pk=pk)
    data = _body(request)
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'detail': 'Location name is required.'}, status=400)
        if MoneyLocation.objects.exclude(pk=location.pk).filter(name=name).exists():
            return Response({'detail': 'A money location with this name already exists.'}, status=400)
        location.name = name
    if 'location_type' in data:
        value = str(data.get('location_type', '')).strip()
        if value not in {'bank', 'cash', 'travel_card', 'change_cash'}:
            return Response({'detail': 'Invalid money location type.'}, status=400)
        location.location_type = value
    location.save()
    return Response({'id': str(location.id), 'name': location.name, 'location_type': location.location_type, 'active': location.active})


@api_view(['POST'])
def master_location_status(request, pk):
    location = get_object_or_404(MoneyLocation, pk=pk)
    active = _body(request).get('active')
    if not isinstance(active, bool):
        return Response({'detail': 'active must be true or false.'}, status=400)
    if not active and location.accounts.filter(active=True).exists():
        return Response({'detail': 'A money location used by an active account cannot be archived.'}, status=400)
    location.active = active
    location.save(update_fields=['active', 'updated_at'])
    return Response(_status_response(location))


@api_view(['GET', 'POST'])
def master_config(request):
    values = DEFAULTS.copy()
    values.update({row.key: row.value for row in AppSetting.objects.all()})
    if request.method == 'GET':
        return Response(values)
    data = _body(request)
    unknown = sorted(set(data) - set(DEFAULTS))
    if unknown:
        return Response({'detail': f'Unsupported setting(s): {", ".join(unknown)}'}, status=400)
    if 'default_allocation' in data and data['default_allocation'] not in {'spendable', 'savings'}:
        return Response({'detail': 'default_allocation must be spendable or savings.'}, status=400)
    if 'default_owner' in data and not Owner.objects.filter(name=str(data['default_owner']).strip(), active=True).exists():
        return Response({'detail': 'default_owner must reference an active owner.'}, status=400)
    if 'default_money_location' in data and not MoneyLocation.objects.filter(name=str(data['default_money_location']).strip(), active=True).exists():
        return Response({'detail': 'default_money_location must reference an active money location.'}, status=400)
    for key, value in data.items():
        value = str(value).strip()
        if not value:
            return Response({'detail': f'{key} cannot be empty.'}, status=400)
        AppSetting.objects.update_or_create(key=key, defaults={'value': value})
    values.update({row.key: row.value for row in AppSetting.objects.all()})
    return Response(values)


@login_required
def master_data_page(request):
    return render(request, 'master_data.html')
