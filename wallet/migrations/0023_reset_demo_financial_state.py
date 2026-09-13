from django.db import migrations


def noop_demo_reset(apps, schema_editor):
    """Intentionally retained as a historical no-op.

    This migration originally reset the financial ledger. Data cleanup must
    never happen implicitly during ``manage.py migrate`` because migrations
    may run against a real database. The old reset is preserved in Git history
    for auditability, but this migration now performs no data mutation.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0022_phase6_master_data_lifecycle"),
    ]

    operations = [
        migrations.RunPython(noop_demo_reset),
    ]
