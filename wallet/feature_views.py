from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .feature_models import MealOption
from .models import (
    Account, Allocation, AllocationType, Category, FoodEvent, FoodEventItem,
    Item, MoneyLocation, Owner, SubCategory, Transaction,
    TransactionType,
)
from .serializers import AccountSerializer, TransactionSerializer
from .views import (
    _account_context, _apply_money_pool_delta, _assert_account_reconciles,
    _check_pool_funds, _ensure_allocations,
)


TRANSPORT_KEYS = ('transport_from', 'transport_to', 'transport_mode', 'bus_type', 'payment_method')


def _metadata_from_request(data):
    metadata = {
        'merchant': data.get('merchant', ''),
        'note': data.get('note', ''),
        'custom_description': data.get('custom_description', ''),
    }
    for key in TRANSPORT_KEYS:
        value = data.get(key)
        if value not in (None, ''):
            metadata[key] = value
    return metadata


def _validate_transport(data, category):
    is_transport = bool(category and category.name.strip().lower() == 'transport')
    if not is_transport:
        return
    required = {
        'transport_from': 'From is required for transport expenses.',
        'transport_to': 'To is required for transport expenses.',
        'payment_method': 'Payment method is required for transport expenses.',
    }
    for key, message in required.items():
        if not str(data.get(key, '')).strip():
            raise ValidationError({key: message})


