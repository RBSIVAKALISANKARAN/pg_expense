from decimal import Decimal
from time import perf_counter
from uuid import uuid4

from django.db import connection, transaction
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .feature_models import MealOption
from .models import (
    Account, Allocation, AllocationType, Category, FoodEvent, FoodEventItem,
    Item, MoneyLocation, MoneyLocationType, MoneyPool, Owner, SubCategory,
    Transaction, TransactionType,
)
from .serializers import AccountSerializer, TransactionSerializer
from .views import (
    _account_context, _apply_money_pool_delta, _assert_account_reconciles,
    _check_pool_funds, _ensure_allocations, _ensure_family_defaults,
    _ensure_money_pool,
)


PAYMENT_TO_LOCATION = {
    'upi': {'bank'},
    'bank': {'bank'},
    'cash': {'cash', 'change_cash'},
    'travel_card': {'travel_card'},
}


def _get_account(pk):
    try:
        return Account.objects.select_for_update().get(pk=pk)
    except Account.DoesNotExist:
        raise ValidationError({'account': 'Account not found.'})


def _amount(value):
    try:
        value = Decimal(str(value))
    except Exception:
        raise ValidationError({'amount': 'Amount must be a valid number.'})
    if value <= 0:
        raise ValidationError({'amount': 'Amount must be greater than zero.'})
    return value


def _validate_taxonomy(category, subcategory, item):
    if subcategory and (not category or subcategory.category_id != category.id):
        raise ValidationError({'subcategory': 'Subcategory must belong to the selected category.'})
    if item and category and item.category_id != category.id:
        raise ValidationError({'item': 'Item must belong to the selected category.'})
    if item and subcategory and item.subcategory_id not in (None, subcategory.id):
        raise ValidationError({'item': 'Item must belong to the selected subcategory.'})


def _validate_transport(data, category, location_type):
    is_transport = bool(category and category.name.strip().lower() == 'transport')
    if not is_transport:
        return
    for key in ('transport_from', 'transport_to', 'payment_method'):
        if not str(data.get(key, '')).strip():
            raise ValidationError({key: f'{key.replace("_", " ").title()} is required for transport expenses.'})
    payment = str(data.get('payment_method')).strip().lower()
    if payment not in PAYMENT_TO_LOCATION:
        raise ValidationError({'payment_method': 'Payment method must be Cash, Travel Card, UPI, or Bank/Card.'})
    if location_type not in PAYMENT_TO_LOCATION[payment]:
        raise ValidationError({'payment_method': f'{payment} does not match the selected account wallet type ({location_type}).'})
    mode = str(data.get('transport_mode') or '').strip().lower()
    if not mode:
        raise ValidationError({'transport_mode': 'Transport mode is required.'})
    if mode == 'bus' and not str(data.get('bus_type') or '').strip():
        raise ValidationError({'bus_type': 'Bus type is required for bus expenses.'})


def _metadata(data):
    keys = ('merchant', 'note', 'custom_description', 'transport_from', 'transport_to',
            'transport_mode', 'bus_type', 'payment_method')
    return {key: str(data.get(key, '') or '').strip() for key in keys if data.get(key) not in (None, '')}


def _owner(owner_id=None):
    _ensure_family_defaults()
    if owner_id:
        try:
            return Owner.objects.get(pk=owner_id, active=True)
        except Owner.DoesNotExist:
            raise ValidationError({'owner': 'Owner not found.'})
    return Owner.objects.get(name='Me')


def _lock_two_accounts(source_id, destination_id):
    if str(source_id) == str(destination_id):
        raise ValidationError({'destination_account': 'Source and destination accounts must differ.'})
    ids = sorted([source_id, destination_id], key=str)
    locked = {str(a.id): a for a in Account.objects.select_for_update().filter(id__in=ids)}
    if len(locked) != 2:
        raise ValidationError({'account': 'Source or destination account not found.'})
    return locked[str(source_id)], locked[str(destination_id)]


