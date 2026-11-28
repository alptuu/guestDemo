from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from user.models import Profile

from .models import GraphRun

User = get_user_model()


class PanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.personnel = User.objects.create_user("ayse", password="pw-12345-x")
        cls.other = User.objects.create_user("mehmet", password="pw-12345-x")
        cls.admin = User.objects.create_user("root", password="pw-12345-x")
        cls.admin.profile.role = Profile.ROLE_ADMIN
        cls.admin.profile.save()

    def test_login_required(self):
        response = self.client.get(reverse("graph:dashboard"))
        self.assertRedirects(response, f"{reverse('user:login')}?next={reverse('graph:dashboard')}")

    def test_pages_render(self):
        self.client.force_login(self.personnel)
        for name in ("graph:dashboard", "graph:runner", "graph:run_history", "user:profile"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_execute_runs_all_services_and_records_them(self):
        self.client.force_login(self.personnel)
        response = self.client.post(
            reverse("graph:execute"), {"service": ["cafe", "housekeeping", "technical"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)
        runs = GraphRun.objects.filter(user=self.personnel)
        self.assertEqual(runs.count(), 3)
        self.assertTrue(all(r.status == GraphRun.STATUS_SUCCESS for r in runs))
        cafe = runs.get(service_type="cafe")
        # Mock veride H01 kafe katları eşiği aşıyor.
        self.assertEqual(cafe.decision, "notify")
        self.assertGreater(cafe.notified_count, 0)
        self.assertEqual([s["node"] for s in cafe.payload["steps"]], ["fetch", "calc", "route", "notify"])

    def test_execute_rejects_unknown_service(self):
        self.client.force_login(self.personnel)
        response = self.client.post(reverse("graph:execute"), {"service": ["bogus"]})
        self.assertEqual(response.status_code, 400)

    def test_history_is_scoped_by_role(self):
        mine = GraphRun.objects.create(user=self.personnel, service_type="cafe")
        theirs = GraphRun.objects.create(user=self.other, service_type="cafe")

        self.client.force_login(self.personnel)
        self.assertEqual(self.client.get(reverse("graph:run_detail", args=[mine.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("graph:run_detail", args=[theirs.pk])).status_code, 404)
        history = self.client.get(reverse("graph:run_history"))
        self.assertEqual(history.context["page"].paginator.count, 1)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("graph:run_detail", args=[theirs.pk])).status_code, 200)
        history = self.client.get(reverse("graph:run_history"))
        self.assertEqual(history.context["page"].paginator.count, 2)
