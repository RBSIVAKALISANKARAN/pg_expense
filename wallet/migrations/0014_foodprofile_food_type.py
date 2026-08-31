from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0013_moneypool_location_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='foodprofile',
            name='food_type',
            field=models.CharField(
                choices=[('food', 'Food'), ('drink', 'Drink')],
                default='food',
                max_length=10,
            ),
        ),
    ]
