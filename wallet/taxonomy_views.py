from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    Category,
    FoodGroup,
    FoodProfile,
    FoodType,
    HealthClassification,
    Item,
    SubCategory,
    SugaryStatus,
)


def _profile_data(profile):
    item = profile.item
    return {
        'id': str(profile.id),
        'item': str(item.id),
        'item_name': item.name,
        'category': str(item.category_id),
        'category_name': item.category.name,
        'subcategory': str(item.subcategory_id) if item.subcategory_id else None,
        'subcategory_name': item.subcategory.name if item.subcategory else None,
        'food_type': profile.food_type,
        'food_group': profile.food_group,
        'health_classification': profile.health_classification,
        'sugary': profile.sugary,
    }


def _choices(enum):
    return [{'value': value, 'label': label} for value, label in enum.choices]


@api_view(['GET', 'POST', 'PATCH'])
def food_taxonomy(request):
    if request.method == 'GET':
        profiles = FoodProfile.objects.select_related('item', 'item__category', 'item__subcategory').order_by('item__name')
        return Response({
            'profiles': [_profile_data(profile) for profile in profiles],
            'choices': {
                'food_type': _choices(FoodType),
                'food_group': _choices(FoodGroup),
                'health_classification': _choices(HealthClassification),
                'sugary': _choices(SugaryStatus),
            },
        })

    item_id = request.data.get('item')
    if not item_id:
        return Response({'detail': 'Item is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        item = Item.objects.select_related('category', 'subcategory').get(id=item_id, active=True)
    except Item.DoesNotExist:
        return Response({'detail': 'Selected item was not found.'}, status=status.HTTP_404_NOT_FOUND)

    if item.category.name.strip().lower() != 'food':
        return Response({'detail': 'Food profiles can only be assigned to items in the Food category.'}, status=status.HTTP_400_BAD_REQUEST)

    allowed = {
        'food_type': {value for value, _ in FoodType.choices},
        'food_group': {value for value, _ in FoodGroup.choices},
        'health_classification': {value for value, _ in HealthClassification.choices},
        'sugary': {value for value, _ in SugaryStatus.choices},
    }
    values = {}
    for field, valid_values in allowed.items():
        if field in request.data:
            value = str(request.data.get(field) or '').strip()
            if value not in valid_values:
                return Response({field: 'Invalid taxonomy value.'}, status=status.HTTP_400_BAD_REQUEST)
            values[field] = value

    profile, created = FoodProfile.objects.update_or_create(
        item=item,
        defaults=values,
    )
    return Response(_profile_data(profile), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
