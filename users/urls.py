from django.urls import path
from .views import (
    login_view, 
    refresh_token_view, 
    logout_view,
    users_view,
    user_detail_view,
    profile_view,
    update_signature_view,
    verify_signature_password_view,
    services_view,
    service_detail_view,
    notifications_view,
    notifications_non_lues_view,
    marquer_notification_lue_view,
    marquer_toutes_lues_view,
    supprimer_notification_view,
)

urlpatterns = [
    # Authentification
    path('login/', login_view, name='login'),
    path('refresh/', refresh_token_view, name='token_refresh'),
    path('logout/', logout_view, name='logout'),
    
    # Profil
    path('profile/', profile_view, name='profile'),
    
    # Signature électronique
    path('signature/', update_signature_view, name='update_signature'),
    path('signature/verify/', verify_signature_password_view, name='verify_signature_password'),
    
    # Gestion utilisateurs (admin)
    path('', users_view, name='users'),
    path('<int:pk>/', user_detail_view, name='user_detail'),
    
    # Gestion services
    path('services/', services_view, name='services'),
    path('services/<int:pk>/', service_detail_view, name='service_detail'),
    
    # Notifications
    path('notifications/', notifications_view, name='notifications'),
    path('notifications/non-lues/', notifications_non_lues_view, name='notifications_non_lues'),
    path('notifications/<int:pk>/lue/', marquer_notification_lue_view, name='marquer_notification_lue'),
    path('notifications/marquer-toutes-lues/', marquer_toutes_lues_view, name='marquer_toutes_lues'),
    path('notifications/<int:pk>/', supprimer_notification_view, name='supprimer_notification'),
]
