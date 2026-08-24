from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0020_restore_account_scoped_money_pool_identity'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.TextField(blank=True, default='')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
