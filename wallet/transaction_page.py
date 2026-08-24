from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def enhanced_transaction_page(request):
    return render(request, 'transactions_enhanced.html')
