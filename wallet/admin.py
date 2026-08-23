from django.contrib import admin

from .models import Account, Allocation, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'currency', 'total_balance', 'created_at')
    search_fields = ('name',)


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ('account', 'type', 'balance', 'updated_at')
    list_filter = ('type',)
    search_fields = ('account__name',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'type', 'amount', 'allocation', 'created_at')
    list_filter = ('type',)
    search_fields = ('account__name', 'metadata')
