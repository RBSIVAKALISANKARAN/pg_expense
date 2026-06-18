from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # These choices match the dropdown in your HTML exactly
    ROLE_CHOICES = (
        ('pg-student', 'PG-Student'),
        ('fresher', 'Fresher'),
        ('working-professional', 'Working Professional'),
    )
    
    # Adding your custom fields to the database
    phone = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, blank=True, null=True)

    def __str__(self):
        # This determines what shows up in the Django admin panel
        return self.email or self.username