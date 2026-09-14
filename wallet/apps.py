from django.apps import AppConfig


class WalletConfig(AppConfig):
    name = "wallet"

    def ready(self):
        # Keep every module's imported pool helpers on the same concurrency-safe
        # implementation. Several wallet modules import these helpers directly
        # from views at module load time, so patching only views is insufficient.
        from . import feature_models  # noqa: F401
        from . import signals  # noqa: F401
        from . import (
            account_money_views,
            complete_flow_views,
            feature_views,
            financial_integrity,
            views,
        )

        views._ensure_money_pool = financial_integrity.ensure_account_money_pool
        views._sync_account_pools = (
            financial_integrity.sync_account_pools_with_legacy_repair
        )

        for module in (account_money_views, complete_flow_views, feature_views):
            if hasattr(module, "_ensure_money_pool"):
                module._ensure_money_pool = (
                    financial_integrity.ensure_account_money_pool
                )
            if hasattr(module, "_sync_account_pools"):
                module._sync_account_pools = (
                    financial_integrity.sync_account_pools_with_legacy_repair
                )