@api_view(['GET', 'POST'])
def meals(request):
    if request.method == 'GET':
        defaults = ['Breakfast', 'Lunch', 'Dinner', 'Snack']
        for name in defaults:
            MealOption.objects.get_or_create(name=name)
        return Response([{'id': meal.id, 'name': meal.name, 'active': meal.active} for meal in MealOption.objects.filter(active=True)])
    name = str(request.data.get('name', '')).strip()
    if not name:
        return Response({'detail': 'Meal name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    meal, created = MealOption.objects.get_or_create(name=name, defaults={'active': True})
    if not created and not meal.active:
        meal.active = True
        meal.save(update_fields=['active'])
    return Response({'id': meal.id, 'name': meal.name, 'active': meal.active}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


def expense_page(request):
    return render(request, 'expense.html')


@api_view(['GET', 'POST'])
def expense_entry(request):
    if request.method == 'GET':
        accounts = Account.objects.all()
        return Response(AccountSerializer(accounts, many=True).data)
    data = request.data
    try:
        amount = Decimal(str(data.get('amount', '0')))
    except Exception:
        raise ValidationError({'amount': 'Amount must be a valid number.'})
    if amount <= 0:
        raise ValidationError({'amount': 'Amount must be greater than zero.'})
    account = get_object_or_404(Account, id=data.get('account'))
    allocation_type = str(data.get('allocation') or 'spendable')
    if allocation_type not in ('spendable', 'savings'):
        raise ValidationError({'allocation': 'Allocation must be spendable or savings.'})
    category = get_object_or_404(Category, id=data.get('category')) if data.get('category') else None
    subcategory = get_object_or_404(SubCategory, id=data.get('subcategory')) if data.get('subcategory') else None
    item = get_object_or_404(Item, id=data.get('item')) if data.get('item') else None
    if subcategory and (not category or subcategory.category_id != category.id):
        raise ValidationError({'subcategory': 'Subcategory must belong to the selected category.'})
    if item and category and item.category_id != category.id:
        raise ValidationError({'item': 'Item must belong to the selected category.'})
    if item and subcategory and item.subcategory_id not in (None, subcategory.id):
        raise ValidationError({'item': 'Item must belong to the selected subcategory.'})
    _validate_transport(data, category)

    with transaction.atomic():
        account = Account.objects.select_for_update().get(pk=account.pk)
        _ensure_allocations(account)
        allocation = Allocation.objects.select_for_update().get(account=account, type=allocation_type)
        owner = get_object_or_404(Owner, id=data.get('owner')) if data.get('owner') else None
        location = get_object_or_404(MoneyLocation, id=data.get('money_location')) if data.get('money_location') else None
        owner, location = _account_context(account, owner, location)
        if allocation.balance < amount:
            raise ValidationError({'amount': f'Insufficient funds in {allocation_type} allocation.'})
        _check_pool_funds(account, owner, location, allocation, amount)
        allocation.balance -= amount
        account.total_balance -= amount
        allocation.save(update_fields=['balance', 'updated_at'])
        account.save(update_fields=['total_balance', 'updated_at'])
        source_pool = _apply_money_pool_delta(account, owner, location, allocation, -amount)
        metadata = _metadata_from_request(data)
        tx = Transaction.objects.create(
            account=account, owner=owner, money_location=location, allocation=allocation,
            source_pool=source_pool, category=category, subcategory=subcategory, item=item,
            variant=str(data.get('variant') or '').strip(), meal=data.get('meal') or None,
            type=TransactionType.EXPENSE, amount=amount, metadata=metadata,
            occurred_at=data.get('occurred_at') or None,
        )
        food_items = data.get('food_items') or []
        if food_items:
            meal = str(data.get('meal') or '').strip()
            if not meal:
                raise ValidationError({'meal': 'Meal is required when food items are supplied.'})
            event = FoodEvent.objects.create(transaction=tx, meal=meal)
            for entry in food_items:
                food_item = get_object_or_404(Item, id=entry.get('item')) if entry.get('item') else None
                custom_name = str(entry.get('custom_name') or '').strip()
                if not food_item and not custom_name:
                    raise ValidationError({'food_items': 'Each food entry needs an item or custom name.'})
                FoodEventItem.objects.create(
                    event=event, item=food_item, custom_name=custom_name,
                    variant=str(entry.get('variant') or ''), quantity=Decimal(str(entry.get('quantity') or '1')),
                )
        _assert_account_reconciles(account)
    return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def transfer_between_accounts(request):
    try:
        amount = Decimal(str(request.data.get('amount', '0')))
    except Exception:
        raise ValidationError({'amount': 'Amount must be a valid number.'})
    if amount <= 0:
        raise ValidationError({'amount': 'Amount must be greater than zero.'})
    source = get_object_or_404(Account, id=request.data.get('source_account'))
    destination = get_object_or_404(Account, id=request.data.get('destination_account'))
    if source.pk == destination.pk:
        raise ValidationError({'destination_account': 'Source and destination accounts must differ.'})
    with transaction.atomic():
        source = Account.objects.select_for_update().get(pk=source.pk)
        destination = Account.objects.select_for_update().get(pk=destination.pk)
        _ensure_allocations(source); _ensure_allocations(destination)
        src_alloc = Allocation.objects.select_for_update().get(account=source, type=AllocationType.SPENDABLE)
        dst_alloc = Allocation.objects.select_for_update().get(account=destination, type=AllocationType.SPENDABLE)
        src_owner, src_location = _account_context(source)
        dst_owner, dst_location = _account_context(destination)
        if src_alloc.balance < amount:
            raise ValidationError({'amount': 'Insufficient spendable funds in source account.'})
        _check_pool_funds(source, src_owner, src_location, src_alloc, amount)
        src_alloc.balance -= amount; source.total_balance -= amount
        dst_alloc.balance += amount; destination.total_balance += amount
        src_alloc.save(update_fields=['balance', 'updated_at']); source.save(update_fields=['total_balance', 'updated_at'])
        dst_alloc.save(update_fields=['balance', 'updated_at']); destination.save(update_fields=['total_balance', 'updated_at'])
        src_pool = _apply_money_pool_delta(source, src_owner, src_location, src_alloc, -amount)
        dst_pool = _apply_money_pool_delta(destination, dst_owner, dst_location, dst_alloc, amount)
        group = str(Transaction.objects.count() + 1)
        out_tx = Transaction.objects.create(account=source, owner=src_owner, money_location=src_location, allocation=src_alloc, source_pool=src_pool, type=TransactionType.TRANSFER, amount=amount, metadata={'direction': 'out', 'transfer_group': group, 'destination_account': str(destination.id)})
        in_tx = Transaction.objects.create(account=destination, owner=dst_owner, money_location=dst_location, allocation=dst_alloc, source_pool=dst_pool, type=TransactionType.TRANSFER, amount=amount, metadata={'direction': 'in', 'transfer_group': group, 'source_account': str(source.id)})
        out_tx.related_tx = in_tx; in_tx.related_tx = out_tx; out_tx.save(update_fields=['related_tx']); in_tx.save(update_fields=['related_tx'])
        _assert_account_reconciles(source); _assert_account_reconciles(destination)
    return Response({'outgoing': TransactionSerializer(out_tx).data, 'incoming': TransactionSerializer(in_tx).data}, status=status.HTTP_201_CREATED)



