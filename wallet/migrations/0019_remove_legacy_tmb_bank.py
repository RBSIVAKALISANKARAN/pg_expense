from django.db import migrations


def remove_legacy_tmb_bank(apps, schema_editor):
    MoneyLocation = apps.get_model('wallet', 'MoneyLocation')
    MoneyLocation.objects.filter(name='TMB Bank').delete()


def restore_legacy_tmb_bank(apps, schema_editor):
    MoneyLocation = apps.get_model('wallet', 'MoneyLocation')
    MoneyLocation.objects.get_or_create(
        name='TMB Bank',
        defaults={
            'location_type': 'bank',
            'active': True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0018_alter_account_name'),
    ]

    operations = [
        migrations.RunPython(
            remove_legacy_tmb_bank,
            restore_legacy_tmb_bank,
        ),
    ]