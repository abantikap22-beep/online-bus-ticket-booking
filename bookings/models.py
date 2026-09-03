import time
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

# ---------------- USER PROFILE ----------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=11)

    def __str__(self):
        return f"{self.user.username} - {self.phone}"


# ---------------- BUS & SEAT ----------------
class Bus(models.Model):
    bus_name = models.CharField(max_length=100)
    number = models.CharField(max_length=20, unique=True)
    origin = models.CharField(max_length=50)
    destination = models.CharField(max_length=50)
    features = models.TextField()
    start_time = models.TimeField()
    reach_time = models.TimeField()
    no_of_seats = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.bus_name} ({self.number}) | {self.origin} → {self.destination}"


class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)
    booked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        status = "Booked" if self.is_booked else "Available"
        return f"Seat {self.seat_number} - {self.bus.bus_name} ({status})"

    def is_available(self):
        """Seat is available if not booked and no active booking"""
        active_bookings = self.booking_set.exclude(status__in=['cancelled'])
        return not active_bookings.exists() and not self.is_booked


# ---------------- BOOKING ----------------
class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancellation_requested', 'Cancellation Requested'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    booking_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Booking #{self.id} - {self.user.username} ({self.bus.bus_name}, Seat {self.seat.seat_number})"


# ---------------- CANCELLATION REQUEST ----------------
class CancellationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Cancellation Request #{self.id} - {self.booking}"

    def approve(self, admin_notes=""):
        try:
            self.status = 'approved'
            self.processed_at = timezone.now()
            self.admin_notes = admin_notes
            self.save()

            booking = self.booking
            booking.status = 'cancelled'
            booking.save()

            seat = booking.seat
            seat.is_booked = False
            seat.booked_by = None
            seat.save()
            return True
        except Exception:
            self.status = 'pending'
            self.save()
            return False

    def reject(self, admin_notes=""):
        try:
            self.status = 'rejected'
            self.processed_at = timezone.now()
            self.admin_notes = admin_notes
            self.save()

            booking = self.booking
            booking.status = 'confirmed'
            booking.save()

            seat = booking.seat
            if not seat.is_booked:
                seat.is_booked = True
                seat.booked_by = booking.user
                seat.save()
            return True
        except Exception:
            self.status = 'pending'
            self.save()
            return False


# ---------------- MOCK PAYMENT ----------------
class MockPayment(models.Model):
    payment_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default="PENDING")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"MockPayment {self.payment_id} ({self.status})"


# ---------------- USER PROFILE SIGNALS ----------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, phone="temporary")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
