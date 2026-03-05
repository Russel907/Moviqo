# payments/serializers.py

from rest_framework import serializers
from .models import Plan, Payment, UserSubscription


class PlanSerializer(serializers.ModelSerializer):
    amount_in_rupees = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = ['id', 'name', 'description', 'amount', 'amount_in_rupees', 'duration']

    def get_amount_in_rupees(self, obj):
        return obj.amount / 100


class CreateOrderSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate_plan_id(self, value):
        try:
            plan = Plan.objects.get(id=value, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive plan.")
        return value


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class PaymentSerializer(serializers.ModelSerializer):
    plan = PlanSerializer()

    class Meta:
        model = Payment
        fields = ['id', 'plan', 'razorpay_order_id', 'razorpay_payment_id', 'amount', 'status', 'created_at']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer()

    class Meta:
        model = UserSubscription
        fields = ['plan', 'is_active', 'started_at', 'expires_at']
