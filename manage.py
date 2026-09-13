#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pg_expense.settings')

    # Make the test-only authentication mode explicit. This is deliberately
    # scoped to Django's test command rather than having settings.py inspect
    # sys.argv. Other management commands always use the real auth boundary.
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        os.environ.setdefault('DJANGO_TESTING', '1')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
