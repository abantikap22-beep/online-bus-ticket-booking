from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Bus, Seat, Booking, CancellationRequest, MockPayment
import re

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone']

    def validate_phone(self, value):
        phone = re.sub(r'[\s\-\(\)]', '', str(value))
        pattern = r'^01[3-9]\d{8}$'
        if not re.match(pattern, phone):
            raise serializers.ValidationError("Invalid Bangladeshi phone number")
        return phone

    def create(self, validated_data):
        phone = validated_data.pop('phone')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        UserProfile.objects.get_or_create(user=user)
        user.userprofile.phone = phone
        user.userprofile.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id', 'seat_number', 'is_booked']


class BusSerializer(serializers.ModelSerializer):
    seats = SeatSerializer(many=True, read_only=True)
    available_seats_count = serializers.SerializerMethodField()

    class Meta:
        model = Bus
        fields = [
            'id', 'bus_name', 'number', 'origin', 'destination', 'features',
            'start_time', 'reach_time', 'no_of_seats', 'price', 'seats', 'available_seats_count'
        ]

    def get_available_seats_count(self, obj):
        return obj.seats.filter(is_booked=False).count()


class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    bus = BusSerializer(read_only=True)
    seat = SeatSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'bus', 'seat', 'booking_time', 'status']


class CancellationRequestSerializer(serializers.ModelSerializer):
    booking_details = BookingSerializer(source='booking', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CancellationRequest
        fields = [
            'id', 'booking', 'booking_details', 'user', 'user_name', 'reason',
            'status', 'requested_at', 'processed_at', 'admin_notes'
        ]
        read_only_fields = ['user', 'status', 'requested_at', 'processed_at', 'admin_notes']
