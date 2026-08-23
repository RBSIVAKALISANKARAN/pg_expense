from django.db import models


class MealOption(models.Model):
    name = models.CharField(max_length=80, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
