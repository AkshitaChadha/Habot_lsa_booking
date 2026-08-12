import logging

from django.db import transaction

from .models import Booking, Payment


logger = logging.getLogger(__name__)


class PaymentProcessingError(Exception):
    """Raised when a payment webhook cannot be processed."""


@transaction.atomic
def process_payment_webhook(
    *,
    event,
    booking_id,
    transaction_id,
    amount,
):
    logger.info(
        "Processing payment webhook",
        extra={
            "event": event,
            "booking_id": booking_id,
            "transaction_id": transaction_id,
        },
    )

    # Lock the booking so concurrent webhook requests
    # cannot modify it at the same time.
    try:
        booking = (
            Booking.objects
            .select_for_update()
            .get(pk=booking_id)
        )
    except Booking.DoesNotExist:
        logger.error(
            "Payment webhook references unknown booking",
            extra={
                "booking_id": booking_id,
                "transaction_id": transaction_id,
            },
        )

        raise PaymentProcessingError(
            "Booking does not exist."
        )

    # Check whether this transaction has already been processed.
    payment = Payment.objects.filter(
        transaction_id=transaction_id
    ).first()

    if payment:
        # A transaction ID must never belong to another booking.
        if payment.booking_id != booking.id:
            logger.error(
                "Transaction belongs to another booking",
                extra={
                    "transaction_id": transaction_id,
                    "booking_id": booking_id,
                    "existing_booking_id": payment.booking_id,
                },
            )

            raise PaymentProcessingError(
                "Transaction belongs to another booking."
            )

        # Same transaction received again.
        # Treat it as an idempotent duplicate.
        logger.info(
            "Duplicate payment webhook ignored",
            extra={
                "transaction_id": transaction_id,
                "booking_id": booking_id,
            },
        )

        return booking

    # A new payment can only be processed for a booking
    # that is still waiting for payment.
    if booking.status != Booking.Status.PENDING_PAYMENT:
        logger.warning(
            "Payment received for booking not awaiting payment",
            extra={
                "booking_id": booking_id,
                "current_status": booking.status,
                "transaction_id": transaction_id,
            },
        )

        raise PaymentProcessingError(
            "Booking is not awaiting payment."
        )

    # Create the payment record initially as PENDING.
    payment = Payment.objects.create(
        booking=booking,
        transaction_id=transaction_id,
        amount=amount,
        status=Payment.Status.PENDING,
    )

    # Successful payment → confirm booking.
    if event == "payment.success":

        payment.status = Payment.Status.SUCCESS

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        booking.status = Booking.Status.CONFIRMED

        booking.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        logger.info(
            "Payment successful and booking confirmed",
            extra={
                "booking_id": booking_id,
                "transaction_id": transaction_id,
            },
        )

    # Failed payment → mark payment and booking as failed.
    elif event == "payment.failed":

        payment.status = Payment.Status.FAILED

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        booking.status = Booking.Status.PAYMENT_FAILED

        booking.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        logger.info(
            "Payment failed and booking marked as payment failed",
            extra={
                "booking_id": booking_id,
                "transaction_id": transaction_id,
            },
        )

    else:
        logger.error(
            "Unsupported payment event",
            extra={
                "event": event,
                "booking_id": booking_id,
                "transaction_id": transaction_id,
            },
        )

        raise PaymentProcessingError(
            "Unsupported payment event."
        )

    return booking