def _assert_global_reconciliation(accounts):
    for account in accounts:
        account.refresh_from_db()
        _assert_account_reconciles(account)


@api_view(['POST'])
def create_wallet_account(request):
    name = str(request.data.get('name') or '').strip()
    currency = str(request.data.get('currency') or 'INR').strip() or 'INR'
    location_type = str(request.data.get('location_type') or MoneyLocationType.BANK).strip()
    location_name = str(request.data.get('location_name') or name).strip()
    valid_types = {value for value, _ in MoneyLocationType.choices}
    if not name:
        raise ValidationError({'name': 'Account name is required.'})
    if location_type not in valid_types:
        raise ValidationError({'location_type': 'Invalid wallet type.'})
    with transaction.atomic():
        location, _ = MoneyLocation.objects.get_or_create(
            name=location_name,
            defaults={'location_type': location_type, 'active': True},
        )
        if location.location_type != location_type:
            raise ValidationError({'location_type': 'An existing location with this name has a different wallet type.'})

        account = Account.objects.filter(name=name).first()
        if account is None:
            account = Account.objects.create(name=name, currency=currency, money_location=location)
        else:
            if account.money_location_id and account.money_location_id != location.id:
                raise ValidationError({'name': 'An account with this name already exists for a different wallet location.'})
            account.money_location = location
            account.currency = currency
            account.save(update_fields=['money_location', 'currency', 'updated_at'])

        if not account.money_location_id:
            account.money_location = location
            account.save(update_fields=['money_location', 'updated_at'])

        _ensure_allocations(account)
        owner = _owner()
        for allocation_type in AllocationType.values:
            _ensure_money_pool(account, owner, location, allocation_type)
        _assert_account_reconciles(account)
    return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def wallet_transfer(request):
    amount = _amount(request.data.get('amount'))
    owner = _owner(request.data.get('owner'))
    with transaction.atomic():
        source, destination = _lock_two_accounts(request.data.get('source_account'), request.data.get('destination_account'))
        _ensure_allocations(source)
        _ensure_allocations(destination)
        source_alloc = Allocation.objects.select_for_update().get(account=source, type=AllocationType.SPENDABLE)
        destination_alloc = Allocation.objects.select_for_update().get(account=destination, type=AllocationType.SPENDABLE)
        source_owner, source_location = _account_context(source, owner)
        destination_owner, destination_location = _account_context(destination, owner)
        if source_alloc.balance < amount:
            raise ValidationError({'amount': 'Insufficient spendable balance in the source wallet.'})
        _check_pool_funds(source, source_owner, source_location, source_alloc, amount)
        source_alloc.balance -= amount
        source.total_balance -= amount
        destination_alloc.balance += amount
        destination.total_balance += amount
        source_alloc.save(update_fields=['balance', 'updated_at'])
        source.save(update_fields=['total_balance', 'updated_at'])
        destination_alloc.save(update_fields=['balance', 'updated_at'])
        destination.save(update_fields=['total_balance', 'updated_at'])
        source_pool = _apply_money_pool_delta(source, source_owner, source_location, source_alloc, -amount)
        destination_pool = _apply_money_pool_delta(destination, destination_owner, destination_location, destination_alloc, amount)
        group = str(uuid4())
        out_tx = Transaction.objects.create(
            account=source, owner=source_owner, money_location=source_location,
            allocation=source_alloc, source_pool=source_pool, type=TransactionType.TRANSFER,
            amount=amount, metadata={'direction': 'out', 'transfer_group': group,
            'destination_account': str(destination.id), 'destination_location': destination_location.name},
        )
        in_tx = Transaction.objects.create(
            account=destination, owner=destination_owner, money_location=destination_location,
            allocation=destination_alloc, source_pool=destination_pool, type=TransactionType.TRANSFER,
            amount=amount, metadata={'direction': 'in', 'transfer_group': group,
            'source_account': str(source.id), 'source_location': source_location.name},
        )
        out_tx.related_tx = in_tx
        in_tx.related_tx = out_tx
        out_tx.save(update_fields=['related_tx'])
        in_tx.save(update_fields=['related_tx'])
        _assert_global_reconciliation([source, destination])
    return Response({'outgoing': TransactionSerializer(out_tx).data, 'incoming': TransactionSerializer(in_tx).data}, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def wallet_expense_entry(request):
    if request.method == 'GET':
        return Response({'accounts': AccountSerializer(Account.objects.all(), many=True).data})
    data = request.data
    amount = _amount(data.get('amount'))
    try:
        account_id = data.get('account')
        category = Category.objects.get(pk=data.get('category')) if data.get('category') else None
        subcategory = SubCategory.objects.get(pk=data.get('subcategory')) if data.get('subcategory') else None
        item = Item.objects.get(pk=data.get('item')) if data.get('item') else None
    except (Category.DoesNotExist, SubCategory.DoesNotExist, Item.DoesNotExist):
        raise ValidationError({'category': 'Selected category, subcategory, or item does not exist.'})
    _validate_taxonomy(category, subcategory, item)
    owner = _owner(data.get('owner'))
    allocation_type = str(data.get('allocation') or AllocationType.SPENDABLE)
    if allocation_type not in AllocationType.values:
        raise ValidationError({'allocation': 'Allocation must be spendable or savings.'})
    with transaction.atomic():
        account = _get_account(account_id)
        _ensure_allocations(account)
        allocation = Allocation.objects.select_for_update().get(account=account, type=allocation_type)
        owner, location = _account_context(account, owner)
        _validate_transport(data, category, location.location_type)
        if allocation.balance < amount:
            raise ValidationError({'amount': f'Insufficient funds in {allocation_type} allocation.'})
        _check_pool_funds(account, owner, location, allocation, amount)
        allocation.balance -= amount
        account.total_balance -= amount
        allocation.save(update_fields=['balance', 'updated_at'])
        account.save(update_fields=['total_balance', 'updated_at'])
        source_pool = _apply_money_pool_delta(account, owner, location, allocation, -amount)
        tx = Transaction.objects.create(
            account=account, owner=owner, money_location=location, allocation=allocation,
            source_pool=source_pool, category=category, subcategory=subcategory, item=item,
            variant=str(data.get('variant') or '').strip(), meal=data.get('meal') or None,
            type=TransactionType.EXPENSE, amount=amount, metadata=_metadata(data),
            occurred_at=data.get('occurred_at') or timezone.now(),
        )
        food_items = data.get('food_items') or []
        if food_items:
            meal = str(data.get('meal') or '').strip()
            if not meal:
                raise ValidationError({'meal': 'Meal is required when food items are supplied.'})
            event = FoodEvent.objects.create(transaction=tx, meal=meal)
            for entry in food_items:
                food_item = Item.objects.filter(pk=entry.get('item')).first() if entry.get('item') else None
                custom_name = str(entry.get('custom_name') or '').strip()
                if not food_item and not custom_name:
                    raise ValidationError({'food_items': 'Each food entry needs an item or custom name.'})
                quantity = Decimal(str(entry.get('quantity') or '1'))
                if quantity <= 0:
                    raise ValidationError({'food_items': 'Quantity must be greater than zero.'})
                FoodEventItem.objects.create(event=event, item=food_item, custom_name=custom_name,
                                              variant=str(entry.get('variant') or '').strip(), quantity=quantity)
        _assert_account_reconciles(account)
    return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'PUT'])
