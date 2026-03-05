# payments/urls.py

from django.urls import path
from .views import (
    PlanListAPIView,
    CreateOrderAPIView,
    VerifyPaymentAPIView,
    SubscriptionStatusAPIView,
    PaymentHistoryAPIView,
    RazorpayWebhookAPIView
)

urlpatterns = [
    path('plans/', PlanListAPIView.as_view()),                  
    path('create-order/', CreateOrderAPIView.as_view()),        
    path('verify/', VerifyPaymentAPIView.as_view()),            
    path('subscription/', SubscriptionStatusAPIView.as_view()), 
    path('history/', PaymentHistoryAPIView.as_view()),          
    path('webhook/', RazorpayWebhookAPIView.as_view()),
]
