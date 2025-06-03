from django.contrib import admin
from django.utils.html import format_html
from .models import Payment
from .models import Withdrawal
from .models import Deposit
from .models import SupportMessage
from .models import MaintenancePayment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id',
        'user',
        'product',
        'amount',
        'payment_method',
        'colored_status',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('transaction_id', 'user__username', 'full_name', 'product__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at',)
    actions = ['mark_as_completed', 'mark_as_delivered']

    def colored_status(self, obj):
        """Return the payment status with colored text for quick identification."""
        if obj.status in [Payment.COMPLETED, Payment.DELIVERED]:
            color = 'green'
        elif obj.status == Payment.CANCELLED:
            color = 'red'
        else:
            color = 'orange'
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
    colored_status.short_description = 'Status'

    def mark_as_completed(self, request, queryset):
        updated_count = queryset.update(status=Payment.COMPLETED)
        self.message_user(request, f"{updated_count} payment(s) successfully marked as completed.")
    mark_as_completed.short_description = "Mark selected payments as Completed"

    def mark_as_delivered(self, request, queryset):
        updated_count = queryset.update(status=Payment.DELIVERED)
        self.message_user(request, f"{updated_count} payment(s) successfully marked as delivered.")
    mark_as_delivered.short_description = "Mark selected payments as Delivered"




class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'colored_status', 'requested_at', 'processed_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('user__username',)
    actions = ['mark_as_completed', 'mark_as_declined']

    def colored_status(self, obj):
        if obj.status == 'pending':
            color = 'orange'
        elif obj.status == 'completed':
            color = 'green'
        elif obj.status == 'declined':
            color = 'red'
        else:
            color = 'black'
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
    colored_status.short_description = 'Status'

    def mark_as_completed(self, request, queryset):
        updated_count = queryset.update(status='completed')
        self.message_user(request, f"{updated_count} withdrawal(s) successfully marked as completed.")
    mark_as_completed.short_description = "Mark selected withdrawals as Completed"

    def mark_as_declined(self, request, queryset):
        updated_count = queryset.update(status='declined')
        self.message_user(request, f"{updated_count} withdrawal(s) successfully marked as declined.")
    mark_as_declined.short_description = "Mark selected withdrawals as Declined"


class RepliedFilter(admin.SimpleListFilter):
    title = 'Replied'
    parameter_name = 'replied'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Replied'),
            ('no', 'Not Replied'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(admin_reply__exact='').exclude(admin_reply__isnull=True)
        if self.value() == 'no':
            return queryset.filter(admin_reply__exact='') | queryset.filter(admin_reply__isnull=True)
        return queryset

@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'created_at', 'admin_reply', 'reply_at')
    search_fields = ('user__username', 'content', 'admin_reply')
    list_filter = ('created_at', RepliedFilter)
    
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'amount', 'payment_method', 'colored_status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('transaction_id', 'user__username', 'full_name')
    readonly_fields = ('created_at', 'updated_at',)
    actions = ['mark_as_approved', 'mark_as_denied']

    def colored_status(self, obj):
        if obj.status == 'approved':
            color = 'green'
        elif obj.status == 'denied':
            color = 'red'
        else:
            color = 'orange'
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
    colored_status.short_description = 'Status'

    def mark_as_approved(self, request, queryset):
        updated_count = queryset.update(status='approved')
        self.message_user(request, f"{updated_count} deposit(s) successfully marked as approved.")
    mark_as_approved.short_description = "Mark selected deposits as Approved"

    def mark_as_denied(self, request, queryset):
        updated_count = queryset.update(status='denied')
        self.message_user(request, f"{updated_count} deposit(s) successfully marked as denied.")
    mark_as_denied.short_description = "Mark selected deposits as Denied"
    

@admin.register(MaintenancePayment)
class MaintenancePaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone_number', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'full_name', 'phone_number')
    ordering = ('-created_at',)

admin.site.register(Withdrawal, WithdrawalAdmin)