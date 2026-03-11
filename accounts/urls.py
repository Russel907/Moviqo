from django.urls import path
from .views import SignupAPIView, LoginAPIView, ProfileAPIView, LogoutAPIView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('signup/', SignupAPIView.as_view()),
    path('login/', LoginAPIView.as_view()),
    path('profile/', ProfileAPIView.as_view()),
    path('logout/', LogoutAPIView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
]