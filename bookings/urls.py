
from django.urls import path
from . import views

urlpatterns = [
    # ---------------- AUTH ----------------
    path('api/register/', views.RegisterView.as_view(), name='register'),
    path('api/login/', views.LoginView.as_view(), name='login'),

    # ---------------- BUSES ----------------
    path('api/buses/', views.BusListCreateView.as_view(), name='bus-list'),
    path('api/buses/<int:pk>/', views.BusDetailView.as_view(), name='bus-detail'),

    # ---------------- BOOKINGS ----------------
    path('api/booking/', views.BookingView.as_view(), name='booking'),
    path('api/user/<int:user_id>/bookings/', views.UserBookingView.as_view(), name='user-bookings'),

    # ---------------- CANCELLATIONS ----------------
    path('api/booking/<int:booking_id>/request-cancellation/', views.RequestCancellationView.as_view(), name='request-cancellation'),
    path('api/admin/cancellations/', views.AdminCancellationListView.as_view(), name='admin-cancellations'),
    path('api/admin/cancellations/<int:request_id>/process/', views.AdminProcessCancellationView.as_view(), name='process-cancellation'),

    # ---------------- MOCK PAYMENT ----------------
    path('api/bkash/mock-payment/', views.create_mock_payment, name='mock-payment'),
]
