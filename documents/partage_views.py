"""
Views pour la gestion des partages de courriers
"""
from django_filters import rest_framework as filters
from django.db.models import Count
from django.core.mail import EmailMessage
from rest_framework import viewsets, status
from rest_framework import filters as rest_filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import os

from .models import PartageLog, Courrier
from .serializer import PartageLogSerializer, PartageLogCreateSerializer
from users.permissions import IsRHOrAdmin


class PartageFilter(filters.FilterSet):
    """
    Filtres personnalisés pour l'historique des partages
    """
    date_debut = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_fin = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    courrier_numero = filters.CharFilter(field_name='courrier__numero_registre', lookup_expr='icontains')
    
    class Meta:
        model = PartageLog
        fields = ['type_partage', 'courrier', 'partage_par', 'date_debut', 'date_fin']


class PartageLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer l'historique des partages de courriers.
    
    Routes disponibles :
    - GET /api/partages/ : Liste tous les partages (avec filtres)
    - POST /api/partages/ : Créer un nouveau partage
    - GET /api/partages/{id}/ : Détails d'un partage
    - GET /api/partages/mes_partages/ : Partages effectués par l'utilisateur connecté
    - GET /api/partages/statistiques/ : Statistiques sur les partages
    """
    queryset = PartageLog.objects.select_related(
        'courrier', 
        'partage_par'
    ).all()
    permission_classes = [IsAuthenticated, IsRHOrAdmin]
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter, rest_filters.OrderingFilter]
    filterset_class = PartageFilter
    search_fields = ['destinataire', 'courrier__numero_registre', 'courrier__objet']
    ordering_fields = ['created_at', 'type_partage']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Utiliser le bon serializer selon l'action"""
        if self.action == 'create':
            return PartageLogCreateSerializer
        return PartageLogSerializer
    
    def perform_create(self, serializer):
        """Enregistrer l'utilisateur qui a partagé"""
        serializer.save(partage_par=self.request.user)
    
    @action(detail=False, methods=['get'])
    def mes_partages(self, request):
        """
        Récupérer tous les partages effectués par l'utilisateur connecté.
        URL : GET /api/partages/mes_partages/
        """
        partages = self.queryset.filter(partage_par=request.user)
        
        # Appliquer les filtres
        partages = self.filter_queryset(partages)
        
        # Pagination
        page = self.paginate_queryset(partages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(partages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """
        Statistiques sur les partages de courriers.
        URL : GET /api/partages/statistiques/
        
        Retourne :
        - Total des partages
        - Partages par type (email, whatsapp)
        - Partages par utilisateur
        - Top 5 des courriers les plus partagés
        """
        # Total des partages
        total = self.queryset.count()
        
        # Partages par type
        par_type = {}
        for type_choice in PartageLog.TYPE_PARTAGE_CHOICES:
            type_code = type_choice[0]
            count = self.queryset.filter(type_partage=type_code).count()
            par_type[type_code] = {
                'label': type_choice[1],
                'count': count
            }
        
        # Partages par utilisateur (top 10)
        par_utilisateur = self.queryset.values(
            'partage_par__username',
            'partage_par__email'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Courriers les plus partagés (top 5)
        courriers_populaires = self.queryset.values(
            'courrier__numero_registre',
            'courrier__objet',
            'courrier__type_courrier'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return Response({
            'total': total,
            'par_type': par_type,
            'par_utilisateur': list(par_utilisateur),
            'courriers_populaires': list(courriers_populaires)
        })

    @action(detail=False, methods=['post'])
    def send_email(self, request):
        """
        Envoyer un courrier par email avec le fichier en pièce jointe.
        URL : POST /api/partages/send_email/
        
        Body : {
            "courrier_id": 1,
            "destinataire": "email@example.com",
            "message": "Message personnalisé (optionnel)"
        }
        """
        courrier_id = request.data.get('courrier_id')
        destinataire = request.data.get('destinataire')
        message_perso = request.data.get('message', '')
        
        # Validation des données
        if not courrier_id:
            return Response(
                {'error': 'Le courrier_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not destinataire:
            return Response(
                {'error': 'Le destinataire est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que le courrier existe
        try:
            courrier = Courrier.objects.get(id=courrier_id)
        except Courrier.DoesNotExist:
            return Response(
                {'error': 'Courrier introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier que le fichier existe
        if not courrier.fichier:
            return Response(
                {'error': 'Ce courrier n\'a pas de fichier attaché'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Préparer le sujet de l'email
            subject = f"Partage de courrier - {courrier.numero_registre}"
            
            # Préparer le corps de l'email
            body = f"""
Bonjour,

Vous trouverez ci-joint le courrier suivant :

Numéro de registre : {courrier.numero_registre}
Type : {courrier.get_type_courrier_display()}
Objet : {courrier.objet}
Date : {courrier.date_reception or courrier.date_envoi or 'N/A'}
Expéditeur : {courrier.expediteur}
Destinataire : {courrier.destinataire}
"""
            
            # Ajouter le message personnalisé s'il existe
            if message_perso:
                body += f"\nMessage :\n{message_perso}\n"
            
            body += "\nCordialement,"
            
            # Créer l'email avec pièce jointe
            email = EmailMessage(
                subject=subject,
                body=body,
                to=[destinataire],
            )
            
            # Attacher le fichier si disponible
            if courrier.fichier:
                file_path = courrier.fichier.path
                if os.path.exists(file_path):
                    email.attach_file(file_path)
            
            # Envoyer l'email
            email.send(fail_silently=False)
            
            # Créer une entrée dans l'historique des partages
            partage = PartageLog.objects.create(
                courrier=courrier,
                type_partage='email',
                destinataire=destinataire,
                partage_par=request.user
            )
            
            return Response({
                'success': True,
                'message': 'Email envoyé avec succès',
                'partage_id': partage.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Log l'erreur pour le debug
            import traceback
            print(f"Erreur lors de l'envoi de l'email: {str(e)}")
            print(traceback.format_exc())
            
            return Response(
                {'error': f'Erreur lors de l\'envoi de l\'email : {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
