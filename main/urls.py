from django.urls import path
from .views import index,login_view, signup_view,home_view
from django.contrib.auth import views as auth_views
from .views import regional_governance
from .views import upload_excel_view
from .views import regional_market_conditions,consumer_perception,regional_overview,logout_view,re_rmi_summary
from . import views
from .views import help_view  # Import the new help view

urlpatterns = [
    path('', index, name='index'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),  # Password reset view
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),  # Success view
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),  # Confirm reset
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),  # Completion view
    path('home/', home_view, name='home'),
    path('upload_excel/', upload_excel_view, name='upload_excel'),
    path('regional_governance/', regional_governance, name='regional_governance'),
    path('regional_market_conditions/', regional_market_conditions, name='regional_market_conditions'),
    path('consumer_perception/', consumer_perception, name='consumer_perception'),
    path('regional_overview/', regional_overview, name='regional_overview'),
    path('logout/', logout_view, name='logout'),
    path('api/get-topic-data/<int:topic_id>/', views.get_topic_data, name='get_topic_data'),
    path('re_rmi_summary/', views.re_rmi_summary, name='re_rmi_summary'),
    path('help/', views.help_view, name='help')  # Add the help page URL pattern
]