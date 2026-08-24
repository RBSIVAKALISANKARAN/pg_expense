import os

# Playwright's synchronous API runs inside an asyncio-managed context on
# Python 3.14. The Phase 7 cleanup code uses Django's synchronous ORM after
# the browser actions, so explicitly allow that controlled test-only access.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
