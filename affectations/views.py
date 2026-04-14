from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from .models import Circuit, Affectation
from .serializers import (
    CircuitSerializer,
    CircuitCreateSerializer,
    AffectationSerializer,
)
from documents.models import ActionLog


# ============================================================================
# CircuitViewSet
# ============================================================================

class CircuitViewSet(viewsets.ModelViewSet):
    """
    CRUD complet sur les circuits + création groupée avec affectations.

    POST /api/affectations/circuits/          → crée un circuit avec ses affectations
    GET  /api/affectations/circuits/          → liste les circuits
    GET  /api/affectations/circuits/{id}/     → détail d'un circuit
    POST /api/affectations/circuits/{id}/annuler/  → annule le circuit
    """

    queryset = Circuit.objects.all()
    serializer_class = CircuitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Circuit.objects.select_related('courrier', 'cree_par').prefetch_related(
            'affectations__destinataire',
            'affectations__service',
            'affectations__affecte_par',
        )
        
        # Si utilisateur non authentifié, retourner queryset vide
        if not self.request.user or not self.request.user.is_authenticated:
            return qs.none()
        
        user = self.request.user

        # Admin / RH voient tout ; les autres voient uniquement les circuits
        # où ils sont destinataires d'une affectation
        if hasattr(user, 'role') and user.role in ('admin', 'rh', 'dg'):
            pass
        else:
            qs = qs.filter(affectations__destinataire=user).distinct()

        # Filtres optionnels
        courrier_id = self.request.query_params.get('courrier')
        if courrier_id:
            qs = qs.filter(courrier_id=courrier_id)

        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)

        return qs.order_by('-date_creation')

    def get_serializer_class(self):
        if self.action == 'create':
            return CircuitCreateSerializer
        return CircuitSerializer

    def create(self, request, *args, **kwargs):
        """Création explicite d'un circuit avec ses affectations."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        # CircuitCreateSerializer.create() gère tout
        serializer.save()

    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        circuit = self.get_object()
        if circuit.statut == 'termine':
            return Response(
                {'detail': 'Ce circuit est déjà terminé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        circuit.statut = 'annule'
        circuit.save(update_fields=['statut', 'date_modification'])
        return Response(CircuitSerializer(circuit, context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def progression(self, request, pk=None):
        """Retourne la progression détaillée du circuit."""
        circuit = self.get_object()
        affectations = circuit.affectations.select_related('destinataire', 'service').all()
        statuts_termines = {'valide', 'rejete', 'signe', 'renvoye'}
        data = {
            'circuit_id': circuit.id,
            'type_circuit': circuit.type_circuit,
            'statut': circuit.statut,
            'etape_actuelle': circuit.get_etape_actuelle(),
            'affectations': AffectationSerializer(
                affectations, many=True, context={'request': request}
            ).data,
        }
        return Response(data)


# ============================================================================
# AffectationViewSet
# ============================================================================

class AffectationViewSet(viewsets.ModelViewSet):
    """
    CRUD sur les affectations individuelles + actions métier.

    GET  /api/affectations/affectations/                → liste
    GET  /api/affectations/affectations/?circuit=<id>   → par circuit
    GET  /api/affectations/affectations/?courrier=<id>  → par courrier
    GET  /api/affectations/affectations/?mes_affectations=1  → mes affectations
    POST /api/affectations/affectations/{id}/marquer_lu/
    POST /api/affectations/affectations/{id}/demarrer/
    POST /api/affectations/affectations/{id}/valider/
    POST /api/affectations/affectations/{id}/signer/
    POST /api/affectations/affectations/{id}/rejeter/
    POST /api/affectations/affectations/{id}/renvoyer/
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = AffectationSerializer

    def get_queryset(self):
        qs = Affectation.objects.select_related(
            'circuit', 'courrier', 'destinataire', 'service', 'affecte_par'
        )
        
        # Si utilisateur non authentifié, retourner queryset vide
        if not self.request.user or not self.request.user.is_authenticated:
            return qs.none()
        
        user = self.request.user
        params = self.request.query_params

        # Filtre par défaut : les non-admin ne voient que leurs affectations
        if hasattr(user, 'role') and user.role not in ('admin', 'rh', 'dg'):
            qs = qs.filter(destinataire=user)

        # ?mes_affectations=1 → forcer la vue personnelle même pour admin
        if params.get('mes_affectations') == '1':
            qs = qs.filter(destinataire=user)

        # ?circuit=<id>
        if params.get('circuit'):
            qs = qs.filter(circuit_id=params['circuit'])

        # ?courrier=<id>
        if params.get('courrier'):
            qs = qs.filter(courrier_id=params['courrier'])

        # ?statut=<val>
        if params.get('statut'):
            qs = qs.filter(statut=params['statut'])

        # ?service=<id>
        if params.get('service'):
            qs = qs.filter(service_id=params['service'])

        return qs.order_by('etape_numero', '-date_affectation')

    # ------------------------------------------------------------------
    # Surcharge create/update : protection
    # ------------------------------------------------------------------

    def perform_create(self, serializer):
        serializer.save(
            affecte_par=self.request.user,
            courrier=serializer.validated_data['circuit'].courrier,
        )

    # ------------------------------------------------------------------
    # Actions métier
    # ------------------------------------------------------------------

    def _action_traitement(self, request, pk, method_name, field='commentaire'):
        affectation = self.get_object()

        if not affectation.peut_etre_traitee():
            return Response(
                {'detail': "Ce n'est pas encore votre tour (circuit séquentiel)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valeur = request.data.get(field, '')
        getattr(affectation, method_name)(valeur)
        return Response(
            AffectationSerializer(affectation, context={'request': request}).data
        )

    @action(detail=True, methods=['post'])
    def marquer_lu(self, request, pk=None):
        affectation = self.get_object()
        affectation.marquer_comme_lu()
        return Response(AffectationSerializer(affectation, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def demarrer(self, request, pk=None):
        affectation = self.get_object()
        affectation.demarrer_traitement()
        return Response(AffectationSerializer(affectation, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        return self._action_traitement(request, pk, 'valider', 'commentaire')

    @action(detail=True, methods=['post'])
    def signer(self, request, pk=None):
        affectation = self.get_object()
        
        if not affectation.peut_etre_traitee():
            return Response(
                {'detail': "Ce n'est pas encore votre tour (circuit séquentiel)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        commentaire = request.data.get('commentaire', '')
        position = request.data.get('position', {'x': 100, 'y': 100})
        size = request.data.get('size', {'width': 200, 'height': 80})
        
        # Appliquer la signature sur le PDF et créer une nouvelle version
        try:
            from documents.views import appliquer_signature_pdf
            from documents.models import Courrier
            from django.core.files.base import ContentFile
            import os
            
            courrier = affectation.courrier
            user = request.user
            
            # Vérifier que l'utilisateur a une signature
            if not user.signature_electronique or not user.signature_electronique.path:
                return Response(
                    {'detail': 'Vous devez configurer votre signature électronique avant de pouvoir signer un document.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Vérifier que le courrier a un fichier PDF
            if not courrier.fichier or not courrier.fichier.path:
                return Response(
                    {'detail': 'Le courrier ne possède pas de fichier PDF à signer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Appliquer la signature sur le PDF
            pdf_path = courrier.fichier.path
            signature_path = user.signature_electronique.path
            
            # Appliquer la signature (position en pixels du frontend, convertis en coordonnées PDF)
            pdf_signed_stream = appliquer_signature_pdf(
                pdf_path=pdf_path,
                signature_path=signature_path,
                position_x=position['x'],
                position_y=position['y'],
                largeur=size['width'],
                hauteur=size['height'],
                page_height=1200  # Hauteur du conteneur frontend
            )
            
            # Remplacer le fichier du courrier existant par la version signée
            from django.core.files.base import ContentFile
            filename = f"{courrier.numero_registre}_signe.pdf"
            
            # Sauvegarder l'ancien fichier dans les notes (optionnel - pour historique)
            old_filename = courrier.fichier.name if courrier.fichier else "document_original.pdf"
            
            # Remplacer le fichier
            courrier.fichier.save(filename, ContentFile(pdf_signed_stream.read()), save=False)
            
            # Ajouter une note dans le champ notes pour tracer la signature
            timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
            signature_note = f"\n[{timestamp}] Document signé électroniquement par {user.get_full_name() or user.username}"
            courrier.notes = (courrier.notes or "") + signature_note
            courrier.save()
            
            # Log d'audit
            try:
                ActionLog.log_action(
                    action_type='document_signe',
                    utilisateur=user,
                    description=f"{user.get_full_name() or user.username} a signé électroniquement le courrier {courrier.numero_registre}",
                    courrier=courrier,
                    request=request,
                )
            except Exception as e:
                print(f"[signer] ActionLog error: {e}")
            
        except FileNotFoundError as e:
            return Response(
                {'detail': f'Fichier introuvable : {str(e)}'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            print(f"[signer] Erreur lors de l'application de la signature: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f'Erreur lors de l\'application de la signature : {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Marquer l'affectation comme signée
        affectation.signer(commentaire)
        
        return Response(
            AffectationSerializer(affectation, context={'request': request}).data
        )

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        return self._action_traitement(request, pk, 'rejeter', 'motif')

    @action(detail=True, methods=['post'])
    def renvoyer(self, request, pk=None):
        affectation = self.get_object()
        commentaire = request.data.get('commentaire', '')

        if not affectation.peut_etre_traitee():
            return Response(
                {'detail': "Ce n'est pas encore votre tour (circuit séquentiel)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        affectation.renvoyer(commentaire)

        destinataire_nom = affectation.destinataire.get_full_name() or affectation.destinataire.username

        # Log d'audit (non bloquant)
        try:
            ActionLog.log_action(
                action_type='affectation_renvoye',
                utilisateur=request.user,
                description=(
                    f"{destinataire_nom} a renvoyé le courrier "
                    f"{affectation.courrier.numero_registre} — à réaffecter"
                    + (f" : {commentaire}" if commentaire else "")
                ),
                courrier=affectation.courrier,
                request=request,
            )
        except Exception as e:
            print(f"[renvoyer] ActionLog error: {e}")

        # Alertes urgentes pour RH + DG (non bloquant, bloc séparé)
        try:
            from users.models import Notification, User as UserModel
            rh_dg = UserModel.objects.filter(role__in=['rh', 'dg', 'admin'], is_active=True)
            for u in rh_dg:
                Notification.objects.create(
                    utilisateur=u,
                    type='courrier_renvoye',
                    titre=f'Courrier renvoyé — à réaffecter : {affectation.courrier.numero_registre}',
                    message=(
                        f'{destinataire_nom} a renvoyé le courrier « {affectation.courrier.objet} ».'
                        + (f' Motif : {commentaire}' if commentaire else '')
                        + ' Ce courrier doit être réaffecté.'
                    ),
                    courrier_id=affectation.courrier.id,
                    urgente=True,
                )
        except Exception as e:
            print(f"[renvoyer] Notification error: {e}")

        return Response(
            AffectationSerializer(affectation, context={'request': request}).data
        )
