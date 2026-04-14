from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourrierViewSet, CategorieViewSet
from .partage_views import PartageLogViewSet
from .action_log_views import ActionLogViewSet

# Configuration du routeur pour les endpoints API
router = DefaultRouter()

# Endpoint pour le registre de courrier RH
router.register(r'courriers', CourrierViewSet, basename='courrier')

# Endpoint pour les catégories de courrier
router.register(r'categories', CategorieViewSet, basename='categorie')

# Endpoint pour l'historique des partages
router.register(r'partages', PartageLogViewSet, basename='partage')

# Endpoint pour les logs d'actions (journal d'audit)
router.register(r'action-logs', ActionLogViewSet, basename='action-log')

urlpatterns = [
    path('', include(router.urls)),
]