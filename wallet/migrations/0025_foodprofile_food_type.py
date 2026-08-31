from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0024_cleanup_phase7_demo_data'),
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
