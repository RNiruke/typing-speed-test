from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path("try-again/", views.try_again, name="try_again"),
    path("csrf/",       views.get_csrf_token, name="csrf_token"), 
    # path('dashboard/', views.dashboard, name='dashboard'),
    # path("test-ocr/", views.test_ocr),
    path("performance/", views.performance, name="performance"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/<uidb64>/<token>/", views.reset_password, name="reset_password"),
   ]
