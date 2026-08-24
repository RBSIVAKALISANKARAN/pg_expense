from datetime import datetime, time

from django.db import connection
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Account, Category, Owner, AllocationType, QueryExecutionLog,
    SavedQuery, SubCategory, Item, Transaction, TransactionType,
)
from .serializers import TransactionSerializer
from .views import _validate_sql_for_execution


def _auth(request):
    if not request.user or not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
    return None


@api_view(['GET'])
def phase4_transaction_list(request):
    auth = _auth(request)
    if auth:
        return auth
    qs = Transaction.objects.select_related('account', 'owner', 'money_location', 'allocation', 'category', 'subcategory', 'item').order_by('-occurred_at', '-created_at')
    params = request.query_params
    search = params.get('search', '').strip()
    if search:
        query = (Q(account__name__icontains=search) | Q(owner__name__icontains=search) | Q(money_location__name__icontains=search) |
                 Q(category__name__icontains=search) | Q(subcategory__name__icontains=search) | Q(item__name__icontains=search) |
                 Q(variant__icontains=search) | Q(metadata__merchant__icontains=search) | Q(metadata__note__icontains=search) |
                 Q(metadata__custom_description__icontains=search) | Q(type__icontains=search))
        try:
            query |= Q(amount=search)
        except Exception:
            pass
        qs = qs.filter(query)
    for key, field in (('account', 'account_id'), ('owner', 'owner_id'), ('type', 'type'), ('category', 'category_id'), ('subcategory', 'subcategory_id'), ('allocation', 'allocation__type')):
        value = params.get(key, '').strip()
        if value:
            qs = qs.filter(**{field: value})
    date_from, date_to = params.get('date_from', '').strip(), params.get('date_to', '').strip()
    try:
        if date_from:
            qs = qs.filter(occurred_at__gte=timezone.make_aware(datetime.combine(datetime.strptime(date_from, '%Y-%m-%d').date(), time.min)))
        if date_to:
            qs = qs.filter(occurred_at__lte=timezone.make_aware(datetime.combine(datetime.strptime(date_to, '%Y-%m-%d').date(), time.max)))
    except ValueError:
        return Response({'detail': 'Dates must use YYYY-MM-DD.'}, status=400)
    try:
        limit = min(max(int(params.get('limit', '200')), 1), 500)
    except ValueError:
        limit = 200
    data = TransactionSerializer(qs[:limit], many=True).data
    return Response({'count': len(data), 'filters': dict(params), 'results': data})


@api_view(['GET'])
def phase4_transaction_filter_options(request):
    auth = _auth(request)
    if auth:
        return auth
    return Response({
        'accounts': [{'id': str(x.id), 'name': x.name} for x in Account.objects.all()],
        'owners': [{'id': str(x.id), 'name': x.name} for x in Owner.objects.filter(active=True)],
        'types': [{'value': value, 'label': label} for value, label in TransactionType.choices],
        'categories': [{'id': str(x.id), 'name': x.name} for x in Category.objects.all()],
        'subcategories': [{'id': str(x.id), 'name': x.name, 'category': str(x.category_id)} for x in SubCategory.objects.select_related('category').all()],
        'items': [{'id': str(x.id), 'name': x.name, 'category': str(x.category_id), 'subcategory': str(x.subcategory_id) if x.subcategory_id else ''} for x in Item.objects.all()],
        'allocations': [{'value': value, 'label': label} for value, label in AllocationType.choices],
    })


@api_view(['GET'])
def phase4_sql_history(request):
    auth = _auth(request)
    if auth:
        return auth
    logs = QueryExecutionLog.objects.all()[:50]
    return Response([{'id': str(x.id), 'query': x.query, 'status': x.status, 'execution_time_ms': x.execution_time_ms, 'error_message': x.error_message, 'created_at': x.created_at.isoformat()} for x in logs])


@api_view(['GET', 'POST', 'DELETE'])
def phase4_saved_queries(request, id=None):
    auth = _auth(request)
    if auth:
        return auth
    if request.method == 'GET':
        if id:
            query = SavedQuery.objects.filter(id=id).first()
            if not query:
                return Response({'detail': 'Saved query not found.'}, status=404)
            return Response({'id': str(query.id), 'name': query.name, 'description': query.description, 'sql': query.sql, 'created_at': query.created_at.isoformat()})
        return Response([{'id': str(x.id), 'name': x.name, 'description': x.description, 'sql': x.sql, 'created_at': x.created_at.isoformat()} for x in SavedQuery.objects.all()[:50]])
    if request.method == 'DELETE':
        query = SavedQuery.objects.filter(id=id).first()
        if not query:
            return Response({'detail': 'Saved query not found.'}, status=404)
        query.delete()
        return Response({'detail': 'Saved query deleted.'})
    name, sql, description = str(request.data.get('name') or 'Untitled query').strip(), str(request.data.get('sql') or '').strip(), str(request.data.get('description') or '').strip()
    if not sql:
        return Response({'detail': 'SQL is required.'}, status=400)
    try:
        sql = _validate_sql_for_execution(sql)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
    query = SavedQuery.objects.create(name=name[:200], description=description, sql=sql)
    return Response({'id': str(query.id), 'name': query.name, 'description': query.description, 'sql': query.sql}, status=201)


@api_view(['GET'])
def phase4_sql_schema(request):
    auth = _auth(request)
    if auth:
        return auth
    with connection.cursor() as cursor:
        names = sorted(t.name for t in connection.introspection.get_table_list(cursor) if t.type == 't')
        tables = []
        for name in names:
            columns = connection.introspection.get_table_description(cursor, name)
            tables.append({'name': name, 'columns': [{'name': c.name, 'type': str(c.type_code), 'nullable': c.null_ok} for c in columns]})
    return Response({'tables': tables})
