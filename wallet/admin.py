from django.contrib import admin

from .models import Account, Allocation, Category, FoodProfile, Item, MoneyLocation, MoneyPool, Owner, QueryExecutionLog, SavedQuery, SubCategory, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'currency', 'total_balance', 'created_at')
    search_fields = ('name',)


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ('account', 'type', 'balance', 'updated_at')
    list_filter = ('type',)
    search_fields = ('account__name',)


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_at')
    search_fields = ('name',)


@admin.register(MoneyLocation)
class MoneyLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_type', 'active', 'created_at')
    list_filter = ('location_type', 'active')
    search_fields = ('name',)


@admin.register(MoneyPool)
class MoneyPoolAdmin(admin.ModelAdmin):
    list_display = ('owner', 'location', 'allocation_type', 'current_amount', 'updated_at')
    list_filter = ('owner', 'location', 'allocation_type')
    search_fields = ('owner__name', 'location__name', 'allocation_type')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('category', 'name', 'created_at')
    list_filter = ('category',)
    search_fields = ('name', 'category__name')


@admin.register(FoodProfile)
class FoodProfileAdmin(admin.ModelAdmin):
    list_display = ('item', 'food_group', 'health_classification', 'sugary', 'updated_at')
    list_filter = ('food_group', 'health_classification', 'sugary')
    search_fields = ('item__name',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('category', 'subcategory', 'name', 'is_custom', 'created_at')
    list_filter = ('category', 'subcategory', 'is_custom')
    search_fields = ('name', 'category__name', 'subcategory__name')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'owner', 'money_location', 'type', 'amount', 'allocation', 'category', 'item', 'meal', 'created_at')
    list_filter = ('type', 'category', 'owner', 'money_location', 'meal')
    search_fields = ('account__name', 'metadata', 'owner__name', 'money_location__name')


@admin.register(SavedQuery)
class SavedQueryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name', 'sql')


@admin.register(QueryExecutionLog)
class QueryExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('status', 'execution_time_ms', 'created_at')
    list_filter = ('status',)
    search_fields = ('query', 'error_message')
