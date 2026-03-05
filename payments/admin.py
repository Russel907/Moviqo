# payments/admin.py

from django.contrib import admin
from .models import Plan, Payment, UserSubscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'duration', 'is_active']
    list_editable = ['is_active']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'razorpay_order_id', 'amount', 'status', 'created_at']
    list_filter = ['status']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'is_active', 'started_at', 'expires_at']
