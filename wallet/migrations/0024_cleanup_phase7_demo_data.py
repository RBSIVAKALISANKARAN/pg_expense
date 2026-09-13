from django.db import migrations


def noop_phase7_cleanup(apps, schema_editor):
    """Intentionally retained as a historical no-op.

    Phase 7 browser-test cleanup used to delete transactions and reset wallet
    balances from inside the migration chain. That is unsafe because Django
    cannot distinguish a demo database from a real database while migrating.
    Explicit demo cleanup, if ever needed again, must be a separately invoked
    management command or other deliberate operator action.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0023_reset_demo_financial_state"),
    ]

    operations = [
        migrations.RunPython(noop_phase7_cleanup),
    ]
