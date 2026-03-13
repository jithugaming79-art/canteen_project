from django.urls import path
from . import views

urlpatterns = [
    path('payment/<int:order_id>/', views.payment_page, name='payment_page'),
    path('payment/<int:order_id>/cash/', views.process_cash_payment, name='process_cash_payment'),
    path('payment/<int:order_id>/wallet/', views.process_wallet_payment, name='process_wallet_payment'),
    path('payment/<int:order_id>/online/', views.process_online_payment, name='process_online_payment'),
    path('payment/<int:order_id>/dodo/success/', views.dodo_success, name='dodo_success'),
    path('dodo/webhook/', views.dodo_webhook, name='dodo_webhook'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/add/', views.add_money_to_wallet, name='add_money_to_wallet'),
    path('wallet/topup/success/', views.wallet_topup_success, name='wallet_topup_success'),
    path('api/payment/<int:payment_id>/status/', views.payment_status_api, name='payment_status_api'),
]

