from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

# In "admin" mode the forgot-password page queues a request that the system
# administrator handles manually (no email infrastructure needed). In
# "email" mode it sends a self-service reset link by email instead.
if settings.PASSWORD_RESET_MODE == "email":
    password_reset_urls = [
        path(
            "password-reset/",
            auth_views.PasswordResetView.as_view(),
            name="password_reset",
        ),
        path(
            "password-reset/done/",
            auth_views.PasswordResetDoneView.as_view(),
            name="password_reset_done",
        ),
        path(
            "password-reset/<uidb64>/<token>/",
            auth_views.PasswordResetConfirmView.as_view(),
            name="password_reset_confirm",
        ),
        path(
            "password-reset/complete/",
            auth_views.PasswordResetCompleteView.as_view(),
            name="password_reset_complete",
        ),
    ]
else:
    password_reset_urls = [
        path("password-reset/", views.forgot_password, name="password_reset"),
    ]

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    *password_reset_urls,
    path("signup/", views.signup, name="signup"),
    path("login/", views.RateLimitedLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("settings/", views.profile_edit, name="profile_edit"),
    path("clients/", views.client_list, name="client_list"),
    path("clients/new/", views.client_create, name="client_create"),
    path("clients/<int:pk>/edit/", views.client_edit, name="client_edit"),
    path("clients/<int:pk>/delete/", views.client_delete, name="client_delete"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),
    path("invoices/<int:pk>/mark-sent/", views.invoice_mark_sent, name="invoice_mark_sent"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("invoices/<int:pk>/payments/new/", views.payment_add, name="payment_add"),
]
