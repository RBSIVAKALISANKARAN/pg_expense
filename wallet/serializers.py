from decimal import Decimal

from rest_framework import serializers

from .models import Account, Allocation, Transaction


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        fields = ['id', 'type', 'balance']


class AccountSerializer(serializers.ModelSerializer):
    allocations = AllocationSerializer(many=True, read_only=True)

    class Meta:
        model = Account
        fields = ['id', 'name', 'currency', 'total_balance', 'allocations', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'name', 'currency']
        read_only_fields = ['id']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Account name is required.')
        return value.strip()


class MoneyActionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


class DepositSerializer(MoneyActionSerializer):
    allocate_to_savings = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_allocate_to_savings(self, value):
        if value < Decimal('0'):
            raise serializers.ValidationError('Savings allocation cannot be negative.')
        return value


class AllocationTransferSerializer(serializers.Serializer):
    from_type = serializers.ChoiceField(choices=['spendable', 'savings'])
    to_type = serializers.ChoiceField(choices=['spendable', 'savings'])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate(self, data):
        if data['from_type'] == data['to_type']:
            raise serializers.ValidationError('Source and destination allocation cannot be the same.')
        return data


class ExpenseSerializer(MoneyActionSerializer):
    allocation = serializers.ChoiceField(choices=['spendable', 'savings'])
    merchant = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)


class TransactionSerializer(serializers.ModelSerializer):
    allocation_type = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['id', 'account', 'allocation', 'allocation_type', 'type', 'amount', 'metadata', 'created_at', 'related_tx']

    def get_allocation_type(self, obj):
        return obj.allocation.type if obj.allocation else None
