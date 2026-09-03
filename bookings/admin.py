
from django.contrib import admin
from .models import Bus, Seat, Booking, MockPayment, CancellationRequest, UserProfile
from django.utils import timezone

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone']
    search_fields = ['user__username', 'phone']

class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_name', 'number', 'origin', 'destination', 'start_time', 'reach_time', 'price', 'get_total_seats')
    def get_total_seats(self, obj): return obj.seats.count()
    get_total_seats.short_description = "Total Seats"

class SeatAdmin(admin.ModelAdmin):
    list_display = ('seat_number', 'bus', 'is_booked', 'booked_by')

class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'bus', 'seat', 'booking_time', 'status')

class MockPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'amount', 'status', 'booking', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment_id',)

class CancellationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'user', 'status', 'requested_at', 'processed_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('user__username', 'booking__id')
    readonly_fields = ('requested_at', 'processed_at')
    actions = ['approve_selected_requests', 'reject_selected_requests']
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            original_obj = CancellationRequest.objects.get(pk=obj.pk)
            original_status = original_obj.status
            if original_status == 'pending' and obj.status == 'approved':
                obj.approve("Approved via admin panel"); return
            elif original_status == 'pending' and obj.status == 'rejected':
                obj.reject("Rejected via admin panel"); return
        super().save_model(request, obj, form, change)
    
    def approve_selected_requests(self, request, queryset):
        approved_count = 0
        for cancellation in queryset:
            if cancellation.status == 'pending':
                success = cancellation.approve("Approved via admin action")
                if success: approved_count += 1
        if approved_count > 0:
            self.message_user(request, f"✓ Approved {approved_count} cancellation requests")
        else:
            self.message_user(request, "No pending requests were approved", level='warning')
    
    def reject_selected_requests(self, request, queryset):
        rejected_count = 0
        for cancellation in queryset:
            if cancellation.status == 'pending':
                success = cancellation.reject("Rejected via admin action")
                if success: rejected_count += 1
        if rejected_count > 0:
            self.message_user(request, f"✓ Rejected {rejected_count} cancellation requests")
        else:
            self.message_user(request, "No pending requests were rejected", level='warning')

admin.site.register(Bus, BusAdmin)
admin.site.register(Seat, SeatAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(MockPayment, MockPaymentAdmin)
admin.site.register(CancellationRequest, CancellationRequestAdmin)