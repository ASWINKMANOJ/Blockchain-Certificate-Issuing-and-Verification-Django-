from django.urls import path
from .views import login_user, owner_dashboard, organization_dashboard, verify_certificate, print_certificate_pdf
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("auth/", login_user, name="login"),
    path("owner/", owner_dashboard, name="owner_dashboard"),
    path("organization/", organization_dashboard, name="organization_dashboard"),
    path("", verify_certificate, name="verify_certificate"),
    path("print_certificate/<str:certificate_id>/", print_certificate_pdf, name="print_certificate"),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
