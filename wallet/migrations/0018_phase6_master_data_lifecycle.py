from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0017_fix_duplicate_standard_accounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='category',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='subcategory',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='item',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
