from collections import defaultdict
from datetime import datetime, time
from decimal import Decimal

from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AllocationType, Transaction, TransactionType


def _auth(request):
    if not request.user or not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=401)
    return None


def _date_range(request):
    start_raw = request.query_params.get('date_from', '').strip()
    end_raw = request.query_params.get('date_to', '').strip()
    try:
        start = datetime.strptime(start_raw, '%Y-%m-%d').date() if start_raw else None
        end = datetime.strptime(end_raw, '%Y-%m-%d').date() if end_raw else None
    except ValueError:
        return None, None, {'detail': 'Dates must use YYYY-MM-DD.'}
    return start, end, None


def _savings_transactions(start=None, end=None):
    qs = Transaction.objects.select_related('account', 'owner', 'money_location', 'allocation').order_by('occurred_at', 'created_at')
    # A transaction is a savings movement when the transaction explicitly uses the
    # savings allocation, or when its metadata records an allocation transfer into/out of savings.
    qs = qs.filter(
        Q(allocation__type=AllocationType.SAVINGS) |
        Q(type=TransactionType.TRANSFER, metadata__direction__in=['to_savings', 'to_spendable']) |
        Q(type=TransactionType.ALLOCATION, metadata__from=AllocationType.SAVINGS) |
        Q(type=TransactionType.ALLOCATION, metadata__to=AllocationType.SAVINGS)
    )
    if start:
        qs = qs.filter(occurred_at__date__gte=start)
    if end:
        qs = qs.filter(occurred_at__date__lte=end)
    return qs


def _movement(tx):
    md = tx.metadata or {}
    if tx.type == TransactionType.TRANSFER and md.get('direction') == 'to_savings':
        return 'inflow', 'transfer_to_savings'
    if tx.type == TransactionType.TRANSFER and md.get('direction') == 'to_spendable':
        return 'outflow', 'withdrawal_from_savings'
    if tx.type == TransactionType.ALLOCATION and md.get('to') == AllocationType.SAVINGS:
        return 'inflow', 'allocation_to_savings'
    if tx.type == TransactionType.ALLOCATION and md.get('from') == AllocationType.SAVINGS:
        return 'outflow', 'allocation_from_savings'
    if tx.type == TransactionType.DEPOSIT and tx.allocation and tx.allocation.type == AllocationType.SAVINGS:
        return 'inflow', 'deposit_to_savings'
    if tx.type == TransactionType.EXPENSE and tx.allocation and tx.allocation.type == AllocationType.SAVINGS:
        return 'outflow', 'expense_from_savings'
    return None, None


def _decimal(value):
    return value.quantize(Decimal('0.01'))


def savings_page(request):
    return render(request, 'savings.html')


@api_view(['GET'])
def savings_analytics(request):
    auth = _auth(request)
    if auth:
        return auth
    start, end, error = _date_range(request)
    if error:
        return Response(error, status=400)

    qs = _savings_transactions(start, end)
    inflow = Decimal('0')
    outflow = Decimal('0')
    rows = []
    by_type = defaultdict(lambda: {'inflow': Decimal('0'), 'outflow': Decimal('0'), 'count': 0})
    by_wallet = defaultdict(lambda: {'inflow': Decimal('0'), 'outflow': Decimal('0'), 'net': Decimal('0'), 'count': 0})
    by_location = defaultdict(lambda: {'inflow': Decimal('0'), 'outflow': Decimal('0'), 'net': Decimal('0'), 'count': 0})
    by_period = defaultdict(lambda: {'inflow': Decimal('0'), 'outflow': Decimal('0'), 'net': Decimal('0'), 'count': 0})

    for tx in qs:
        direction, movement = _movement(tx)
        if not direction:
            continue
        amount = Decimal(tx.amount)
        if direction == 'inflow':
            inflow += amount
        else:
            outflow += amount
        bucket = by_type[movement]
        bucket[direction] += amount
        bucket['count'] += 1
        wallet = by_wallet[tx.account.name]
        wallet[direction] += amount
        wallet['net'] += amount if direction == 'inflow' else -amount
        wallet['count'] += 1
        location_name = tx.money_location.name if tx.money_location else 'Unknown'
        location = by_location[location_name]
        location[direction] += amount
        location['net'] += amount if direction == 'inflow' else -amount
        location['count'] += 1
        period = timezone.localtime(tx.occurred_at).strftime('%Y-%m')
        month = by_period[period]
        month[direction] += amount
        month['net'] += amount if direction == 'inflow' else -amount
        month['count'] += 1
        rows.append({
            'id': str(tx.id), 'date': timezone.localtime(tx.occurred_at).isoformat(),
            'account': tx.account.name, 'owner': tx.owner.name if tx.owner else None,
            'location': location_name, 'amount': str(_decimal(amount)),
            'direction': direction, 'movement': movement, 'type': tx.type,
            'metadata': tx.metadata or {},
        })

    net = inflow - outflow
    # Savings rate measures the net amount retained from money deposited into the workspace.
    deposit_total = Transaction.objects.filter(type=TransactionType.DEPOSIT).filter(
        occurred_at__date__gte=start if start else datetime.min.date(),
        occurred_at__date__lte=end if end else datetime.max.date(),
    ).aggregate_total if False else None
    deposits = Transaction.objects.filter(type=TransactionType.DEPOSIT)
    if start:
        deposits = deposits.filter(occurred_at__date__gte=start)
    if end:
        deposits = deposits.filter(occurred_at__date__lte=end)
    deposit_total = sum((Decimal(x.amount) for x in deposits), Decimal('0'))
    rate = (net / deposit_total * Decimal('100')) if deposit_total else Decimal('0')

    def serialise_map(data):
        return [
            {'name': name, 'inflow': str(_decimal(v['inflow'])), 'outflow': str(_decimal(v['outflow'])),
             'net': str(_decimal(v.get('net', v['inflow'] - v['outflow']))), 'count': v['count']}
            for name, v in sorted(data.items())
        ]

    periods = [
        {'period': name, 'inflow': str(_decimal(v['inflow'])), 'outflow': str(_decimal(v['outflow'])),
         'net': str(_decimal(v['net'])), 'count': v['count']}
        for name, v in sorted(by_period.items())
    ]
    return Response({
        'period': {'date_from': start.isoformat() if start else None, 'date_to': end.isoformat() if end else None},
        'overview': {'inflow': str(_decimal(inflow)), 'outflow': str(_decimal(outflow)), 'net_savings': str(_decimal(net)), 'deposit_base': str(_decimal(deposit_total)), 'savings_rate_percent': str(_decimal(rate)), 'movement_count': len(rows)},
        'activity': rows,
        'by_movement': serialise_map(by_type),
        'by_wallet': serialise_map(by_wallet),
        'by_location': serialise_map(by_location),
        'periods': periods,
    })
