from rest_framework import serializers

from .models import Booking, LSAProfile
from .services import create_booking
from .exceptions import BookingConflictError

class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "parent",
            "lsa",
            "start_time",
            "end_time",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
        ]

    def validate(self, attrs):
        start_time = attrs["start_time"]
        end_time = attrs["end_time"]

        if start_time >= end_time:
            raise serializers.ValidationError(
                "start_time must be earlier than end_time."
            )

        return attrs
    
    def create(self,validated_data):
      try:
        return create_booking(**validated_data)
      except BookingConflictError as exc:
        raise serializers.ValidationError(
          {"booking":str(exc)}
        )

class LSASearchSerializer(serializers.ModelSerializer):
  skills= serializers.StringRelatedField(many=True)
  
  class Meta:
    model= LSAProfile
    fields=[
      "id",
      "name",
      "email",
      "bio",
      "is_active",
      "skills",
    ]        
    
class LSASearchQuerySerializer(serializers.Serializer):
    skill = serializers.CharField(required=True)
    start_time = serializers.DateTimeField(required=True)
    end_time = serializers.DateTimeField(required=True)

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(
                "start_time must be earlier than end_time."
            )

        return attrs
      
class PaymentWebhookSerializer(serializers.Serializer):
    event = serializers.ChoiceField(
        choices=[
            "payment.success",
            "payment.failed",
        ]
    )
    transaction_id = serializers.CharField(max_length=100)
    booking_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2,)