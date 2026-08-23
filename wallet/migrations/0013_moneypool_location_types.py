from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0012_mealoption'),
    ]

    operations = [
        migrations.AlterField(
            model_name='moneylocation',
            name='location_type',
            field=models.CharField(
                choices=[
                    ('bank', 'Bank'),
                    ('cash', 'Cash'),
                    ('travel_card', 'Travel Card'),
                    ('change_cash', 'Change Cash'),
                ],
                default='bank',
                max_length=20,
            ),
        ),
    ]
