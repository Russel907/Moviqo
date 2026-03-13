# payments/views.py

import razorpay
import hmac
import hashlib

from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Plan, Payment, UserSubscription
from .serializers import (
    PlanSerializer,
    CreateOrderSerializer,
    VerifyPaymentSerializer,
    PaymentSerializer,
    UserSubscriptionSerializer,
)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

# Initialize Razorpay client
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID or "", settings.RAZORPAY_KEY_SECRET or "")
)


# ─────────────────────────────────────────────
# 1. List all active plans
# GET /payments/plans/
# ─────────────────────────────────────────────
class PlanListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = Plan.objects.filter(is_active=True)
        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data)


# ─────────────────────────────────────────────
# 2. Create Razorpay Order
# POST /payments/create-order/
# Body: { "plan_id": 1 }
# ─────────────────────────────────────────────
class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Prevent multiple active subscriptions
        subscription = UserSubscription.objects.filter(
            user=request.user,
            is_active=True
        ).first()

        if subscription and subscription.expires_at and subscription.expires_at > timezone.now():
            return Response(
                {"error": "You already have an active subscription."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = Plan.objects.get(id=serializer.validated_data['plan_id'])

        # Create Razorpay order
        razorpay_order = client.order.create({
            "amount": plan.amount,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "user_id": str(request.user.id),
                "plan_id": str(plan.id),
                "email": request.user.email,
            }
        })

        # Save to DB
        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            razorpay_order_id=razorpay_order['id'],
            amount=plan.amount,
            status='created',
        )

        return Response({
            "order_id": razorpay_order['id'],
            "amount": plan.amount,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "plan": PlanSerializer(plan).data,
            "user": {
                "email": request.user.email,
                "full_name": request.user.full_name,
            }
        }, status=status.HTTP_201_CREATED)
# ─────────────────────────────────────────────
# 3. Verify Payment after frontend completes it
# POST /payments/verify/
# Body: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
# ─────────────────────────────────────────────
class VerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['razorpay_order_id']
        payment_id = serializer.validated_data['razorpay_payment_id']
        signature = serializer.validated_data['razorpay_signature']

        # Fetch payment from DB
        try:
            payment = Payment.objects.get(
                razorpay_order_id=order_id,
                user=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment record not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        if payment.status == "paid":
            return Response(
                {"message": "Payment already verified."},
                status=status.HTTP_200_OK
            )

        # Verify signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
      
      
        if generated_signature != signature:
            payment.status = 'failed'
            payment.save()
            return Response(
                {"error": "Payment verification failed. Invalid signature."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark payment as paid
        payment.razorpay_payment_id = payment_id
        payment.razorpay_signature = signature
        payment.status = 'paid'
        payment.save()

        # Create or update subscription
        plan = payment.plan
        expires_at = self._get_expiry(plan.duration)

        subscription, _ = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'payment': payment,
                'is_active': True,
                'expires_at': expires_at,
            }
        )

        return Response({
            "message": "Payment successful! Subscription activated.",
            "payment_id": payment_id,
            "subscription": UserSubscriptionSerializer(subscription).data,
        }, status=status.HTTP_200_OK)

    def _get_expiry(self, duration):
        now = timezone.now()
        mapping = {
            'weekly': timedelta(weeks=1),
            'monthly': timedelta(days=30),
            'yearly': timedelta(days=365),
            'lifetime': timedelta(days=36500),  # 100 years
        }
        return now + mapping.get(duration, timedelta(days=30))


# ─────────────────────────────────────────────
# 4. Check current user's subscription status
# GET /payments/subscription/
# ─────────────────────────────────────────────
class SubscriptionStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            # Auto-expire check
            if subscription.expires_at and subscription.expires_at < timezone.now():
                subscription.is_active = False
                subscription.save()
            return Response(UserSubscriptionSerializer(subscription).data)
        except UserSubscription.DoesNotExist:
            return Response({
                "is_active": False,
                "plan": None,
                "message": "No active subscription."
            })


# ─────────────────────────────────────────────
# 5. Payment history
# GET /payments/history/
# ─────────────────────────────────────────────
class PaymentHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user).order_by('-created_at')
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

        payload = request.body
        received_signature = request.headers.get('X-Razorpay-Signature')
        
        if not received_signature:
            return Response({"error": "Missing signature"}, status=400)

        # Verify webhook signature
        generated_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(generated_signature, received_signature):
            return Response({"error": "Invalid webhook signature"}, status=400)

        data = json.loads(payload)
        event = data.get("event")

        # Handle payment captured
        if event == "payment.captured":
            payment_data = data["payload"]["payment"]["entity"]
            order_id = payment_data["order_id"]
            payment_id = payment_data["id"]

            try:
                payment = Payment.objects.get(razorpay_order_id=order_id)
                payment.razorpay_payment_id = payment_id
                payment.status = "paid"
                payment.save()

                # Activate subscription
                plan = payment.plan
                expires_at = self._get_expiry(plan.duration)

                UserSubscription.objects.update_or_create(
                    user=payment.user,
                    defaults={
                        "plan": plan,
                        "payment": payment,
                        "is_active": True,
                        "expires_at": expires_at,
                    },
                )

            except Payment.DoesNotExist:
                pass

        # Handle payment failed
        if event == "payment.failed":
            payment_data = data["payload"]["payment"]["entity"]
            order_id = payment_data["order_id"]
            try:
                payment = Payment.objects.filter(
                    razorpay_order_id=order_id
                ).first()
                if payment:
                    payment.status = "failed"
                    payment.save()
            except Exception:
                pass

        # Handle refund
        if event == "refund.processed":
            refund_data = data["payload"]["refund"]["entity"]
            payment_id = refund_data["payment_id"]

            try:
                payment = Payment.objects.filter(razorpay_payment_id=payment_id).first()
                if not payment:
                    return Response({"status": "success"})
                payment.status = "failed"
                payment.save()

                # Deactivate subscription
                subscription = UserSubscription.objects.filter(user=payment.user).first()
                if subscription:
                    subscription.is_active = False
                    subscription.save()

            except Payment.DoesNotExist:
                pass

        return Response({"status": "success"})

    def _get_expiry(self, duration):
        mapping = {
            'weekly': timedelta(weeks=1),
            'monthly': timedelta(days=30),
            'yearly': timedelta(days=365),
            'lifetime': timedelta(days=36500),
        }
        return mapping.get(duration, timedelta(days=30))