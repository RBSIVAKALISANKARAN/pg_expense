from django.urls import path
from . import views

urlpatterns = [
    # This creates the endpoint: /register/
    path('register/', views.register_user, name='register'),
]