def wallet_edit_expense(request, id):
    with transaction.atomic():
        tx = Transaction.objects.select_for_update().filter(pk=id, type=TransactionType.EXPENSE).first()
        if not tx:
            raise ValidationError('Only existing expense transactions can be edited.')
        if tx.metadata.get('reverted') or tx.metadata.get('deleted'):
            raise ValidationError('A reverted/deleted transaction cannot be edited.')
        account = Account.objects.select_for_update().get(pk=tx.account_id)
        allocation = Allocation.objects.select_for_update().get(pk=tx.allocation_id)
        owner, location = _account_context(account, tx.owner, tx.money_location)
        old_amount = tx.amount
        new_amount = _amount(request.data.get('amount', old_amount))
        category = Category.objects.get(pk=request.data['category']) if request.data.get('category') else tx.category
        subcategory = SubCategory.objects.get(pk=request.data['subcategory']) if request.data.get('subcategory') else tx.subcategory
        item = Item.objects.get(pk=request.data['item']) if request.data.get('item') else tx.item
        _validate_taxonomy(category, subcategory, item)
        _validate_transport(request.data, category, location.location_type) if category and category.name.lower() == 'transport' else None
        delta = new_amount - old_amount
        if delta > 0:
            _check_pool_funds(account, owner, location, allocation, delta)
        allocation.balance -= delta
        account.total_balance -= delta
        allocation.save(update_fields=['balance', 'updated_at'])
        account.save(update_fields=['total_balance', 'updated_at'])
        _apply_money_pool_delta(account, owner, location, allocation, -delta)
        tx.amount = new_amount
        tx.category = category
        tx.subcategory = subcategory
        tx.item = item
        tx.variant = str(request.data.get('variant', tx.variant) or '').strip()
        tx.meal = request.data.get('meal', tx.meal) or None
        tx.metadata = {**tx.metadata, **_metadata(request.data), 'edited': True}
        tx.save(update_fields=['amount', 'category', 'subcategory', 'item', 'variant', 'meal', 'metadata'])
        _assert_account_reconciles(account)
    return Response(TransactionSerializer(tx).data)


