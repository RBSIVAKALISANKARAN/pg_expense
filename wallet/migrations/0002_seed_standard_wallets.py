from django.db import migrations

from wallet import seeds


class Migration(migrations.Migration):

    dependencies = [
        ("wallet", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seeds.seed_standard_wallets,
            seeds.reverse_seed_standard_wallets,
        ),
    ]