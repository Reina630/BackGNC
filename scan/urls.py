from django.urls import path
from . import views

urlpatterns = [
    path('detect/', views.detect_corners, name='scan-detect'),
    path('warp/', views.warp_document, name='scan-warp'),
]