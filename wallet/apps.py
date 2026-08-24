from django.apps import AppConfig


class WalletConfig(AppConfig):
    name = 'wallet'

    def ready(self):
        from . import feature_models  # noqa: F401
        from . import signals  # noqa: F401
        # Keep the existing financial endpoints intact while routing their
        # money-pool lookup through the account-scoped integrity implementation.
        from . import financial_integrity, views
        views._ensure_money_pool = financial_integrity.ensure_account_money_pool