@api_view(['POST', 'DELETE'])
def wallet_revert_transaction(request, id):
    with transaction.atomic():
        tx = Transaction.objects.select_for_update().filter(pk=id).first()
        if not tx:
            raise ValidationError('Transaction not found.')
        if tx.metadata.get('reverted') or tx.metadata.get('deleted'):
            raise ValidationError('Transaction has already been reverted/deleted.')
        related = Transaction.objects.select_for_update().filter(pk=tx.related_tx_id).first() if tx.related_tx_id else None
        targets = [tx] + ([related] if related else [])
        for target in targets:
            account = Account.objects.select_for_update().get(pk=target.account_id)
            _ensure_allocations(account)
            allocation = Allocation.objects.select_for_update().get(pk=target.allocation_id) if target.allocation_id else None
            owner, location = _account_context(account, target.owner, target.money_location)
            amount = target.amount
            if target.type == TransactionType.EXPENSE:
                continue
            if target.type == TransactionType.DEPOSIT:
                if not allocation or allocation.balance < amount:
                    raise ValidationError('Deposit cannot be reverted because the credited money is no longer available.')
            elif target.type == TransactionType.TRANSFER and target.metadata.get('direction') == 'in':
                if not allocation or allocation.balance < amount:
                    raise ValidationError('Transfer cannot be reverted because destination funds were already spent.')
        for target in targets:
            account = Account.objects.select_for_update().get(pk=target.account_id)
            _ensure_allocations(account)
            allocation = Allocation.objects.select_for_update().get(pk=target.allocation_id) if target.allocation_id else None
            owner, location = _account_context(account, target.owner, target.money_location)
            amount = target.amount
            if target.type == TransactionType.EXPENSE:
                allocation.balance += amount
                account.total_balance += amount
                allocation.save(update_fields=['balance', 'updated_at'])
                account.save(update_fields=['total_balance', 'updated_at'])
                _apply_money_pool_delta(account, owner, location, allocation, amount)
            elif target.type == TransactionType.DEPOSIT:
                allocation.balance -= amount
                account.total_balance -= amount
                allocation.save(update_fields=['balance', 'updated_at'])
                account.save(update_fields=['total_balance', 'updated_at'])
                _apply_money_pool_delta(account, owner, location, allocation, -amount)
            elif target.type == TransactionType.ALLOCATION:
                source_type = target.metadata.get('from')
                destination_type = target.metadata.get('to')
                source = Allocation.objects.select_for_update().get(account=account, type=source_type)
                destination = Allocation.objects.select_for_update().get(account=account, type=destination_type)
                if destination.balance < amount:
                    raise ValidationError('Allocation cannot be reverted because destination funds were already spent.')
                destination.balance -= amount
                source.balance += amount
                destination.save(update_fields=['balance', 'updated_at'])
                source.save(update_fields=['balance', 'updated_at'])
                _apply_money_pool_delta(account, owner, location, destination, -amount)
                _apply_money_pool_delta(account, owner, location, source, amount)
            elif target.type == TransactionType.TRANSFER:
                direction = target.metadata.get('direction')
                if direction == 'out':
                    allocation.balance += amount
                    account.total_balance += amount
                    allocation.save(update_fields=['balance', 'updated_at'])
                    account.save(update_fields=['total_balance', 'updated_at'])
                    _apply_money_pool_delta(account, owner, location, allocation, amount)
                elif direction == 'in':
                    allocation.balance -= amount
                    account.total_balance -= amount
                    allocation.save(update_fields=['balance', 'updated_at'])
                    account.save(update_fields=['total_balance', 'updated_at'])
                    _apply_money_pool_delta(account, owner, location, allocation, -amount)
            target.metadata = {**target.metadata, 'reverted': True, 'deleted': request.method == 'DELETE', 'reverted_at': str(target.occurred_at)}
            target.save(update_fields=['metadata'])
            _assert_account_reconciles(account)
    return Response({'detail': 'Transaction reverted and retained in the ledger for audit history.'})


