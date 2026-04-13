"""
ViewSet pour gérer les logs d'actions (audit trail)
"""

from rest_framework import viewsets, filters as rest_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from datetime import datetime, timedelta

from .models import ActionLog
from .serializer import ActionLogSerializer
from users.permissions import IsRHOrAdmin


class ActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet en lecture seule pour consulter le journal d'audit.
    
    Routes disponibles :
    - GET /api/action-logs/ : Liste de toutes les actions
    - GET /api/action-logs/{id}/ : Détails d'une action
    - GET /api/action-logs/statistiques/ : Statistiques sur les actions
    - GET /api/action-logs/mes_actions/ : Actions de l'utilisateur connecté
    """
    queryset = ActionLog.objects.select_related(
        'utilisateur',
        'courrier',
        'document'
    ).all()
    serializer_class = ActionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter, rest_filters.OrderingFilter]
    search_fields = ['description', 'utilisateur_username', 'courrier_numero', 'document_nom']
    ordering_fields = ['timestamp', 'action_type']
    ordering = ['-timestamp']
    filterset_fields = ['action_type', 'utilisateur']
    
    def get_queryset(self):
        """
        Filtrer les logs selon l'utilisateur :
        - RH/Admin : tous les logs
        - Autres : seulement leurs propres actions et celles liées à leurs courriers/documents
        """
        user = self.request.user
        if user.role in ['rh', 'admin']:
            return ActionLog.objects.select_related('utilisateur', 'courrier', 'document').all()
        else:
            # Voir :
            # - Ses propres actions
            # - Actions sur courriers qui lui sont affectés (via circuits v2)
            # - Actions sur courriers de son service (via service_destinataire)
            # - Actions sur documents qu'il possède
            filters = Q(utilisateur=user) | Q(document__owner=user)
            
            # Courriers affectés via le nouveau système de circuits
            filters |= Q(courrier__circuits_v2__affectations__destinataire=user)
            
            # Courriers du service de l'utilisateur (si l'utilisateur a un service)
            if hasattr(user, 'service') and user.service:
                filters |= Q(courrier__service_destinataire=user.service.nom) | Q(courrier__service_emetteur=user.service.nom)
            
            return ActionLog.objects.filter(filters).select_related(
                'utilisateur', 'courrier', 'document'
            ).distinct()
    
    @action(detail=False, methods=['get'])
    def mes_actions(self, request):
        """
        Récupérer les actions effectuées par l'utilisateur connecté.
        URL : GET /api/action-logs/mes_actions/
        """
        actions = self.queryset.filter(utilisateur=request.user)
        
        # Appliquer les filtres
        actions = self.filter_queryset(actions)
        
        # Pagination
        page = self.paginate_queryset(actions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(actions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """
        Récupérer les statistiques sur les actions.
        URL : GET /api/action-logs/statistiques/
        """
        queryset = self.get_queryset()
        
        # Statistiques globales
        total_actions = queryset.count()
        
        # Par type d'action
        actions_par_type = {}
        for action_type, label in ActionLog.TYPE_ACTION_CHOICES:
            count = queryset.filter(action_type=action_type).count()
            if count > 0:
                actions_par_type[action_type] = {
                    'count': count,
                    'label': label
                }
        
        # Actions des 7 derniers jours
        date_il_y_a_7_jours = datetime.now() - timedelta(days=7)
        actions_recentes = queryset.filter(timestamp__gte=date_il_y_a_7_jours).count()
        
        # Actions du jour
        aujourdhui = datetime.now().date()
        actions_aujourdhui = queryset.filter(timestamp__date=aujourdhui).count()
        
        # Top utilisateurs (seulement pour RH/Admin)
        top_utilisateurs = []
        if request.user.role in ['rh', 'admin']:
            top_utilisateurs = list(
                queryset.values('utilisateur_username', 'utilisateur_nom_complet')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            )
        
        return Response({
            'total_actions': total_actions,
            'actions_par_type': actions_par_type,
            'actions_7_derniers_jours': actions_recentes,
            'actions_aujourdhui': actions_aujourdhui,
            'top_utilisateurs': top_utilisateurs,
        })
    
    @action(detail=False, methods=['get'])
    def par_courrier(self, request):
        """
        Récupérer les logs liés à un courrier spécifique.
        URL : GET /api/action-logs/par_courrier/?courrier_id=123
        """
        courrier_id = request.query_params.get('courrier_id')
        if not courrier_id:
            return Response({'error': 'courrier_id requis'}, status=400)
        
        actions = self.get_queryset().filter(courrier_id=courrier_id)
        serializer = self.get_serializer(actions, many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def par_utilisateur(self, request):
        """
        Récupérer les logs d'un utilisateur spécifique (RH/Admin seulement).
        URL : GET /api/action-logs/par_utilisateur/?utilisateur_id=123
        """
        if request.user.role not in ['rh', 'admin']:
            return Response({'error': 'Permission refusée'}, status=403)
        
        utilisateur_id = request.query_params.get('utilisateur_id')
        if not utilisateur_id:
            return Response({'error': 'utilisateur_id requis'}, status=400)
        
        actions = ActionLog.objects.filter(utilisateur_id=utilisateur_id).order_by('-timestamp')
        
        # Pagination
        page = self.paginate_queryset(actions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(actions, many=True)
        return Response(serializer.data)
