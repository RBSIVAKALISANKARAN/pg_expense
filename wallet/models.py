import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AppSetting(models.Model):
    """Persistent application preferences for the single PG Expense workspace."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.key}={self.value}'


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    money_location = models.ForeignKey(
        'MoneyLocation', on_delete=models.PROTECT, null=True, blank=True,
        related_name='accounts',
    )
    total_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=10, default='INR')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=Q(total_balance__gte=0), name='account_total_non_negative'),
        ]

    def __str__(self):
        return self.name


class AllocationType(models.TextChoices):
    SPENDABLE = 'spendable', 'Spendable'
    SAVINGS = 'savings', 'Savings'


class Allocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='allocations')
    type = models.CharField(max_length=20, choices=AllocationType.choices)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                  validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['account', 'type'], name='unique_account_allocation_type'),
            models.CheckConstraint(condition=Q(balance__gte=0), name='allocation_balance_non_negative'),
        ]

    def __str__(self):
        return f'{self.account.name} - {self.type}'


class Owner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MoneyLocationType(models.TextChoices):
    BANK = 'bank', 'Bank'
    CASH = 'cash', 'Cash'
    TRAVEL_CARD = 'travel_card', 'Travel Card'
    CHANGE_CASH = 'change_cash', 'Change Cash'


class MoneyLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    location_type = models.CharField(max_length=20, choices=MoneyLocationType.choices, default=MoneyLocationType.BANK)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MoneyPool(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='money_pools')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='money_pools')
    location = models.ForeignKey(MoneyLocation, on_delete=models.CASCADE, related_name='money_pools')
    allocation_type = models.CharField(max_length=20, choices=AllocationType.choices)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                         validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['owner__name', 'location__name', 'allocation_type']
        constraints = [
            models.UniqueConstraint(
                fields=['account', 'owner', 'location', 'allocation_type'],
                name='unique_account_owner_location_allocation_pool',
            ),
            models.CheckConstraint(condition=Q(current_amount__gte=0), name='money_pool_amount_non_negative'),
        ]

    def __str__(self):
        return f'{self.owner.name} | {self.location.name} | {self.allocation_type}'


class TransactionType(models.TextChoices):
    DEPOSIT = 'deposit', 'Deposit'
    EXPENSE = 'expense', 'Expense'
    ALLOCATION = 'allocation', 'Allocation'
    TRANSFER = 'transfer', 'Transfer'


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['category', 'name'], name='unique_category_subcategory_name')
        ]

    def __str__(self):
        return f'{self.category.name} - {self.name}'


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    is_custom = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__name', 'subcategory__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['category', 'subcategory', 'name'], name='unique_category_subcategory_item_name')
        ]

    def __str__(self):
        return f'{self.category.name} - {self.name}'


class FoodGroup(models.TextChoices):
    MAIN_MEAL = 'main_meal', 'Main Meal'
    SNACK = 'snack', 'Snack'
    BAKERY = 'bakery', 'Bakery'
    BEVERAGE = 'beverage', 'Beverage'
    FRUIT = 'fruit', 'Fruit'
    OTHER = 'other', 'Other'


class HealthClassification(models.TextChoices):
    HEALTHY = 'healthy', 'Healthy'
    MODERATE = 'moderate', 'Moderate'
    UNHEALTHY = 'unhealthy', 'Unhealthy'
    UNKNOWN = 'unknown', 'Unknown'


class SugaryClassification(models.TextChoices):
    YES = 'yes', 'Yes'
    NO = 'no', 'No'
    UNKNOWN = 'unknown', 'Unknown'


class FoodProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='food_profile')
    food_group = models.CharField(max_length=30, choices=FoodGroup.choices, default=FoodGroup.OTHER)
    health_classification = models.CharField(max_length=30, choices=HealthClassification.choices, default=HealthClassification.UNKNOWN)
    sugary = models.CharField(max_length=10, choices=SugaryClassification.choices, default=SugaryClassification.UNKNOWN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Food profile: {self.item.name}'


class MealType(models.TextChoices):
    BREAKFAST = 'breakfast', 'Breakfast'
    LUNCH = 'lunch', 'Lunch'
    DINNER = 'dinner', 'Dinner'
    SNACK = 'snack', 'Snack'
    OTHER = 'other', 'Other'


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT, related_name='transactions')
    money_location = models.ForeignKey(MoneyLocation, on_delete=models.PROTECT, related_name='transactions')
    allocation = models.ForeignKey(Allocation, on_delete=models.PROTECT, related_name='transactions', null=True, blank=True)
    source_pool = models.ForeignKey(MoneyPool, on_delete=models.PROTECT, related_name='transactions', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True, related_name='transactions')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.PROTECT, null=True, blank=True, related_name='transactions')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, null=True, blank=True, related_name='transactions')
    variant = models.CharField(max_length=200, blank=True, default='')
    meal = models.CharField(max_length=30, choices=MealType.choices, blank=True, default='')
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    related_tx = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='related_transaction')

    class Meta:
        ordering = ['-occurred_at', '-created_at']
        indexes = [
            models.Index(fields=['account', '-occurred_at']),
            models.Index(fields=['type', '-occurred_at']),
        ]

    def __str__(self):
        return f'{self.type}: {self.amount}'


class FoodEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='food_event')
    meal = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)


class FoodEventItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(FoodEvent, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, null=True, blank=True, related_name='food_event_items')
    custom_name = models.CharField(max_length=200, blank=True, default='')
    variant = models.CharField(max_length=200, blank=True, default='')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, validators=[MinValueValidator(0)])


class QueryExecutionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.TextField()
    status = models.CharField(max_length=20)
    row_count = models.IntegerField(default=0)
    execution_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class SavedQuery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    sql = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
