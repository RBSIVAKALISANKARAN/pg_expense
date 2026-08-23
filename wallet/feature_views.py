import re
from decimal import Decimal
from time import perf_counter

from django.db import connection, transaction
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .feature_models import MealOption
from .models import (
    Account, Allocation, AllocationType, Category, FoodEvent, FoodEventItem,
    Item, MealType, MoneyLocation, MoneyPool, Owner, SubCategory, Transaction,
    TransactionType,
)
from .serializers import AccountSerializer, CategorySerializer, ItemSerializer, SubCategorySerializer, TransactionSerializer
from .views import (
    _account_context, _apply_money_pool_delta, _assert_account_reconciles,
    _check_pool_funds, _ensure_allocations, _ensure_family_defaults,
    _ensure_money_pool, _json_safe,
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


def enhanced_reports_page(request):
    return render(request, 'reports_enhanced.html')


def enhanced_database_page(request):
    with connection.cursor() as cursor:
        table_names = [t.name for t in connection.introspection.get_table_list(cursor) if t.type == 't']
        tables = []
        for name in sorted(table_names):
            description = connection.introspection.get_table_description(cursor, name)
            columns = []
            for column in description:
                columns.append({
                    'name': column.name,
                    'type': str(column.type_code),
                    'nullable': column.null_ok,
                })
            tables.append({'name': name, 'columns': columns})
    return render(request, 'database_structure_enhanced.html', {'tables': tables})


def enhanced_sql_page(request):
    return render(request, 'sql_playground_enhanced.html')


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


def _revert_single_transaction(tx):
    if tx.metadata.get('reverted'):
        raise ValidationError('Transaction has already been reverted.')
    account = Account.objects.select_for_update().get(pk=tx.account_id)
    _ensure_allocations(account)
    allocation = Allocation.objects.select_for_update().get(pk=tx.allocation_id) if tx.allocation_id else None
    owner, location = _account_context(account, tx.owner, tx.money_location)
    amount = tx.amount
    if tx.type == TransactionType.EXPENSE:
        if not allocation:
            raise ValidationError('Expense has no allocation to restore.')
        allocation.balance += amount; account.total_balance += amount
        allocation.save(update_fields=['balance', 'updated_at']); account.save(update_fields=['total_balance', 'updated_at'])
        _apply_money_pool_delta(account, owner, location, allocation, amount)
    elif tx.type == TransactionType.DEPOSIT:
        if not allocation or allocation.balance < amount:
            raise ValidationError('Deposit cannot be reverted because the credited funds are no longer available.')
        allocation.balance -= amount; account.total_balance -= amount
        allocation.save(update_fields=['balance', 'updated_at']); account.save(update_fields=['total_balance', 'updated_at'])
        _apply_money_pool_delta(account, owner, location, allocation, -amount)
    elif tx.type in (TransactionType.ALLOCATION, TransactionType.TRANSFER):
        direction = tx.metadata.get('direction')
        if tx.type == TransactionType.ALLOCATION:
            source_type = tx.metadata.get('from'); target_type = tx.metadata.get('to')
            source = Allocation.objects.select_for_update().get(account=account, type=source_type)
            target = Allocation.objects.select_for_update().get(account=account, type=target_type)
            if target.balance < amount:
                raise ValidationError('Transfer cannot be reverted because destination funds were already spent.')
            target.balance -= amount; source.balance += amount
            target.save(update_fields=['balance', 'updated_at']); source.save(update_fields=['balance', 'updated_at'])
            _apply_money_pool_delta(account, owner, location, target, -amount)
            _apply_money_pool_delta(account, owner, location, source, amount)
        else:
            if direction == 'out':
                if allocation and allocation.balance + amount < 0:
                    raise ValidationError('Transfer cannot be reverted because source funds are unavailable.')
                allocation.balance += amount; account.total_balance += amount
                allocation.save(update_fields=['balance', 'updated_at']); account.save(update_fields=['total_balance', 'updated_at'])
                _apply_money_pool_delta(account, owner, location, allocation, amount)
            elif direction == 'in':
                if not allocation or allocation.balance < amount:
                    raise ValidationError('Incoming transfer cannot be reverted because the funds were already spent.')
                allocation.balance -= amount; account.total_balance -= amount
                allocation.save(update_fields=['balance', 'updated_at']); account.save(update_fields=['total_balance', 'updated_at'])
                _apply_money_pool_delta(account, owner, location, allocation, -amount)
    tx.metadata = {**tx.metadata, 'reverted': True, 'reverted_at': str(tx.occurred_at)}
    tx.save(update_fields=['metadata'])
    _assert_account_reconciles(account)
    return tx


@api_view(['POST', 'DELETE'])
def revert_transaction(request, id):
    with transaction.atomic():
        tx = get_object_or_404(Transaction.objects.select_for_update(), id=id)
        if tx.related_tx_id and not tx.metadata.get('reverted'):
            related = Transaction.objects.select_for_update().get(pk=tx.related_tx_id)
            _revert_single_transaction(tx)
            if not related.metadata.get('reverted'):
                _revert_single_transaction(related)
        else:
            _revert_single_transaction(tx)
    return Response({'detail': 'Transaction reverted. It remains in the ledger for audit history.', 'transaction': TransactionSerializer(tx).data})


@api_view(['PATCH', 'PUT'])
def edit_expense(request, id):
    with transaction.atomic():
        tx = get_object_or_404(Transaction.objects.select_for_update(), id=id)
        if tx.type != TransactionType.EXPENSE:
            raise ValidationError('Only expense transactions can be edited from the expense ledger.')
        if tx.metadata.get('reverted'):
            raise ValidationError('A reverted transaction cannot be edited.')
        account = Account.objects.select_for_update().get(pk=tx.account_id)
        allocation = Allocation.objects.select_for_update().get(pk=tx.allocation_id)
        owner, location = _account_context(account, tx.owner, tx.money_location)
        old_amount = tx.amount
        try:
            new_amount = Decimal(str(request.data.get('amount', old_amount)))
        except Exception:
            raise ValidationError({'amount': 'Amount must be a valid number.'})
        if new_amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        category = get_object_or_404(Category, id=request.data.get('category')) if request.data.get('category') else tx.category
        subcategory = get_object_or_404(SubCategory, id=request.data.get('subcategory')) if request.data.get('subcategory') else tx.subcategory
        item = get_object_or_404(Item, id=request.data.get('item')) if request.data.get('item') else tx.item
        _validate_transport(request.data, category)
        delta = new_amount - old_amount
        if delta > 0:
            _check_pool_funds(account, owner, location, allocation, delta)
        else:
            # restoring the old amount first makes a reduction always safe
            pass
        allocation.balance -= delta; account.total_balance -= delta
        allocation.save(update_fields=['balance', 'updated_at']); account.save(update_fields=['total_balance', 'updated_at'])
        _apply_money_pool_delta(account, owner, location, allocation, -delta)
        tx.amount = new_amount
        tx.category = category; tx.subcategory = subcategory; tx.item = item
        tx.variant = str(request.data.get('variant', tx.variant) or '')
        tx.meal = request.data.get('meal', tx.meal) or None
        tx.metadata = _metadata_from_request(request.data) | {'edited': True}
        tx.save(update_fields=['amount', 'category', 'subcategory', 'item', 'variant', 'meal', 'metadata'])
        _assert_account_reconciles(account)
    return Response(TransactionSerializer(tx).data)


@api_view(['GET'])
def enhanced_transaction_list(request):
    qs = Transaction.objects.select_related('account', 'owner', 'money_location', 'allocation', 'category', 'subcategory', 'item').order_by('-occurred_at', '-created_at')
    if request.query_params.get('type'):
        qs = qs.filter(type=request.query_params['type'])
    return Response(TransactionSerializer(qs[:200], many=True).data)


@api_view(['GET'])
def report_data(request):
    qs = Transaction.objects.select_related('category', 'subcategory', 'item', 'account', 'money_location', 'owner').filter(type=TransactionType.EXPENSE)
    category = {}; subcategory = {}; item = {}; payment = {}; transport = {}; meals = {}
    for tx in qs:
        amount = float(tx.amount)
        category[tx.category.name if tx.category else 'Uncategorized'] = category.get(tx.category.name if tx.category else 'Uncategorized', 0) + amount
        subcategory[tx.subcategory.name if tx.subcategory else 'Uncategorized'] = subcategory.get(tx.subcategory.name if tx.subcategory else 'Uncategorized', 0) + amount
        item[tx.item.name if tx.item else (tx.metadata.get('custom_description') or 'Custom / Other')] = item.get(tx.item.name if tx.item else (tx.metadata.get('custom_description') or 'Custom / Other'), 0) + amount
        method = tx.metadata.get('payment_method', 'Not specified'); payment[method] = payment.get(method, 0) + amount
        if tx.metadata.get('transport_from') or tx.metadata.get('transport_to'):
            mode = tx.metadata.get('transport_mode') or 'Transport'; transport[mode] = transport.get(mode, 0) + amount
        if tx.meal: meals[tx.meal] = meals.get(tx.meal, 0) + amount
    return Response({'category': category, 'subcategory': subcategory, 'item': item, 'payment_method': payment, 'transport': transport, 'meal': meals})


@api_view(['POST'])
def enhanced_sql_execute(request):
    raw = str(request.data.get('sql') or '').strip()
    if not raw:
        return Response({'status': 'error', 'message': 'SQL query is required.'}, status=400)
    sql = raw[:-1].strip() if raw.endswith(';') else raw
    if ';' in sql:
        return Response({'status': 'error', 'message': 'Only one SQL statement is allowed.'}, status=400)
    # Strip comments before checking keywords so comments cannot bypass the guard.
    normalized = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.S)
    normalized = re.sub(r'--[^\n]*', ' ', normalized).strip()
    if not re.match(r'^(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN|VALUES)\b', normalized, re.I):
        return Response({'status': 'error', 'message': 'Only read-only SELECT/WITH/SHOW/DESCRIBE/EXPLAIN/VALUES queries are allowed.'}, status=400)
    if re.search(r'\b(DROP|ALTER|DELETE|INSERT|UPDATE|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|COPY|VACUUM|ANALYZE)\b', normalized, re.I):
        return Response({'status': 'error', 'message': 'Write/destructive SQL is blocked.'}, status=400)
    started = perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [c[0] for c in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(500)
            return Response({'status': 'success', 'columns': columns, 'rows': [{c: _json_safe(v) for c, v in zip(columns, row)} for row in rows], 'row_count': len(rows), 'limited': len(rows) == 500, 'execution_time_ms': int((perf_counter() - started) * 1000)})
    except Exception as exc:
        return Response({'status': 'error', 'message': str(exc), 'execution_time_ms': int((perf_counter() - started) * 1000)}, status=400)


@api_view(['GET'])
def sql_schema_data(request):
    with connection.cursor() as cursor:
        names = sorted(t.name for t in connection.introspection.get_table_list(cursor) if t.type == 't')
        tables = []
        for name in names:
            columns = connection.introspection.get_table_description(cursor, name)
            tables.append({'name': name, 'columns': [{'name': c.name, 'type': str(c.type_code), 'nullable': c.null_ok} for c in columns]})
    return Response({'tables': tables})
