from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


User = get_user_model()


@override_settings(TESTING=False)
class SQLStaffAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sql-nonstaff", password="StrongTestPassword123!")
        self.staff = User.objects.create_user(
            username="sql-staff",
            password="StrongTestPassword123!",
            is_staff=True,
        )

    def test_non_staff_cannot_open_sql_page_or_execute(self):
        self.assertTrue(self.client.login(username="sql-nonstaff", password="StrongTestPassword123!"))
        self.assertEqual(self.client.get("/api/sql/").status_code, 403)
        self.assertEqual(self.client.post("/api/sql/execute/", {"sql": "SELECT 1"}).status_code, 403)

    def test_staff_can_open_sql_page(self):
        self.assertTrue(self.client.login(username="sql-staff", password="StrongTestPassword123!"))
        self.assertEqual(self.client.get("/api/sql/").status_code, 200)
