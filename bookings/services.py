from django.db import transaction
from django.db.models import Q
from .models import Booking, LSAProfile
from .exceptions import BookingConflictError

def create_booking(*, parent,lsa,start_time, end_time):
  with transaction.atomic():
    locked_lsa=(
      LSAProfile.objects.select_for_update().get(pk=lsa.pk)
    )
    if not locked_lsa.is_active:
      raise BookingConflictError(
        "LSA is currently inactive."
      )
    overlapping_booking=(
      Booking.objects.select_for_update().filter(
        lsa=lsa,
        start_time__lt=end_time,
        end_time__gt= start_time,
      )
      .exclude(
        status__in=[
          Booking.Status.CANCELLED,
          Booking.Status.PAYMENT_FAILED,
        ]
      ).first()
    )
    
    if overlapping_booking:
      raise BookingConflictError(
        "LSA is already booked during the requested time."
      )
      
    booking=Booking.objects.create(
      parent=parent,
      lsa=lsa,
      start_time=start_time,
      end_time=end_time,
      status=Booking.Status.PENDING_PAYMENT,
    )
    
    return booking