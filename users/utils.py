"""
Fonctions utilitaires pour la gestion des notifications
"""
from .models import Notification, User


def creer_notification(utilisateur, type_notif, titre, message, courrier_id=None, document_id=None):
    """
    Créer une nouvelle notification pour un utilisateur
    
    Args:
        utilisateur: Instance de User ou ID
        type_notif: Type de notification ('courrier_affecte', 'document_partage', etc.)
        titre: Titre de la notification
        message: Message de la notification
        courrier_id: ID du courrier concerné (optionnel)
        document_id: ID du document concerné (optionnel)
    
    Returns:
        La notification créée
    """
    if isinstance(utilisateur, int):
        utilisateur = User.objects.get(id=utilisateur)
    
    notification = Notification.objects.create(
        utilisateur=utilisateur,
        type=type_notif,
        titre=titre,
        message=message,
        courrier_id=courrier_id,
        document_id=document_id,
    )
    
    return notification


def creer_notifications_service(service, type_notif, titre, message, courrier_id=None, document_id=None):
    """
    Créer des notifications pour tous les utilisateurs d'un service
    
    Args:
        service: Instance de Service ou ID
        type_notif: Type de notification
        titre: Titre de la notification
        message: Message de la notification
        courrier_id: ID du courrier concerné (optionnel)
        document_id: ID du document concerné (optionnel)
    
    Returns:
        Liste des notifications créées
    """
    from .models import Service
    
    if isinstance(service, int):
        service = Service.objects.get(id=service)
    
    notifications = []
    utilisateurs = service.utilisateurs.filter(is_active=True)
    
    for utilisateur in utilisateurs:
        notification = creer_notification(
            utilisateur=utilisateur,
            type_notif=type_notif,
            titre=titre,
            message=message,
            courrier_id=courrier_id,
            document_id=document_id,
        )
        notifications.append(notification)
    
    return notifications
