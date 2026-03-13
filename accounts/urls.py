from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import admin_views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('phone-login/', views.phone_login_view, name='phone_login'),
    path('phone-verify/', views.phone_verify_view, name='phone_verify'),
    path('verify-email/', views.verify_email_otp_view, name='verify_email_otp'),
    path('resend-email-otp/', views.resend_email_otp_view, name='resend_email_otp'),
    path('profile/', views.profile_view, name='profile'),
    path('complete_profile/', views.complete_profile_view, name='complete_profile'),
    path('deactivate-account/', views.deactivate_account_view, name='deactivate_account'),
    path('reactivate-account/', views.reactivate_account_view, name='reactivate_account'),
    path('home/', views.home_view, name='home'),
    path('staff/dashboard/', RedirectView.as_view(pattern_name='custom_admin_overview'), name='admin_dashboard'),
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('kitchen/sales-summary/', views.kitchen_sales_summary, name='kitchen_sales_summary'),
    path('kitchen/api/scan-qr/', views.kitchen_scan_qr_api, name='kitchen_scan_qr_api'),

    # New Admin Panel
    path('admin-dashboard/', admin_views.admin_overview, name='custom_admin_overview'),
    path('admin-dashboard/orders/', admin_views.admin_orders, name='custom_admin_orders'),
    path('admin-dashboard/orders/export/', admin_views.admin_orders_export, name='custom_admin_orders_export'),
    path('admin-dashboard/menu/', admin_views.admin_menu, name='custom_admin_menu'),
    path('admin-dashboard/users/', admin_views.admin_users, name='custom_admin_users'),
    path('admin-dashboard/feedback/', admin_views.admin_feedback, name='custom_admin_feedback'),
    path('admin-dashboard/settings/', admin_views.admin_settings, name='custom_admin_settings'),
    path('admin-dashboard/whatsapp/', admin_views.admin_whatsapp, name='custom_admin_whatsapp'),
    path('admin-dashboard/api/chart-data/', admin_views.admin_chart_data, name='custom_admin_chart_data'),
    path('admin-dashboard/api/stats/', admin_views.admin_dashboard_api, name='custom_admin_dashboard_api'),
    path('admin-dashboard/api/orders/', admin_views.admin_orders_api, name='custom_admin_orders_api'),
    path('admin-dashboard/api/users/', admin_views.admin_users_api, name='custom_admin_users_api'),
    path('feedback/', views.feedback_view, name='user_feedback'),
    path('terms/', views.terms_view, name='terms'),

    # OTP-Based Password Reset
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/verify/', views.forgot_password_verify_view, name='forgot_password_verify'),
    path('forgot-password/reset/', views.forgot_password_reset_view, name='forgot_password_reset'),
    path('forgot-password/resend/', views.forgot_password_resend_view, name='forgot_password_resend'),
]

