from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import BookingCreateSerializer
from .models import LSAProfile, Booking
from .serializers import BookingCreateSerializer, LSASearchSerializer, LSASearchQuerySerializer, PaymentWebhookSerializer
from django.db.models import Q
from .payment_service import PaymentProcessingError, process_payment_webhook
# Create your views here.
class BookingCreateView(APIView):
  def post(self, request):
    serializer= BookingCreateSerializer(data=request.data)
    
    if serializer.is_valid():
      booking= serializer.save()
      
      return Response(
        BookingCreateSerializer(booking).data,
        status=status.HTTP_201_CREATED,
      )
    
    return Response(
      serializer.errors,
      status=status.HTTP_400_BAD_REQUEST,
    )
    
class LSASearchView(APIView):

    def get(self, request):
        query_serializer = LSASearchQuerySerializer(
            data=request.query_params
        )

        query_serializer.is_valid(raise_exception=True)

        skill = query_serializer.validated_data["skill"]
        start_time = query_serializer.validated_data["start_time"]
        end_time = query_serializer.validated_data["end_time"]

        queryset = (
            LSAProfile.objects
            .filter(
                is_active=True,
                skills__name__iexact=skill,
            )
            .exclude(
                Q(bookings__start_time__lt=end_time)
                & Q(bookings__end_time__gt=start_time)
                & ~Q(
                    bookings__status__in=[
                        Booking.Status.CANCELLED,
                        Booking.Status.PAYMENT_FAILED,
                    ]
                )
            )
            .prefetch_related("skills")
            .distinct()
        )

        serializer = LSASearchSerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)
      
class PaymentWebhookView(APIView):

    def post(self, request):
        serializer = PaymentWebhookSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            booking = process_payment_webhook(
                **serializer.validated_data
            )
        except PaymentProcessingError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Payment processed successfully.",
                "booking_id": booking.id,
                "booking_status": booking.status,
            },
            status=status.HTTP_200_OK,
        )