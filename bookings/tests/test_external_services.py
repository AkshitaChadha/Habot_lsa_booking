from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from bookings.external_services import (
    PaymentGatewayError,
    create_payment,
)


class PaymentGatewayTestCase(SimpleTestCase):

    @patch("bookings.external_services.requests.post")
    def test_payment_gateway_success(self, mock_post):

        mock_response = Mock()

        mock_response.status_code = 200

        mock_response.json.return_value = {
            "status": "success",
            "transaction_id": "txn_123",
        }

        mock_post.return_value = mock_response

        result = create_payment(
            booking_id=1,
            amount="1000.00",
            transaction_id="txn_123",
        )

        self.assertEqual(
            result["status"],
            "success",
        )

        mock_post.assert_called_once()

    @patch("bookings.external_services.requests.post")
    def test_payment_gateway_timeout(self, mock_post):

        import requests

        mock_post.side_effect = requests.exceptions.Timeout

        with self.assertRaises(PaymentGatewayError):
            create_payment(
                booking_id=1,
                amount="1000.00",
                transaction_id="txn_timeout",
            )