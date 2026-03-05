# payments/models.py

from django.db import models
from django.conf import settings


class Plan(models.Model):
    DURATION_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]

    name = models.CharField(max_length=100)               # e.g. "Basic", "Premium"
    description = models.TextField(blank=True)
    amount = models.PositiveIntegerField()                 # Amount in PAISE (₹99 = 9900)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES)
    is_active = models.BooleanField(default=True)

    def amount_in_rupees(self):
        return self.amount / 100

    def __str__(self):
        return f"{self.name} - ₹{self.amount_in_rupees()} ({self.duration})"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)

    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    amount = models.PositiveIntegerField()                 # in paise
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} | {self.plan} | {self.status}"


class UserSubscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {'Active' if self.is_active else 'Inactive'}"
