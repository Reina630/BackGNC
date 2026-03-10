from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet, DocumentShareViewSet, ShareRequestViewSet, 
    CourrierViewSet, CategorieViewSet, AffectationCourrierViewSet, CommentaireCourrierViewSet
)
from .partage_views import PartageLogViewSet

# Configuration du routeur pour les endpoints API
router = DefaultRouter()

# Endpoints existants (système GED complet - à conserver pour compatibilité)
router.register(r'document', DocumentViewSet, basename='document')
router.register(r'share', DocumentShareViewSet, basename='share')
router.register(r'share-request', ShareRequestViewSet, basename='share-request')

# NOUVEAU : Endpoint pour le registre de courrier RH
# URL : /api/courriers/
router.register(r'courriers', CourrierViewSet, basename='courrier')

# Endpoint pour les catégories de courrier
# URL: /api/categories/
router.register(r'categories', CategorieViewSet, basename='categorie')

# Endpoint pour l'historique des partages
# URL: /api/partages/
router.register(r'partages', PartageLogViewSet, basename='partage')

# NOUVEAU : Endpoints pour les affectations de courriers
# URL : /api/affectations/
router.register(r'affectations', AffectationCourrierViewSet, basename='affectation')

# Endpoint pour les commentaires d'affectations
# URL: /api/commentaires-courriers/  
router.register(r'commentaires-courriers', CommentaireCourrierViewSet, basename='commentaire-courrier')

urlpatterns = [
    path('', include(router.urls)),
]