from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


User = get_user_model()


@override_settings(TESTING=False, SQL_PLAYGROUND_TIMEOUT_MS=5000, SQL_PLAYGROUND_MAX_ROWS=500)
class SQLPlaygroundSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sql-security-user',
            password='StrongTestPassword123!',
            is_staff=True,
        )
        self.client.login(username='sql-security-user', password='StrongTestPassword123!')

    def test_non_staff_cannot_execute_sql(self):
        self.user.is_staff = False
        self.user.save(update_fields=['is_staff'])
        response = self.client.post('/api/sql/execute/', data={'sql': 'SELECT 1 AS value'}, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_write_keywords_are_rejected(self):
        response = self.client.post('/api/sql/execute/', data={'sql': 'UPDATE wallet_account SET name = \'x\''}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('read-only', response.json()['message'].lower())

    def test_read_query_executes(self):
        response = self.client.post('/api/sql/execute/', data={'sql': 'SELECT 1 AS value'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['rows'], [{'value': 1}])

    def test_result_set_is_capped(self):
        response = self.client.post('/api/sql/execute/', data={'sql': 'SELECT generate_series(1, 501) AS value'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['row_count'], 500)
        self.assertTrue(payload['truncated'])
        self.assertEqual(payload['max_rows'], 500)
