from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


User = get_user_model()


@override_settings(TESTING=False)
class AuthenticationBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="security-user", password="StrongTestPassword123!")

    def test_unauthenticated_api_request_is_rejected(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication credentials were not provided.")

    def test_unauthenticated_browser_request_redirects_to_login(self):
        response = self.client.get("/api/dashboard/", HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication credentials were not provided.")

    def test_login_page_is_public(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_authenticated_session_can_access_application(self):
        self.assertTrue(self.client.login(username="security-user", password="StrongTestPassword123!"))
        response = self.client.get(reverse("dashboard"))
        self.assertNotEqual(response.status_code, 401)

    def test_non_staff_cannot_access_sql_playground(self):
        self.assertTrue(self.client.login(username="security-user", password="StrongTestPassword123!"))
        page = self.client.get("/api/sql/")
        execute = self.client.post("/api/sql/execute/", {"sql": "SELECT 1"})
        history = self.client.get("/api/sql/history/")
        self.assertEqual(page.status_code, 403)
        self.assertEqual(execute.status_code, 403)
        self.assertEqual(history.status_code, 403)

    def test_csp_header_is_present_and_enforced(self):
        self.assertTrue(self.client.login(username="security-user", password="StrongTestPassword123!"))
        response = self.client.get(reverse("dashboard"))
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'self'", csp)

    def test_logout_ends_authenticated_session(self):
        self.assertTrue(self.client.login(username="security-user", password="StrongTestPassword123!"))
        self.client.post(reverse("logout"))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 401)
