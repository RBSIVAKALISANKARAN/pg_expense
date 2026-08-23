from decimal import Decimal

from rest_framework import serializers

from .models import (
    Account,
    Allocation,
    Category,
    FoodGroup,
    FoodProfile,
    HealthClassification,
    Item,
    MoneyLocation,
    Owner,
    SugaryStatus,
    SubCategory,
    Transaction,
)


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        fields = ['id', 'type', 'balance']


class AccountSerializer(serializers.ModelSerializer):
    allocations = AllocationSerializer(many=True, read_only=True)
    location_name = serializers.CharField(source='money_location.name', read_only=True)

    class Meta:
        model = Account
        fields = ['id', 'name', 'currency', 'money_location', 'location_name', 'total_balance', 'allocations', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateAccountSerializer(serializers.ModelSerializer):
    money_location = serializers.PrimaryKeyRelatedField(
        queryset=MoneyLocation.objects.filter(active=True), required=False, allow_null=True
    )
    class Meta:
        model = Account
        fields = ['id', 'name', 'currency', 'money_location']
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
    owner = serializers.PrimaryKeyRelatedField(queryset=Owner.objects.filter(active=True), required=False, allow_null=True)
    money_location = serializers.PrimaryKeyRelatedField(queryset=MoneyLocation.objects.filter(active=True), required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_allocate_to_savings(self, value):
        if value < Decimal('0'):
            raise serializers.ValidationError('Savings allocation cannot be negative.')
        return value


class AllocationTransferSerializer(serializers.Serializer):
    from_type = serializers.ChoiceField(choices=['spendable', 'savings'])
    to_type = serializers.ChoiceField(choices=['spendable', 'savings'])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    owner = serializers.PrimaryKeyRelatedField(queryset=Owner.objects.filter(active=True), required=False, allow_null=True)
    money_location = serializers.PrimaryKeyRelatedField(queryset=MoneyLocation.objects.filter(active=True), required=False, allow_null=True)

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate(self, data):
        if data['from_type'] == data['to_type']:
            raise serializers.ValidationError('Source and destination allocation cannot be the same.')
        return data


class TransferSerializer(MoneyActionSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=Owner.objects.filter(active=True), required=False, allow_null=True)
    money_location = serializers.PrimaryKeyRelatedField(queryset=MoneyLocation.objects.filter(active=True), required=False, allow_null=True)


class ExpenseSerializer(MoneyActionSerializer):
    allocation = serializers.ChoiceField(choices=['spendable', 'savings'], required=False, default='spendable')
    owner = serializers.PrimaryKeyRelatedField(queryset=Owner.objects.filter(active=True), required=False, allow_null=True)
    money_location = serializers.PrimaryKeyRelatedField(queryset=MoneyLocation.objects.filter(active=True), required=False, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    subcategory = serializers.PrimaryKeyRelatedField(queryset=SubCategory.objects.all(), required=False, allow_null=True)
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), required=False, allow_null=True)
    custom_description = serializers.CharField(required=False, allow_blank=True, max_length=500)
    variant = serializers.CharField(required=False, allow_blank=True, max_length=200)
    merchant = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    meal = serializers.ChoiceField(choices=['breakfast', 'lunch', 'dinner', 'snack', 'other'], required=False, allow_null=True)
    occurred_at = serializers.DateTimeField(required=False)
    food_items = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=False)

    def validate(self, data):
        category, subcategory, item = data.get('category'), data.get('subcategory'), data.get('item')
        if subcategory and (not category or subcategory.category_id != category.id):
            raise serializers.ValidationError({'subcategory': 'Subcategory must belong to the selected category.'})
        if item and category and item.category_id != category.id:
            raise serializers.ValidationError({'item': 'Item must belong to the selected category.'})
        if item and subcategory and item.subcategory_id not in (None, subcategory.id):
            raise serializers.ValidationError({'item': 'Item must belong to the selected subcategory.'})
        return data


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'category_name', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ['id', 'category', 'category_name', 'subcategory', 'subcategory_name', 'name', 'description', 'is_custom', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None


class FoodProfileSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()

    class Meta:
        model = FoodProfile
        fields = ['id', 'item', 'item_name', 'food_group', 'health_classification', 'sugary', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_item_name(self, obj):
        return obj.item.name if obj.item else None


class TransactionSerializer(serializers.ModelSerializer):
    allocation_type = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()
    item_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['id', 'account', 'owner', 'owner_name', 'money_location', 'location_name', 'allocation', 'allocation_type', 'category', 'category_name', 'subcategory', 'subcategory_name', 'item', 'item_name', 'variant', 'meal', 'type', 'amount', 'metadata', 'created_at', 'occurred_at', 'related_tx']

    def get_allocation_type(self, obj):
        return obj.allocation.type if obj.allocation else None

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None

    def get_item_name(self, obj):
        return obj.item.name if obj.item else None

    def get_owner_name(self, obj):
        return obj.owner.name if obj.owner else None

    def get_location_name(self, obj):
        return obj.money_location.name if obj.money_location else None
