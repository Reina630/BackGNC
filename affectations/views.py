from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
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

    @action(detail=True, methods=['post'])
    def ajouter_affectations(self, request, pk=None):
        """
        Ajouter des affectations à un circuit existant.
        POST /api/affectations/circuits/{id}/ajouter_affectations/

        Body :
        {
            "affectations": [
                {
                    "service": <service_id>,
                    "destinataire": <user_id>,   (optionnel)
                    "action_requise": "informatif",
                    "niveau_urgence": "normal",
                    "etape_numero": 2,
                    "note_instruction": "...",
                    "date_echeance": "2026-05-01"
                }
            ]
        }
        """
        circuit = self.get_object()

        if circuit.statut in ('termine', 'annule'):
            return Response(
                {'detail': 'Impossible d\'ajouter des affectations à un circuit terminé ou annulé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        affectations_data = request.data.get('affectations', [])
        if not affectations_data:
            return Response(
                {'detail': 'La liste des affectations ne peut pas être vide.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from users.models import Notification, User as UserModel, Service

        courrier = circuit.courrier
        user = request.user
        created = []

        with transaction.atomic():
            for aff_data in affectations_data:
                service_id = aff_data.get('service')
                destinataire_id = aff_data.get('destinataire')

                if not service_id:
                    return Response(
                        {'detail': 'Chaque affectation doit avoir un service.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                try:
                    service = Service.objects.get(id=service_id)
                except Service.DoesNotExist:
                    return Response(
                        {'detail': f'Service {service_id} introuvable.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                create_kwargs = {
                    'action_requise': aff_data.get('action_requise', 'informatif'),
                    'niveau_urgence': aff_data.get('niveau_urgence', 'normal'),
                    'etape_numero': aff_data.get('etape_numero', 1),
                    'note_instruction': aff_data.get('note_instruction', ''),
                    'date_echeance': aff_data.get('date_echeance') or None,
                }

                if destinataire_id:
                    try:
                        destinataire = UserModel.objects.get(id=destinataire_id)
                    except UserModel.DoesNotExist:
                        return Response(
                            {'detail': f'Utilisateur {destinataire_id} introuvable.'},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    aff = Affectation.objects.create(
                        circuit=circuit,
                        courrier=courrier,
                        affecte_par=user,
                        destinataire=destinataire,
                        service=service,
                        **create_kwargs,
                    )
                    created.append(aff)
                    Notification.objects.create(
                        utilisateur=destinataire,
                        type='courrier_affecte',
                        titre=f'Nouveau courrier à traiter : {courrier.numero_registre}',
                        message=(
                            f'Le courrier « {courrier.objet} » vous a été affecté. '
                            f'Action requise : {aff.get_action_requise_display()}.'
                        ),
                        courrier_id=courrier.id,
                        urgente=True,
                    )
                else:
                    users_in_service = UserModel.objects.filter(service=service, is_active=True)
                    if not users_in_service.exists():
                        return Response(
                            {'detail': f'Aucun utilisateur actif trouvé pour le service {service.nom}.'},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    for user_dest in users_in_service:
                        aff = Affectation.objects.create(
                            circuit=circuit,
                            courrier=courrier,
                            affecte_par=user,
                            destinataire=user_dest,
                            service=service,
                            **create_kwargs,
                        )
                        created.append(aff)
                        Notification.objects.create(
                            utilisateur=user_dest,
                            type='courrier_affecte',
                            titre=f'Nouveau courrier à traiter : {courrier.numero_registre}',
                            message=(
                                f'Le courrier « {courrier.objet} » a été affecté à votre service '
                                f'({service.nom}). Action requise : {aff.get_action_requise_display()}.'
                            ),
                            courrier_id=courrier.id,
                            urgente=True,
                        )

            # Log d'audit
            try:
                ActionLog.log_action(
                    action_type='affectation_courrier',
                    utilisateur=user,
                    description=(
                        f"{user.get_full_name() or user.username} a ajouté {len(created)} affectation(s) "
                        f"au circuit du courrier {courrier.numero_registre}"
                    ),
                    courrier=courrier,
                    request=request,
                )
            except Exception as e:
                print(f"[ajouter_affectations] ActionLog error: {e}")

        return Response(
            CircuitSerializer(circuit, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


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

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def soumettre_reponse(self, request, pk=None):
        """
        Soumettre une réponse à un courrier depuis une affectation 'a_repondre'.
        Crée un courrier sortant et, si soumettre=true, valide l'affectation et
        notifie RH/DG/admin.

        POST /api/affectations/affectations/{id}/soumettre_reponse/
        Body (multipart) :
          - objet            : str (requis)
          - destinataire     : str (requis)
          - date_envoi       : date YYYY-MM-DD (requis si soumettre=true)
          - mode_envoi       : str (optionnel, défaut 'courrier')
          - contenu_lettre   : str (optionnel)
          - categorie        : int pk (optionnel)
          - fichier          : File (requis)
          - soumettre        : '1' | 'true' pour valider, sinon brouillon
        """
        affectation = self.get_object()
        user = request.user

        # Vérifier que c'est bien l'affectation de cet utilisateur
        if affectation.destinataire != user:
            return Response(
                {'detail': "Vous n'êtes pas le destinataire de cette affectation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if affectation.action_requise != 'a_repondre':
            return Response(
                {'detail': "Cette affectation ne nécessite pas de réponse."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data
        fichier = request.FILES.get('fichier')
        objet = data.get('objet', '').strip()
        destinataire = data.get('destinataire', '').strip()
        date_envoi = data.get('date_envoi', '').strip()
        mode_envoi = data.get('mode_envoi', 'courrier')
        contenu_lettre = data.get('contenu_lettre', '')
        categorie_id = data.get('categorie')
        soumettre = str(data.get('soumettre', '')).lower() in ('1', 'true', 'yes')

        if not objet:
            return Response({'detail': "L'objet est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        if not destinataire:
            return Response({'detail': "Le destinataire est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        if not fichier:
            return Response({'detail': "Le fichier est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        if soumettre and not date_envoi:
            return Response({'detail': "La date d'envoi est obligatoire pour soumettre."}, status=status.HTTP_400_BAD_REQUEST)

        courrier_original = affectation.courrier

        try:
            with transaction.atomic():
                from documents.models import Courrier as CourrierModel, ActionLog as ActionLogModel
                from documents.serializer import CourrierSerializer

                create_kwargs = dict(
                    type_courrier='sortant',
                    objet=objet,
                    destinataire=destinataire,
                    mode_envoi=mode_envoi,
                    statut='en_traitement' if soumettre else 'brouillon',
                    fichier=fichier,
                    reponse_a=courrier_original,
                    enregistre_par=user,
                )
                if date_envoi:
                    from datetime import date as DateType
                    try:
                        create_kwargs['date_envoi'] = DateType.fromisoformat(date_envoi)
                    except (ValueError, TypeError):
                        create_kwargs['date_envoi'] = date_envoi
                if contenu_lettre:
                    create_kwargs['contenu_lettre'] = contenu_lettre
                if categorie_id:
                    create_kwargs['categorie_id'] = categorie_id

                courrier_reponse = CourrierModel.objects.create(**create_kwargs)
                if courrier_reponse.fichier:
                    courrier_reponse.file_size = courrier_reponse.fichier.size
                    courrier_reponse.save(update_fields=['file_size'])

                auteur = user.get_full_name() or user.username

                try:
                    ActionLogModel.log_action(
                        action_type='courrier_create',
                        utilisateur=user,
                        description=f"Courrier {courrier_reponse.numero_registre} créé en réponse à {courrier_original.numero_registre}",
                        courrier=courrier_reponse,
                        request=request,
                    )
                except Exception as e:
                    print(f"[soumettre_reponse] ActionLog create error: {e}")

                if soumettre:
                    if affectation.statut not in ('valide', 'rejete', 'renvoye', 'signe'):
                        affectation.valider(f"Réponse soumise : {courrier_reponse.numero_registre}")

                    try:
                        ActionLogModel.log_action(
                            action_type='affectation_repondre',
                            utilisateur=user,
                            description=(
                                f"{auteur} a soumis une réponse au courrier "
                                f"{courrier_original.numero_registre} — "
                                f"courrier sortant : {courrier_reponse.numero_registre}"
                            ),
                            courrier=courrier_original,
                            request=request,
                        )
                    except Exception as e:
                        print(f"[soumettre_reponse] ActionLog repondre error: {e}")

                    try:
                        from users.models import Notification, User as UserModel
                        rh_dg = UserModel.objects.filter(role__in=['rh', 'dg', 'admin'], is_active=True)
                        for u in rh_dg:
                            Notification.objects.create(
                                utilisateur=u,
                                type='courrier_repondu',
                                titre=f'Réponse soumise — à valider : {courrier_original.numero_registre}',
                                message=(
                                    f'{auteur} a soumis une réponse au courrier '
                                    f'« {courrier_original.objet} » '
                                    f'(réf. {courrier_original.numero_registre}). '
                                    f'Courrier sortant {courrier_reponse.numero_registre} en attente de validation.'
                                ),
                                courrier_id=courrier_original.id,
                                urgente=True,
                            )
                    except Exception as e:
                        print(f"[soumettre_reponse] Notification error: {e}")

            return Response(
                CourrierSerializer(courrier_reponse).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f"Erreur lors de la création : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
