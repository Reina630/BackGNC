from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CircuitViewSet, AffectationViewSet

router = DefaultRouter()
router.register(r'circuits', CircuitViewSet, basename='circuit')
router.register(r'affectations', AffectationViewSet, basename='affectation')

urlpatterns = [
    path('', include(router.urls)),
]
