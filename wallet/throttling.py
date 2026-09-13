from rest_framework.throttling import SimpleRateThrottle


class SQLUserRateThrottle(SimpleRateThrottle):
    """Strict per-user throttle for the privileged SQL playground."""

    scope = "sql"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": request.user.pk,
        }
