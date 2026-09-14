from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.schemas import get_schema_view

from .models import (
    Account,
    Allocation,
    AllocationType,
    Category,
    FoodProfile,
    Item,
    MoneyLocation,
    MoneyPool,
    Owner,
    SubCategory,
    Transaction,
    TransactionType,
)
from .pagination import StandardResultsSetPagination
from .reporting import summarize_account_transactions
from .serializers import (
    AccountSerializer,
    CategorySerializer,
    CreateAccountSerializer,
    ExpenseSerializer,
    FoodProfileSerializer,
    ItemSerializer,
    SubCategorySerializer,
    TransactionSerializer,
)
from .services import (
    account_context,
    apply_money_pool_delta,
    assert_account_reconciles,
    check_pool_funds,
    ensure_allocations,
    sync_account_pools,
)

schema_view = get_schema_view(
    title="Expense API", description="API for the Expense app", version="1.0.0"
)


def _paginate_data(request, data):
    """Return a bounded, page-number-paginated response for a list payload."""
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(data, request)
    return paginator.get_paginated_response(page)


@api_view(["GET", "POST"])
def account_list_create(request):
    if request.method == "GET":
        accounts = Account.objects.select_related("money_location").prefetch_related(
            "allocations"
        ).all()
        for account in accounts:
            ensure_allocations(account)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(accounts, request)
        return paginator.get_paginated_response(AccountSerializer(page, many=True).data)
    serializer = CreateAccountSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        requested_location = serializer.validated_data.get("money_location")
        if requested_location is None:
            requested_location, _ = MoneyLocation.objects.get_or_create(
                name=serializer.validated_data["name"],
                defaults={"location_type": "bank", "active": True},
            )
        account = serializer.save(money_location=requested_location)
        ensure_allocations(account)
        owner, location = account_context(account)
        sync_account_pools(account, owner, location)
    return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def account_detail(request, id):
    account = get_object_or_404(Account, id=id)
    ensure_allocations(account)
    owner, location = account_context(account)
    sync_account_pools(account, owner, location)
    return Response(AccountSerializer(account).data)


# ---- Page views ----------------------------------------------------------


def _page(request, template):
    from django.middleware.csrf import get_token

    get_token(request)
    return render(request, template)


def dashboard(request):
    return _page(request, "dashboard.html")


def accounts_page(request):
    return _page(request, "accounts.html")


def categories_page(request):
    return _page(request, "categories.html")


def report_page(request):
    return _page(request, "reports.html")


@api_view(["GET", "POST"])
def categories_list_create(request):
    if request.method == "GET":
        qs = Category.objects.filter(active=True)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CategorySerializer(page, many=True).data
        )
    serializer = CategorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(
        CategorySerializer(serializer.save()).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "POST"])
def subcategories_list_create(request):
    if request.method == "GET":
        qs = SubCategory.objects.select_related("category").filter(active=True)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            SubCategorySerializer(page, many=True).data
        )
    serializer = SubCategorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(
        SubCategorySerializer(serializer.save()).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "POST"])
def items_list_create(request):
    if request.method == "GET":
        qs = Item.objects.select_related("category", "subcategory").filter(active=True)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ItemSerializer(page, many=True).data)
    serializer = ItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(
        ItemSerializer(serializer.save()).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "POST"])
def food_profiles(request):
    if request.method == "GET":
        qs = FoodProfile.objects.select_related("item").all()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            FoodProfileSerializer(page, many=True).data
        )
    serializer = FoodProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(
        FoodProfileSerializer(serializer.save()).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def owners_list(request):
    data = [
        {"id": str(o.id), "name": o.name, "active": o.active}
        for o in Owner.objects.filter(active=True)
    ]
    return _paginate_data(request, data)


@api_view(["GET"])
def money_locations_list(request):
    data = [
        {
            "id": str(x.id),
            "name": x.name,
            "location_type": x.location_type,
            "active": x.active,
        }
        for x in MoneyLocation.objects.filter(active=True)
    ]
    return _paginate_data(request, data)


@api_view(["GET"])
def money_pools_list(request):
    pools = MoneyPool.objects.select_related("account", "owner", "location").all()
    data = [
        {
            "id": str(p.id),
            "account": str(p.account_id) if p.account_id else None,
            "owner": str(p.owner_id) if p.owner_id else None,
            "owner_name": p.owner.name if p.owner else None,
            "location": str(p.location_id) if p.location_id else None,
            "location_name": p.location.name if p.location else None,
            "allocation_type": p.allocation_type,
            "current_amount": str(p.current_amount),
        }
        for p in pools
    ]
    return _paginate_data(request, data)


@api_view(["POST"])
def expense_create(request, id):
    serializer = ExpenseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data["amount"]
    allocation_type = serializer.validated_data["allocation"]
    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        ensure_allocations(account)
        allocation = Allocation.objects.select_for_update().get(
            account=account, type=allocation_type
        )
        owner, location = account_context(
            account,
            serializer.validated_data.get("owner"),
            serializer.validated_data.get("money_location"),
        )
        sync_account_pools(account, owner, location)
        if allocation.balance < amount:
            return Response(
                {"detail": f"Insufficient funds in {allocation_type} allocation."},
                status=400,
            )
        check_pool_funds(account, owner, location, allocation, amount)
        allocation.balance = F("balance") - amount
        account.total_balance = F("total_balance") - amount
        allocation.save(update_fields=["balance"])
        account.save(update_fields=["total_balance"])
        allocation.refresh_from_db()
        account.refresh_from_db()
        source_pool = apply_money_pool_delta(
            account, owner, location, allocation, -amount
        )
        Transaction.objects.create(
            account=account,
            owner=owner,
            money_location=location,
            allocation=allocation,
            source_pool=source_pool,
            category=serializer.validated_data.get("category"),
            subcategory=serializer.validated_data.get("subcategory"),
            item=serializer.validated_data.get("item"),
            variant=serializer.validated_data.get("variant", ""),
            meal=serializer.validated_data.get("meal"),
            type=TransactionType.EXPENSE,
            amount=amount,
            metadata={
                "merchant": serializer.validated_data.get("merchant", ""),
                "note": serializer.validated_data.get("note", ""),
                "custom_description": serializer.validated_data.get(
                    "custom_description", ""
                ),
            },
        )
        assert_account_reconciles(account)
    return Response(AccountSerializer(account).data)


@api_view(["GET"])
def transactions_list(request, id):
    qs = (
        Transaction.objects.filter(account_id=id)
        .select_related(
            "category", "subcategory", "item", "owner", "money_location", "allocation"
        )
        .order_by("-occurred_at", "-created_at")
    )
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(qs, request)
    data = TransactionSerializer(page, many=True).data
    return paginator.get_paginated_response(data)


@api_view(["GET"])
def summary_report(request, id):
    account = get_object_or_404(Account, id=id)
    return Response(summarize_account_transactions(account))