@api_view(['GET'])
def money_report_data(request):
    qs = Transaction.objects.select_related('category', 'subcategory', 'item', 'account', 'money_location').filter(type=TransactionType.EXPENSE).exclude(metadata__reverted=True).exclude(metadata__deleted=True)
    result = {key: {} for key in ('category', 'subcategory', 'item', 'payment_method', 'transport_mode', 'meal')}
    for tx in qs:
        amount = float(tx.amount)
        labels = {
            'category': tx.category.name if tx.category else 'Uncategorized',
            'subcategory': tx.subcategory.name if tx.subcategory else 'Uncategorized',
            'item': tx.item.name if tx.item else (tx.metadata.get('custom_description') or 'Custom / Other'),
            'payment_method': tx.metadata.get('payment_method', 'Other'),
            'transport_mode': tx.metadata.get('transport_mode', 'Non-transport'),
            'meal': tx.meal or 'Not specified',
        }
        for key, label in labels.items():
            result[key][label] = result[key].get(label, 0) + amount
    return Response(result)


def exact_database_page(request):
    with connection.cursor() as cursor:
        table_names = sorted(t.name for t in connection.introspection.get_table_list(cursor) if t.type == 't')
        tables = []
        for name in table_names:
            columns = []
            for column in connection.introspection.get_table_description(cursor, name):
                try:
                    type_name = connection.introspection.get_field_type(column.type_code, column)
                except Exception:
                    type_name = str(column.type_code)
                columns.append({'name': column.name, 'type': type_name, 'nullable': column.null_ok})
            tables.append({'name': name, 'columns': columns})
    return render(request, 'database_structure_exact.html', {'tables': tables})


def complete_sql_page(request):
    return render(request, 'sql_playground_enhanced.html')


@api_view(['GET'])
def exact_sql_schema(request):
    with connection.cursor() as cursor:
        tables = []
        for table in sorted(t.name for t in connection.introspection.get_table_list(cursor) if t.type == 't'):
            columns = []
            for column in connection.introspection.get_table_description(cursor, table):
                try:
                    type_name = connection.introspection.get_field_type(column.type_code, column)
                except Exception:
                    type_name = str(column.type_code)
                columns.append({'name': column.name, 'type': type_name, 'nullable': column.null_ok})
            tables.append({'name': table, 'columns': columns})
    return Response({'tables': tables})
