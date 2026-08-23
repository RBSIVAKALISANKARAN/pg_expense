from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('wallet', '0011_fix_moneypool_location_uniqueness')]

    operations = [
        migrations.CreateModel(
            name='MealOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name']},
        ),
    ]
