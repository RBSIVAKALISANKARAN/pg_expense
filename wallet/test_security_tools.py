from django.test import SimpleTestCase
from django.conf import settings


class SecurityConfigurationTests(SimpleTestCase):
    def test_csp_and_throttle_configuration(self):
        self.assertIn("django.middleware.csp.ContentSecurityPolicyMiddleware", settings.MIDDLEWARE)
        self.assertEqual(settings.SECURE_CSP["default-src"], ["'self'"])
        self.assertIn("rest_framework.throttling.UserRateThrottle", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"])
        self.assertEqual(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["sql"], "10/min")

    def test_dependencies_are_exactly_pinned(self):
        from pathlib import Path

        requirements = (Path(settings.BASE_DIR) / "requirements.txt").read_text(encoding="utf-8").splitlines()
        for line in requirements:
            if line.strip() and not line.lstrip().startswith("#"):
                self.assertRegex(line, r"^[A-Za-z0-9_.-]+==[^=]+$")
