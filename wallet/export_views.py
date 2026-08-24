from django.http import HttpResponse

from .reporting import export_account_csv


def export_report(request, id):
    """Expose the CSV builder through a real HTTP response."""
    csv_content = export_account_csv(id)
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="account-{id}.csv"'
    return response
