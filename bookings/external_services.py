import logging

import requests


logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """Raised when the external payment gateway fails."""


def create_payment(
    *,
    booking_id,
    amount,
    transaction_id,
):
    payload = {
        "booking_id": booking_id,
        "amount": str(amount),
        "transaction_id": transaction_id,
    }

    try:
        response = requests.post(
            "https://mock-payment-gateway.example.com/payments",
            json=payload,
            timeout=5,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout as exc:
        logger.error(
            "Payment gateway request timed out",
            extra={
                "booking_id": booking_id,
                "transaction_id": transaction_id,
            },
        )

        raise PaymentGatewayError(
            "Payment gateway request timed out."
        ) from exc

    except requests.exceptions.RequestException as exc:
        logger.error(
            "Payment gateway request failed",
            extra={
                "booking_id": booking_id,
                "transaction_id": transaction_id,
                "error": str(exc),
            },
        )

        raise PaymentGatewayError(
            "Payment gateway request failed."
        ) from exc

    logger.info(
        "Payment gateway request successful",
        extra={
            "booking_id": booking_id,
            "transaction_id": transaction_id,
        },
    )

    return response.json()