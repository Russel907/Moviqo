from django.urls import path
from .views import SignupAPIView, LoginAPIView, ProfileAPIView

urlpatterns = [
    path('signup/', SignupAPIView.as_view()),
    path('login/', LoginAPIView.as_view()),
    path('profile/', ProfileAPIView.as_view()),
]