import csv
import io
from collections import defaultdict
from datetime import datetime

from django.db.models import Sum
from django.utils import timezone

from .models import Transaction, TransactionType


def summarize_account_transactions(account, start_date=None, end_date=None):
    qs = Transaction.objects.filter(account=account)
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    data = {
        'total_income': '0.00',
        'total_expenses': '0.00',
        'net': '0.00',
        'by_type': defaultdict(float),
    }

    income = qs.filter(type=TransactionType.DEPOSIT).aggregate(total=Sum('amount'))['total'] or 0
    expenses = qs.filter(type=TransactionType.EXPENSE).aggregate(total=Sum('amount'))['total'] or 0
    transfers = qs.filter(type=TransactionType.TRANSFER).aggregate(total=Sum('amount'))['total'] or 0

    data['total_income'] = f'{float(income):.2f}'
    data['total_expenses'] = f'{float(expenses):.2f}'
    data['net'] = f'{float(income - expenses):.2f}'
    data['by_type']['deposit'] = float(income)
    data['by_type']['expense'] = float(expenses)
    data['by_type']['transfer'] = float(transfers)
    return data


def export_account_csv(account, start_date=None, end_date=None):
    qs = Transaction.objects.filter(account=account).order_by('-created_at')
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['id', 'type', 'amount', 'allocation', 'allocation_type', 'created_at', 'metadata'])
    for txn in qs:
        writer.writerow([
            str(txn.id),
            txn.type,
            str(txn.amount),
            str(txn.allocation_id or ''),
            txn.allocation.type if txn.allocation else '',
            txn.created_at.isoformat(),
            str(txn.metadata),
        ])
    return csv_buffer.getvalue()
