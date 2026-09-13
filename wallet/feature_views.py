from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .feature_models import MealOption
from .pagination import StandardResultsSetPagination


@api_view(['GET', 'POST'])
def meals(request):
    if request.method == 'GET':
        defaults = ['Breakfast', 'Lunch', 'Dinner', 'Snack']
        for name in defaults:
            MealOption.objects.get_or_create(name=name)
        meals_qs = MealOption.objects.filter(active=True).order_by('name')
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(meals_qs, request)
        return paginator.get_paginated_response([
            {'id': meal.id, 'name': meal.name, 'active': meal.active} for meal in page
        ])
    name = str(request.data.get('name', '')).strip()
    if not name:
        return Response({'detail': 'Meal name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    meal, created = MealOption.objects.get_or_create(name=name, defaults={'active': True})
    if not created and not meal.active:
        meal.active = True
        meal.save(update_fields=['active'])
    return Response({'id': meal.id, 'name': meal.name, 'active': meal.active}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


def expense_page(request):
    return render(request, 'expense.html')
