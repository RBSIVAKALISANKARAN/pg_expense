from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0010_transaction_variant_alter_foodprofile_food_group'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='moneypool',
            name='unique_account_owner_allocation_pool',
        ),
        migrations.AddConstraint(
            model_name='moneypool',
            constraint=models.UniqueConstraint(
                fields=('account', 'owner', 'location', 'allocation_type'),
                name='unique_account_owner_location_allocation_pool',
            ),
        ),
    ]
