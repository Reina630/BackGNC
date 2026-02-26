from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Courrier
from .serializers import CourrierSerializer, CourrierCreateSerializer, CourrierUpdateSerializer


class CourrierViewSet(viewsets.ModelViewSet):
    """
    API ViewSet pour la gestion des courriers (entrants et sortants)
    
    Endpoints disponibles:
    - GET /api/courriers/ - Liste tous les courriers (avec filtres)
    - POST /api/courriers/ - Créer un nouveau courrier
    - GET /api/courriers/{id}/ - Détails d'un courrier
    - PUT/PATCH /api/courriers/{id}/ - Mettre à jour un courrier
    - DELETE /api/courriers/{id}/ - Supprimer un courrier
    - POST /api/courriers/{id}/archiver/ - Archiver un courrier
    - GET /api/courriers/{id}/download/ - Télécharger le fichier joint
    """
    queryset = Courrier.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Filtres disponibles
    filterset_fields = ['type', 'statut', 'categorie', 'service']
    
    # Recherche textuelle
    search_fields = ['reference', 'objet', 'description', 'expediteur', 'destinataire']
    
    # Tri
    ordering_fields = ['created_at', 'date_reception', 'date_envoi', 'reference']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Retourne le serializer approprié selon l'action
        """
        if self.action == 'create':
            return CourrierCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CourrierUpdateSerializer
        return CourrierSerializer
    
    def perform_create(self, serializer):
        """
        Ajoute automatiquement l'utilisateur connecté comme créateur
        """
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def archiver(self, request, pk=None):
        """
        Action personnalisée pour archiver un courrier
        URL: POST /api/courriers/{id}/archiver/
        """
        courrier = self.get_object()
        courrier.statut = 'archive'
        courrier.save()
        
        serializer = self.get_serializer(courrier)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Télécharger le fichier joint d'un courrier
        URL: GET /api/courriers/{id}/download/
        """
        courrier = self.get_object()
        
        if not courrier.fichier:
            return Response(
                {'error': 'Aucun fichier attaché à ce courrier'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ouvrir et retourner le fichier
        file_handle = courrier.fichier.open()
        response = FileResponse(file_handle)
        response['Content-Disposition'] = f'attachment; filename="{courrier.fichier.name.split("/")[-1]}"'
        
        return response
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """
        Retourne des statistiques sur les courriers
        URL: GET /api/courriers/statistiques/
        """
        stats = {
            'total': Courrier.objects.count(),
            'entrants': Courrier.objects.filter(type='entrant').count(),
            'sortants': Courrier.objects.filter(type='sortant').count(),
            'en_attente': Courrier.objects.filter(statut='en_attente').count(),
            'en_cours': Courrier.objects.filter(statut='en_cours').count(),
            'traites': Courrier.objects.filter(statut='traite').count(),
            'archives': Courrier.objects.filter(statut='archive').count(),
        }
        return Response(stats)
