import uuid
import time
from decimal import Decimal
from .models import MockPayment, Booking

class MockBKashService:
    def create_payment(self, amount, booking_id=None):
        if not booking_id:
            return {'status': 'error', 'message': 'Booking ID is required'}
        try:
            booking = Booking.objects.get(id=booking_id)
            seat = booking.seat
            if seat.is_booked:
                return {'status': 'error', 'message': 'Seat already booked'}

            payment_id = f"mock_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            mock_payment = MockPayment.objects.create(
                payment_id=payment_id,
                amount=Decimal(amount),
                status='PENDING',
                booking=booking,
                metadata={"bus_name": booking.bus.bus_name, "seat_number": seat.seat_number, "user": booking.user.username}
            )

            mock_payment.status = 'COMPLETED'
            mock_payment.save()

            booking.status = 'confirmed'
            booking.save()

            seat.is_booked = True
            seat.booked_by = booking.user
            seat.save()

            return {'status': 'success', 'payment_id': payment_id, 'booking_id': booking_id, 'message': 'Payment completed'}
        except Booking.DoesNotExist:
            return {'status': 'error', 'message': 'Booking not found'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


mock_bkash_service = MockBKashService()
