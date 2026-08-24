from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0021_appsetting'),
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
