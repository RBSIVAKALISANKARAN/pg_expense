from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .feature_models import MealOption


@api_view(['GET', 'POST'])
def meals(request):
    if request.method == 'GET':
        defaults = ['Breakfast', 'Lunch', 'Dinner', 'Snack']
        for name in defaults:
            MealOption.objects.get_or_create(name=name)
        return Response([{'id': meal.id, 'name': meal.name, 'active': meal.active} for meal in MealOption.objects.filter(active=True)])
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
