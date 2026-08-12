from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking, LSAProfile, Parent, Skill


class LSASearchAPITestCase(APITestCase):

    def setUp(self):
        self.parent = Parent.objects.create(
            name="Test Parent",
            email="search_parent@test.com",
            phone="8888888888",
        )

        self.dyslexia_skill = Skill.objects.create(
            name="Dyslexia Support"
        )

        self.adhd_skill = Skill.objects.create(
            name="ADHD Support"
        )

        self.available_lsa = LSAProfile.objects.create(
            name="Available LSA",
            email="available@test.com",
            is_active=True,
        )

        self.available_lsa.skills.add(
            self.dyslexia_skill
        )

        self.other_skill_lsa = LSAProfile.objects.create(
            name="ADHD LSA",
            email="adhd@test.com",
            is_active=True,
        )

        self.other_skill_lsa.skills.add(
            self.adhd_skill
        )

        self.inactive_lsa = LSAProfile.objects.create(
            name="Inactive LSA",
            email="inactive@test.com",
            is_active=False,
        )

        self.inactive_lsa.skills.add(
            self.dyslexia_skill
        )

        self.start_time = timezone.now() + timedelta(days=2)
        self.end_time = self.start_time + timedelta(hours=1)

        self.url = "/api/v1/lsas/search/"

    def search_params(self):
        return {
            "skill": "Dyslexia Support",
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }

    def test_search_filters_by_skill(self):
        response = self.client.get(
            self.url,
            self.search_params(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        names = [
            lsa["name"]
            for lsa in response.data
        ]

        self.assertIn(
            "Available LSA",
            names,
        )

        self.assertNotIn(
            "ADHD LSA",
            names,
        )

    def test_search_excludes_inactive_lsa(self):
        response = self.client.get(
            self.url,
            self.search_params(),
        )

        names = [
            lsa["name"]
            for lsa in response.data
        ]

        self.assertNotIn(
            "Inactive LSA",
            names,
        )

    def test_search_excludes_unavailable_lsa(self):
        Booking.objects.create(
            parent=self.parent,
            lsa=self.available_lsa,
            start_time=self.start_time,
            end_time=self.end_time,
            status=Booking.Status.PENDING_PAYMENT,
        )

        response = self.client.get(
            self.url,
            self.search_params(),
        )

        names = [
            lsa["name"]
            for lsa in response.data
        ]

        self.assertNotIn(
            "Available LSA",
            names,
        )