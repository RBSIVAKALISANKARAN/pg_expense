from django.shortcuts import render


def enhanced_transaction_page(request):
    return render(request, 'transactions_enhanced.html')
