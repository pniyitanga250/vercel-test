from django.urls import path
from .views import login_view, logout_view, register_view, dashboard, activation_view, activation_success_view, maintenance_due_view
from .views import home, about, my_team_view, my_profile_view, earning_history
from . import views


urlpatterns = [
    
    path('', home, name='home'),
    path('about/', about, name='about'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),  # Add registration URL
    path('dashboard/', dashboard, name='dashboard'),  # Add dashboard URL
    path('activation/', activation_view, name='activation'),  # Add activation URL
    path('activation_success/', activation_success_view, name='activation_success'),
    path('maintenance_due/', maintenance_due_view, name='maintenance_due'),
    path('my_team/', my_team_view, name='my_team'),
    path('my_profile/', views.my_profile_view, name='my_profile'),
    path('earning_history/', earning_history, name='earning_history'),
    path('earning_history/ajax/', views.earning_history_ajax, name='earning_history_ajax'),

]
