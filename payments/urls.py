from django.urls import path
from . import views

urlpatterns = [
    path('payment/<int:product_id>/', views.payment_page, name='payment_page'),
    path('history/', views.payment_history, name='payment_history'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('deposit/', views.deposit, name='deposit'),
    path('support/', views.support_thread, name='support_thread'),
    path('maintenance_fee/', views.maintenance_fee_view, name='maintenance_fee'),
]

