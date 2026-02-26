from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourrierViewSet

# Configuration du routeur
router = DefaultRouter()
router.register(r'courriers', CourrierViewSet, basename='courrier')

urlpatterns = [
    path('', include(router.urls)),
]
