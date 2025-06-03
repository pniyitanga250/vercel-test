# myapp/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path, reverse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile, Transaction, ActivationFeeProof, AdminNews
from django.utils.html import format_html
from django.http import HttpResponse
import csv

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    

class CustomUserAdmin(UserAdmin):
    actions = ['activate_users', 'deactivate_users', 'suspend_users', 'export_as_csv']
    
    def activate_users(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f"{updated} user(s) were successfully activated.")
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f"{updated} user(s) were successfully deactivated.")
    deactivate_users.short_description = "Deactivate selected users"
    
    def suspend_users(self, request, queryset):
        updated = queryset.update(status='suspend')
        self.message_user(request, f"{updated} user(s) were successfully suspended.")
    suspend_users.short_description = "Suspend selected users"
    
    # CSV export method for User model
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [
            'username', 'email', 'phone_number', 'status', 'country',
            'date_joined', 'maintenance_due_date', 'activation_paid_date', 'activation_paid_amount',
            'maintenance_paid_date', 'maintenance_paid_amount'
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'

        writer = csv.writer(response)
        writer.writerow(field_names)

        for obj in queryset:
            writer.writerow([
                obj.username,
                obj.email,
                obj.phone_number,
                obj.status,
                obj.country,
                obj.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                obj.maintenance_due_date,
                obj.activation_paid_date,
                obj.activation_paid_amount,
                obj.maintenance_paid_date,
                obj.maintenance_paid_amount,
            ])

        return response

    export_as_csv.short_description = "Export Selected Users as CSV"
    
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'phone_number', 'colored_status', 'is_staff')
    list_filter = ('status', 'is_staff', 'is_superuser', 'groups', 'date_joined', 'maintenance_due_date')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'phone_number', 'country')}),
        ('Permissions', {
            'fields': (
                'status', 
                'is_staff', 
                'is_superuser', 
                'groups',         # Include groups here
                'user_permissions' # And also user_permissions
            )
        }),
        ('Important dates and payments', {'fields': ('date_joined', 'maintenance_due_date', 'maintenance_paid', 'maintenance_fee', 'maintenance_paid_date', 'maintenance_paid_amount','activation_paid_date', 'activation_paid_amount',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 
                'email', 
                'phone_number', 
                'country',
                'password1', 
                'password2', 
                'status', 
                'is_staff', 
                'groups'  # Allow adding groups when creating a user
            ),
        }),
    )
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('user__username', 'description')
    ordering = ('-timestamp',)
    actions = ['export_as_csv']

    # CSV export method
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = ['user', 'transaction_type', 'amount', 'description', 'timestamp']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'

        writer = csv.writer(response)
        writer.writerow(field_names)

        for obj in queryset:
            writer.writerow([
                obj.user.username if obj.user else 'No User',
                obj.transaction_type,
                obj.amount,
                obj.description,
                obj.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        return response

    export_as_csv.short_description = "Export Selected Transactions as CSV"
    
    
    def user(self, obj):
        return obj.user.username

class ActivationFeeProofAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone_number', 'proof_image_tag', 'timestamp')
    search_fields = ('user__username', 'full_name', 'phone_number')
    ordering = ('-timestamp',)

    def proof_image_tag(self, obj):
        if obj.proof_image:
            return format_html('<img src="{}" style="max-height: 200px;"/>', obj.proof_image.url)
        return "-"
    proof_image_tag.short_description = 'Proof Image'


class AdminNewsAdmin(admin.ModelAdmin):
    list_display = ['youtube_video_url']
    search_fields = ['youtube_video_url']
    list_display = ['youtube_video_url', 'image_tag']
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px;"/>', obj.image.url)
        return "-"
    image_tag.short_description = 'Image'
    
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'get_direct_referrals_count', 
        'get_left_count', 
        'get_right_count', 
        'get_total_downlines',
        'downline_tree_link',  # Added link to view downline tree
    )
    readonly_fields = (
        'get_direct_referrals_count', 
        'get_left_count', 
        'get_right_count', 
        'get_total_downlines'
    )
    search_fields = ('user__username',)
    
    actions = ['export_as_csv']  # CSV Export action added

    # CSV export method
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [
            'user', 'referral_code', 'referred_by', 'rank', 'balance',
            'total_earnings', 'total_withdrawals', 'cached_downline_count'
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'

        writer = csv.writer(response)
        writer.writerow(field_names)  # CSV header

        for obj in queryset:
            writer.writerow([
                obj.user.username,
                obj.referral_code,
                obj.referred_by.user.username if obj.referred_by else "",
                obj.rank,
                obj.balance,
                obj.total_earnings,
                obj.total_withdrawals,
                obj.cached_downline_count,
            ])

        return response

    export_as_csv.short_description = "Export Selected UserProfiles as CSV"

    
    def get_direct_referrals_count(self, obj):
        return obj.referrals.count()
    get_direct_referrals_count.short_description = 'Direct Referrals'
    
    def get_left_count(self, obj):
        # Count all downlines in the left branch recursively
        def count_branch(profile):
            if not profile:
                return 0
            return 1 + count_branch(profile.left_leg) + count_branch(profile.right_leg)
        return count_branch(obj.left_leg) if obj.left_leg else 0
    get_left_count.short_description = 'Left Referral (Total Downlines)'
    
    def get_right_count(self, obj):
        # Count all downlines in the right branch recursively
        def count_branch(profile):
            if not profile:
                return 0
            return 1 + count_branch(profile.left_leg) + count_branch(profile.right_leg)
        return count_branch(obj.right_leg) if obj.right_leg else 0
    get_right_count.short_description = 'Right Referral (Total Downlines)'
    
    def get_total_downlines(self, obj):
        return obj.count_downlines()
    get_total_downlines.short_description = 'Total Downlines'
    
    def downline_tree_link(self, obj):
        url = reverse('admin:userprofile-downline', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">Downline Tree</a>', url)
    downline_tree_link.short_description = 'Downline Tree'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:userprofile_id>/downline/', 
                self.admin_site.admin_view(self.downline_view), 
                name='userprofile-downline'
            ),
        ]
        return custom_urls + urls
    
    def downline_view(self, request, userprofile_id, *args, **kwargs):
        user_profile = get_object_or_404(UserProfile, pk=userprofile_id)
        # Reuse the same template as your my_team_view so the display remains consistent.
        context = dict(
            self.admin_site.each_context(request),
            user_profile=user_profile,
        )
        return TemplateResponse(request, "my_team.html", context)


admin.site.register(ActivationFeeProof, ActivationFeeProofAdmin)
admin.site.register(AdminNews, AdminNewsAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
