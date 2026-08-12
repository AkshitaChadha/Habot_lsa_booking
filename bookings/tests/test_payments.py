from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking, LSAProfile, Parent, Payment


class PaymentWebhookAPITestCase(APITestCase):

    def setUp(self):
        self.parent = Parent.objects.create(
            name="Payment Parent",
            email="payment_parent@test.com",
            phone="7777777777",
        )

        self.lsa = LSAProfile.objects.create(
            name="Payment LSA",
            email="payment_lsa@test.com",
            is_active=True,
        )

        self.booking = Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time="2026-09-01T10:00:00Z",
            end_time="2026-09-01T11:00:00Z",
            status=Booking.Status.PENDING_PAYMENT,
        )

        self.url = "/api/payments/webhook/"

    def test_successful_payment_confirms_booking(self):
        response = self.client.post(
            self.url,
            {
                "event": "payment.success",
                "transaction_id": "txn_success_001",
                "booking_id": self.booking.id,
                "amount": "1000.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.CONFIRMED,
        )

        payment = Payment.objects.get(
            booking=self.booking
        )

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESS,
        )

    def test_failed_payment_marks_booking_failed(self):
        response = self.client.post(
            self.url,
            {
                "event": "payment.failed",
                "transaction_id": "txn_failed_001",
                "booking_id": self.booking.id,
                "amount": "1000.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.PAYMENT_FAILED,
        )

        payment = Payment.objects.get(
            booking=self.booking
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

    def test_duplicate_webhook_is_idempotent(self):
        payload = {
            "event": "payment.success",
            "transaction_id": "txn_duplicate_001",
            "booking_id": self.booking.id,
            "amount": "1000.00",
        }

        first_response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        second_response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Payment.objects.filter(
                transaction_id="txn_duplicate_001"
            ).count(),
            1,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.CONFIRMED,
        )