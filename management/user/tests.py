from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()


class UserManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.personnel = User.objects.create_user("ayse", password="pw-12345-x")
        cls.admin = User.objects.create_superuser("root", "root@example.com", "pw-12345-x")

    def test_profile_is_created_with_role_from_user_type(self):
        self.assertEqual(self.personnel.profile.role, Profile.ROLE_PERSONNEL)
        self.assertEqual(self.admin.profile.role, Profile.ROLE_ADMIN)

    def test_user_management_is_admin_only(self):
        self.client.force_login(self.personnel)
        self.assertEqual(self.client.get(reverse("user:user_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("user:user_create")).status_code, 403)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("user:user_list")).status_code, 200)

    def test_admin_creates_user_with_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user:user_create"),
            {
                "username": "zeynep",
                "first_name": "Zeynep",
                "last_name": "Kara",
                "email": "zeynep@example.com",
                "role": Profile.ROLE_ADMIN,
                "password1": "Sup3r-guvenli-parola",
                "password2": "Sup3r-guvenli-parola",
            },
        )
        self.assertRedirects(response, reverse("user:user_list"))
        created = User.objects.get(username="zeynep")
        self.assertEqual(created.profile.role, Profile.ROLE_ADMIN)
        self.assertTrue(created.check_password("Sup3r-guvenli-parola"))

    def test_admin_cannot_demote_self(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("user:user_edit", args=[self.admin.pk]),
            {"first_name": "", "last_name": "", "email": "root@example.com", "role": Profile.ROLE_PERSONNEL},
        )
        self.admin.profile.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.profile.role, Profile.ROLE_ADMIN)
        self.assertTrue(self.admin.is_active)
