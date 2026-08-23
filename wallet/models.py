import uuid

from django.db import models


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    total_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='INR')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class AllocationType(models.TextChoices):
    SPENDABLE = 'spendable', 'Spendable'
    SAVINGS = 'savings', 'Savings'


class Allocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='allocations')
    type = models.CharField(max_length=20, choices=AllocationType.choices)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['account', 'type'], name='unique_account_allocation_type')
        ]

    def __str__(self):
        return f'{self.account.name} - {self.type}'


class TransactionType(models.TextChoices):
    DEPOSIT = 'deposit', 'Deposit'
    EXPENSE = 'expense', 'Expense'
    ALLOCATION = 'allocation', 'Allocation'
    TRANSFER = 'transfer', 'Transfer'


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    allocation = models.ForeignKey(
        Allocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
    )
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    related_tx = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_transactions',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.account.name} - {self.type} - {self.amount}'
