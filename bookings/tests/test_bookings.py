from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking, LSAProfile, Parent, Skill
from unittest.mock import patch

class BookingAPITestCase(APITestCase):

    def setUp(self):
        self.parent = Parent.objects.create(
            name="Test Parent",
            email="parent@test.com",
            phone="9999999999",
        )

        self.skill = Skill.objects.create(
            name="Dyslexia Support"
        )

        self.lsa = LSAProfile.objects.create(
            name="Test LSA",
            email="lsa@test.com",
            is_active=True,
        )

        self.lsa.skills.add(self.skill)

        self.start_time = timezone.now() + timedelta(days=1)
        self.end_time = self.start_time + timedelta(hours=1)

        self.url = "/api/v1/bookings/"

    def booking_payload(self, start_time=None, end_time=None):
        return {
            "parent": self.parent.id,
            "lsa": self.lsa.id,
            "start_time": start_time or self.start_time,
            "end_time": end_time or self.end_time,
        }

    @patch("bookings.services.create_payment")
    def test_create_booking_success(self, mock_create_payment):
        response = self.client.post(
            self.url,
            self.booking_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["status"],
            Booking.Status.PENDING_PAYMENT,
        )

        mock_create_payment.assert_called_once()

        call_kwargs = mock_create_payment.call_args.kwargs

        self.assertEqual(
            call_kwargs["booking_id"],
            response.data["id"],
        )

        self.assertEqual(
            call_kwargs["amount"],
            "1000.00",
        )

    def test_create_booking_rejects_invalid_time(self):
        response = self.client.post(
            self.url,
            self.booking_payload(
                start_time=self.end_time,
                end_time=self.start_time,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_booking_rejects_overlap(self):
        Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=self.start_time,
            end_time=self.end_time,
            status=Booking.Status.PENDING_PAYMENT,
        )

        overlapping_start = self.start_time + timedelta(minutes=30)
        overlapping_end = self.end_time + timedelta(minutes=30)

        response = self.client.post(
            self.url,
            self.booking_payload(
                start_time=overlapping_start,
                end_time=overlapping_end,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch("bookings.services.create_payment")
    def test_adjacent_booking_is_allowed(self, mock_create_payment):
        Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=self.start_time,
            end_time=self.end_time,
            status=Booking.Status.PENDING_PAYMENT,
        )

        adjacent_start = self.end_time
        adjacent_end = adjacent_start + timedelta(hours=1)

        response = self.client.post(
            self.url,
            self.booking_payload(
                start_time=adjacent_start,
                end_time=adjacent_end,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        mock_create_payment.assert_called_once()