import os
import re
from decimal import Decimal
from time import perf_counter

from django.db import connection, transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import QueryExecutionLog

FORBIDDEN_SQL_PATTERNS = (
    r'\bDROP\b', r'\bALTER\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
    r'\bCREATE\b', r'\bTRUNCATE\b', r'\bGRANT\b', r'\bREVOKE\b', r'\bEXEC\b',
    r'\bCOPY\b', r'\bVACUUM\b', r'\bANALYZE\b',
)
ALLOWED_SQL_PREFIXES = {'SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'VALUES'}
SQL_PLAYGROUND_TIMEOUT_MS = max(100, int(os.getenv('SQL_PLAYGROUND_TIMEOUT_MS', '5000')))
SQL_PLAYGROUND_MAX_ROWS = max(1, int(os.getenv('SQL_PLAYGROUND_MAX_ROWS', '500')))


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def _validate_sql(raw_sql):
    if raw_sql is None:
        raise ValueError('SQL query is required.')
    sql = raw_sql.strip()
    if not sql:
        raise ValueError('SQL query is required.')
    if sql.count(';') > 1:
        raise ValueError('Only a single SQL statement is allowed.')
    sql = sql[:-1] if sql.endswith(';') else sql
    if not sql:
        raise ValueError('SQL query is required.')
    if any(re.search(pattern, sql, re.IGNORECASE) for pattern in FORBIDDEN_SQL_PATTERNS):
        raise ValueError('Only read-only SQL queries are allowed in the playground.')
    prefix = sql.split(None, 1)[0].upper()
    if prefix not in ALLOWED_SQL_PREFIXES:
        raise ValueError('Only SELECT, WITH, SHOW, DESCRIBE, EXPLAIN, and VALUES queries are allowed.')
    return sql


@api_view(['POST'])
def sql_execute_secure(request):
    raw_sql = request.data.get('sql', '') if isinstance(request.data, dict) else ''
    started = perf_counter()
    try:
        sql = _validate_sql(raw_sql)
    except ValueError as exc:
        QueryExecutionLog.objects.create(query=str(raw_sql), status='error', execution_time_ms=0, error_message=str(exc))
        return Response({'status': 'error', 'message': str(exc), 'execution_time_ms': 0}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # The SQL itself runs inside a PostgreSQL-enforced READ ONLY transaction.
        # SET TRANSACTION must be the first statement in the transaction.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION READ ONLY')
                cursor.execute('SET LOCAL statement_timeout = %s', [SQL_PLAYGROUND_TIMEOUT_MS])
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description] if cursor.description else []
                rows = cursor.fetchmany(SQL_PLAYGROUND_MAX_ROWS + 1) if columns else []

        truncated = len(rows) > SQL_PLAYGROUND_MAX_ROWS
        rows = rows[:SQL_PLAYGROUND_MAX_ROWS]
        safe_rows = [{col: _json_safe(value) for col, value in zip(columns, row)} for row in rows] if columns else []
        execution_time_ms = int((perf_counter() - started) * 1000)
        QueryExecutionLog.objects.create(query=sql, status='success', execution_time_ms=execution_time_ms)
        return Response({
            'status': 'success',
            'message': 'Query executed successfully.' + (' Result set truncated at the configured row limit.' if truncated else ''),
            'columns': columns,
            'rows': safe_rows,
            'row_count': len(rows),
            'truncated': truncated,
            'max_rows': SQL_PLAYGROUND_MAX_ROWS,
            'execution_time_ms': execution_time_ms,
        })
    except Exception as exc:
        execution_time_ms = int((perf_counter() - started) * 1000)
        QueryExecutionLog.objects.create(query=sql, status='error', execution_time_ms=execution_time_ms, error_message=str(exc))
        return Response({'status': 'error', 'message': 'Query execution failed.', 'detail': str(exc), 'execution_time_ms': execution_time_ms}, status=status.HTTP_400_BAD_REQUEST)
