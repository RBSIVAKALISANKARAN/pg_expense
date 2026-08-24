from django.urls import path

from .phase6_views import (
    master_accounts, master_account_detail, master_account_status,
    master_categories, master_category_detail, master_category_status,
    master_subcategories, master_subcategory_detail, master_subcategory_status,
    master_items, master_item_detail, master_item_status,
    master_owners, master_owner_detail, master_owner_status,
    master_locations, master_location_detail, master_location_status,
    master_config, master_data_page,
)

urlpatterns = [
    path('master-data/page/', master_data_page, name='master-data-page'),
    path('master-data/accounts/', master_accounts, name='master-accounts'),
    path('master-data/accounts/<uuid:pk>/', master_account_detail, name='master-account-detail'),
    path('master-data/accounts/<uuid:pk>/status/', master_account_status, name='master-account-status'),
    path('master-data/categories/', master_categories, name='master-categories'),
    path('master-data/categories/<uuid:pk>/', master_category_detail, name='master-category-detail'),
    path('master-data/categories/<uuid:pk>/status/', master_category_status, name='master-category-status'),
    path('master-data/subcategories/', master_subcategories, name='master-subcategories'),
    path('master-data/subcategories/<uuid:pk>/', master_subcategory_detail, name='master-subcategory-detail'),
    path('master-data/subcategories/<uuid:pk>/status/', master_subcategory_status, name='master-subcategory-status'),
    path('master-data/items/', master_items, name='master-items'),
    path('master-data/items/<uuid:pk>/', master_item_detail, name='master-item-detail'),
    path('master-data/items/<uuid:pk>/status/', master_item_status, name='master-item-status'),
    path('master-data/owners/', master_owners, name='master-owners'),
    path('master-data/owners/<uuid:pk>/', master_owner_detail, name='master-owner-detail'),
    path('master-data/owners/<uuid:pk>/status/', master_owner_status, name='master-owner-status'),
    path('master-data/locations/', master_locations, name='master-locations'),
    path('master-data/locations/<uuid:pk>/', master_location_detail, name='master-location-detail'),
    path('master-data/locations/<uuid:pk>/status/', master_location_status, name='master-location-status'),
    path('master-data/config/', master_config, name='master-config'),
]
