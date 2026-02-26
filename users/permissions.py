from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permission personnalisée : seuls les utilisateurs avec role='admin' sont autorisés
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrSelf(permissions.BasePermission):
    """
    Permission : admin peut tout faire, les autres utilisateurs ne peuvent que se modifier eux-mêmes
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin peut tout faire
        if request.user.role == 'admin':
            return True
        # Les autres utilisateurs peuvent uniquement accéder à leur propre profil
        return obj == request.user


class IsRHOrAdmin(permissions.BasePermission):
    """
    Permission pour le registre de courrier.
    Autorise uniquement les utilisateurs avec role='rh' ou role='admin'.
    Utilisé pour restreindre l'accès au système de gestion des courriers.
    """
    def has_permission(self, request, view):
        # Vérifier que l'utilisateur est authentifié
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Autoriser les admin et les RH
        return request.user.role in ['admin', 'rh']
