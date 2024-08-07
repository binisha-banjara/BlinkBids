from django.urls import path, include
from djoser.views import TokenCreateView
from .views import home,get_user_from_jwt

urlpatterns = [
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("token/", TokenCreateView.as_view(), name="token_create"),
    path("info/",get_user_from_jwt,name="info"),
]