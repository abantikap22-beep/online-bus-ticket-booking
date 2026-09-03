from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics, status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from .models import Bus, Seat, Booking, MockPayment, CancellationRequest
from .serializers import UserRegisterSerializer, BusSerializer, BookingSerializer, CancellationRequestSerializer
from .mock_bkash_service import mock_bkash_service

# ---------------- USER AUTH ----------------
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'message': 'Registration successful'
            }, status=201)
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username
            }, status=200)
        return Response({'error': 'Invalid credentials'}, status=401)


# ---------------- BUS ----------------
class BusListCreateView(generics.ListCreateAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer


class BusDetailView(generics.RetrieveDestroyAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer


# ---------------- BOOKING ----------------
class BookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        seat_id = request.data.get('seat')
        if not seat_id:
            return Response({'error': 'Seat ID required'}, status=400)

        try:
            seat = Seat.objects.get(id=seat_id)
        except Seat.DoesNotExist:
            return Response({'error': 'Seat not found'}, status=404)

        if not seat.is_available():
            return Response({'error': 'Seat already booked'}, status=400)

        booking = Booking.objects.create(
            user=request.user,
            bus=seat.bus,
            seat=seat,
            status='pending'
        )
        serializer = BookingSerializer(booking)
        return Response(serializer.data, status=201)


class UserBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.id != user_id:
            return Response({'error': 'Unauthorized'}, status=401)

        bookings = Booking.objects.filter(user=request.user)
        data = []
        for b in bookings:
            bd = BookingSerializer(b).data
            payments = MockPayment.objects.filter(booking=b).order_by('-created_at')
            bd['payment_status'] = payments[0].status if payments.exists() else 'PENDING'
            data.append(bd)
        return Response(data, status=200)


# ---------------- MOCK PAYMENT ----------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_mock_payment(request):
    amount = request.data.get("amount")
    booking_id = request.data.get("booking_id")
    if not amount or not booking_id:
        return Response({"status": "error", "message": "Amount and booking_id required"}, status=400)

    response = mock_bkash_service.create_payment(amount=amount, booking_id=booking_id)
    return Response(response, status=200 if response['status'] == 'success' else 400)


# ---------------- CANCELLATION REQUESTS ----------------
class RequestCancellationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"status": "error", "message": "Booking not found"}, status=404)

        if booking.status != 'confirmed':
            return Response({"status": "error", "message": "Booking cannot be cancelled"}, status=400)

        cancellation = CancellationRequest.objects.create(
            booking=booking,
            user=request.user,
            reason=request.data.get('reason', '')
        )

        booking.status = 'cancellation_requested'
        booking.save()

        return Response({
            "status": "success",
            "message": "Cancellation request submitted",
            "request_id": cancellation.id
        }, status=200)


class AdminCancellationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=403)

        status_filter = request.GET.get('status', 'pending')
        requests = CancellationRequest.objects.filter(status=status_filter)
        serializer = CancellationRequestSerializer(requests, many=True)
        return Response(serializer.data, status=200)


class AdminProcessCancellationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=403)

        try:
            cancellation = CancellationRequest.objects.get(id=request_id)
        except CancellationRequest.DoesNotExist:
            return Response({"status": "error", "message": "Cancellation request not found"}, status=404)

        action = request.data.get('action')
        admin_notes = request.data.get('admin_notes', '')

        if action == 'approve':
            if cancellation.approve(admin_notes):
                return Response({"status": "success", "message": "Cancellation approved and seat freed"})
            return Response({"status": "error", "message": "Failed to process cancellation"}, status=500)

        elif action == 'reject':
            if cancellation.reject(admin_notes):
                return Response({"status": "success", "message": "Cancellation rejected"})
            return Response({"status": "error", "message": "Failed to process rejection"}, status=500)

        return Response({"status": "error", "message": "Invalid action"}, status=400)
