from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class Phase3PageContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='phase3-pages', password='phase3-pass')
        self.client = APIClient()

    def test_transaction_page_requires_authentication(self):
        response = self.client.get('/api/transactions/page/')
        self.assertEqual(response.status_code, 302)
        self.client.login(username='phase3-pages', password='phase3-pass')
        response = self.client.get('/api/transactions/page/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transaction ledger')

    def test_expense_and_reports_pages_require_authentication(self):
        for path in ('/api/expense/page/', '/api/reports/page/'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
        self.client.login(username='phase3-pages', password='phase3-pass')
        for path, marker in (('/api/expense/page/', 'Record an expense'), ('/api/reports/page/', 'Financial analytics')):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, marker)

    def test_dashboard_page_is_reachable_after_login(self):
        self.client.login(username='phase3-pages', password='phase3-pass')
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_settings_page_renders_persisted_values(self):
        self.client.login(username='phase3-pages', password='phase3-pass')
        self.client.post('/api/settings/', {'app_name': 'Phase 3 UI'}, format='json')
        response = self.client.get('/api/settings/page/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Phase 3 UI')

    def test_reports_endpoint_is_authenticated(self):
        response = self.client.get('/api/reports/data/')
        self.assertIn(response.status_code, (401, 403, 302))
        self.client.login(username='phase3-pages', password='phase3-pass')
        response = self.client.get('/api/reports/data/')
        self.assertEqual(response.status_code, 200)
