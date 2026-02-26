from django.urls import path
from .views import (
    login_view, 
    refresh_token_view, 
    logout_view,
    users_view,
    user_detail_view,
    profile_view,
)

urlpatterns = [
    # Authentification
    path('login/', login_view, name='login'),
    path('refresh/', refresh_token_view, name='token_refresh'),
    path('logout/', logout_view, name='logout'),
    
    # Profil
    path('profile/', profile_view, name='profile'),
    
    # Gestion utilisateurs (admin)
    path('', users_view, name='users'),
    path('<int:pk>/', user_detail_view, name='user_detail'),
]
