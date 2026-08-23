from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.schemas import get_schema_view
from django.http import HttpResponse
from pathlib import Path

from .models import Account, Allocation, AllocationType, Transaction, TransactionType
from .serializers import (
    AccountSerializer,
    AllocationTransferSerializer,
    CreateAccountSerializer,
    DepositSerializer,
    ExpenseSerializer,
    MoneyActionSerializer,
    TransactionSerializer,
)

# schema view (OpenAPI)
schema_view = get_schema_view(title='Expense API', description='API for the Expense app', version='1.0.0')


def _ensure_allocations(account):
    for allocation_type in [AllocationType.SPENDABLE, AllocationType.SAVINGS]:
        Allocation.objects.get_or_create(account=account, type=allocation_type)
    return account.allocations.all()


@api_view(['GET', 'POST'])
def account_list_create(request):
    if request.method == 'GET':
        accounts = Account.objects.all()
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)

    serializer = CreateAccountSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    account = serializer.save()
    _ensure_allocations(account)
    return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def account_detail(request, id):
    account = get_object_or_404(Account, id=id)
    _ensure_allocations(account)
    serializer = AccountSerializer(account)
    return Response(serializer.data)


@api_view(['POST'])
def deposit_funds(request, id):
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']
    allocate_to_savings = serializer.validated_data.get('allocate_to_savings', Decimal('0'))
    if allocate_to_savings > amount:
        return Response({'detail': 'Savings allocation cannot exceed deposit amount.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        # Update using F() for atomic arithmetic
        account.total_balance = F('total_balance') + amount
        if allocate_to_savings > 0:
            savings.balance = F('balance') + allocate_to_savings
            spendable.balance = F('balance') + (amount - allocate_to_savings)
        else:
            spendable.balance = F('balance') + amount

        # Save changes
        account.save(update_fields=['total_balance'])
        spendable.save(update_fields=['balance'])
        savings.save(update_fields=['balance'])

        # Refresh from db to get resolved F() values
        account.refresh_from_db()
        spendable.refresh_from_db()
        savings.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=savings if allocate_to_savings > 0 else spendable,
            type=TransactionType.DEPOSIT,
            amount=amount,
            metadata={'note': serializer.validated_data.get('note', ''), 'allocate_to_savings': str(allocate_to_savings)},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def allocate_funds(request, id):
    serializer = AllocationTransferSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']
    source_type = serializer.validated_data['from_type']
    target_type = serializer.validated_data['to_type']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        source = Allocation.objects.select_for_update().get(account=account, type=source_type)
        target = Allocation.objects.select_for_update().get(account=account, type=target_type)

        if source.balance < amount:
            return Response({'detail': f'Not enough balance in {source_type} allocation.'}, status=status.HTTP_400_BAD_REQUEST)

        source.balance = F('balance') - amount
        target.balance = F('balance') + amount
        source.save(update_fields=['balance'])
        target.save(update_fields=['balance'])
        source.refresh_from_db()
        target.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=source,
            type=TransactionType.ALLOCATION,
            amount=amount,
            metadata={'from': source_type, 'to': target_type},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def expense_create(request, id):
    serializer = ExpenseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']
    allocation_type = serializer.validated_data['allocation']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        allocation = Allocation.objects.select_for_update().get(account=account, type=allocation_type)

        if allocation.balance < amount:
            return Response({'detail': f'Insufficient funds in {allocation_type} allocation.'}, status=status.HTTP_400_BAD_REQUEST)

        allocation.balance = F('balance') - amount
        account.total_balance = F('total_balance') - amount
        allocation.save(update_fields=['balance'])
        account.save(update_fields=['total_balance'])
        allocation.refresh_from_db()
        account.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=allocation,
            type=TransactionType.EXPENSE,
            amount=amount,
            metadata={'merchant': serializer.validated_data.get('merchant', ''), 'note': serializer.validated_data.get('note', '')},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_to_savings(request, id):
    serializer = MoneyActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        if spendable.balance < amount:
            return Response({'detail': 'Not enough spendable funds to transfer to savings.'}, status=status.HTTP_400_BAD_REQUEST)

        spendable.balance = F('balance') - amount
        savings.balance = F('balance') + amount
        spendable.save(update_fields=['balance'])
        savings.save(update_fields=['balance'])
        spendable.refresh_from_db()
        savings.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=savings,
            type=TransactionType.TRANSFER,
            amount=amount,
            metadata={'direction': 'to_savings'},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_to_spendable(request, id):
    serializer = MoneyActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        if savings.balance < amount:
            return Response({'detail': 'Not enough savings funds to transfer to spendable.'}, status=status.HTTP_400_BAD_REQUEST)

        savings.balance = F('balance') - amount
        spendable.balance = F('balance') + amount
        savings.save(update_fields=['balance'])
        spendable.save(update_fields=['balance'])
        savings.refresh_from_db()
        spendable.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=spendable,
            type=TransactionType.TRANSFER,
            amount=amount,
            metadata={'direction': 'to_spendable'},
        )

    return Response(AccountSerializer(account).data)


@api_view(['GET'])
def transactions_list(request, id):
    account = get_object_or_404(Account, id=id)
    qs = Transaction.objects.filter(account=account).order_by('-created_at')
    serializer = TransactionSerializer(qs, many=True)
    return Response(serializer.data)


# Minimal dashboard view
from django.middleware.csrf import get_token

def dashboard(request):
    # ensure CSRF cookie is set for the page so fetch POST works from browser
    get_token(request)
    return render(request, 'dashboard.html')


# Serve the API_DOCS.md as a simple HTML page
def docs(request):
    docs_path = Path(__file__).resolve().parent.parent / 'API_DOCS.md'
    if not docs_path.exists():
        return HttpResponse('API documentation not found', status=404)
    text = docs_path.read_text(encoding='utf-8')
    # Basic HTML escape and preformat
    from html import escape
    body = '<html><head><meta charset="utf-8"><title>API Docs</title></head><body><pre style="white-space:pre-wrap;">' + escape(text) + '</pre></body></html>'
    return HttpResponse(body, content_type='text/html')
