import mimetypes
import json

from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
# Create your views here.
from rest_framework import viewsets, status
from rest_framework import filters as rest_filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import DocumentFilter
from .models import Document, DocumentVersion, DocumentShare, ShareRequest, Courrier, PartageLog, Categorie
from .serializer import (
    DocumentSerializer, 
    DocumentShareSerializer, 
    UserSimpleSerializer, 
    ShareRequestSerializer,
    CourrierSerializer,
    CourrierCreateSerializer,
    CourrierUpdateSerializer,
    PartageLogSerializer,
    PartageLogCreateSerializer,
    CategorieSerializer
)
from users.models import User
from users.permissions import IsRHOrAdmin


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)  # Support pour upload et JSON
    permission_classes = [IsAuthenticated]

    # Ajout des systèmes de filtrage et recherche
    filterset_class = DocumentFilter  # On utilise notre filtre personnalisé
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter, rest_filters.OrderingFilter]

    # Champs sur lesquels on peut faire une recherche textuelle
    search_fields = ['title']

    # Champs pour le tri (ex: ?ordering=-created_at)
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']  # Tri par défaut (du plus récent au plus ancien)

    # Cette méthode va créer l'URL : /api/document/upload/
    @action(detail=False, methods=['post'])
    def upload(self, request):
        # Créer une copie mutable des données pour retirer 'tags' avant validation
        data = request.data.copy()
        
        # Sauvegarder les tags à part (ils seront traités dans perform_create)
        tags_data = data.pop('tags', None)
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            # Remettre les tags dans request.data pour perform_create
            if tags_data:
                request.data['tags'] = tags_data
            
            # On appelle perform_create manuellement ou on gère la sauvegarde ici
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



    def perform_create(self, serializer):
        # 1. Récupérer le fichier uploadé pour obtenir sa taille
        uploaded_file = self.request.FILES.get('file')
        file_size = uploaded_file.size if uploaded_file else 0
        
        # 2. Extraire les tags depuis les données de la requête
        tags_data = self.request.data.get('tags')
        tag_ids = []
        if tags_data:
            try:
                # Si c'est une chaîne JSON, la parser
                if isinstance(tags_data, str):
                    tag_ids = json.loads(tags_data)
                # Sinon, c'est déjà une liste
                elif isinstance(tags_data, list):
                    tag_ids = tags_data
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Erreur lors du parsing des tags: {e}")
                pass
        
        # 3. Sauvegarder le document avec owner et file_size
        # Les tags seront gérés après la création car c'est une relation ManyToMany
        document = serializer.save(owner=self.request.user, file_size=file_size)

        # 4. Ajouter les tags au document (relation ManyToMany)
        if tag_ids:
            try:
                document.tags.set(tag_ids)
            except Exception as e:
                print(f"Erreur lors de l'ajout des tags: {e}")

        # 5. Crée automatiquement la version 1 dans DocumentVersion
        DocumentVersion.objects.create(
            document=document,
            file=document.file,
            version_number=1,
            updated_by=self.request.user
        )

    def get_queryset(self):
        """
        Retourne tous les documents.
        Le champ 'has_access' dans le serializer indique si l'utilisateur y a accès.
        """
        return Document.objects.all()


    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        # 1. Récupérer l'objet (get_object vérifie aussi les permissions de l'user)
        document = self.get_object()

        # 2. Ouvrir le fichier physiquement
        file_handle = document.file.open()

        # 3. Détecter le type de contenu (PDF, Image, etc.)
        content_type, _ = mimetypes.guess_type(document.file.name)

        # 4. Renvoyer le fichier
        response = FileResponse(file_handle, content_type=content_type)

        # 5. Forcer le téléchargement avec le nom d'origine du fichier
        response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'

        return response

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        # 1. Récupérer le document original
        original_doc = self.get_object()

        # 2. Créer une copie de l'objet en mémoire
        new_doc = original_doc
        new_doc.pk = None  # On retire l'ID pour que Django crée une nouvelle ligne

        # 3. Modifier le titre pour indiquer que c'est une copie
        new_doc.title = f"{original_doc.title} (Copie)"

        # 4. Dupliquer le fichier physique
        # C'est crucial : sinon les deux documents pointent vers le même fichier
        original_file = original_doc.file
        new_file_name = f"copy_{original_file.name.split('/')[-1]}"
        new_doc.file.save(new_file_name, ContentFile(original_file.read()), save=False)

        # 5. Sauvegarder en base de données
        new_doc.save()

        # 6. Créer la version 1 pour ce nouveau document
        DocumentVersion.objects.create(
            document=new_doc,
            file=new_doc.file,
            version_number=1,
            updated_by=self.request.user
        )

        serializer = self.get_serializer(new_doc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='advanced-search')
    def search(self, request):
        """
        Action personnalisée pour la recherche avancée.
        URL : GET /api/documents/advanced-search/
        """
        # 1. On récupère le queryset de base (filtré par utilisateur via get_queryset)
        queryset = self.get_queryset()

        # 2. On applique les filtres de la classe DocumentFilter
        filtered_queryset = self.filter_queryset(queryset)

        # 3. Gestion de la pagination (important pour les gros volumes de données)
        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # 4. Si pas de pagination, on renvoie tout
        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """
        Basculer le statut favori d'un document.
        URL : POST /api/document/{id}/toggle_favorite/
        """
        document = self.get_object()
        document.is_favorite = not document.is_favorite
        document.save()
        
        serializer = self.get_serializer(document)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """
        Partager un document avec un ou plusieurs utilisateurs.
        URL : POST /api/documents/{id}/share/
        Body: {
            "user_ids": [1, 2, 3],
            "permission": "view" ou "edit"
        }
        """
        document = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut partager ce document"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_ids = request.data.get('user_ids', [])
        permission = request.data.get('permission', 'view')
        
        if not user_ids:
            return Response(
                {"error": "Veuillez spécifier au moins un utilisateur"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mettre à jour la visibilité si nécessaire
        if document.visibility == 'private':
            document.visibility = 'shared'
            document.save()
        
        # Créer les partages
        created_shares = []
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                if user == request.user:
                    continue  # Ne pas partager avec soi-même
                
                share, created = DocumentShare.objects.get_or_create(
                    document=document,
                    shared_with=user,
                    defaults={
                        'shared_by': request.user,
                        'permission': permission
                    }
                )
                
                if not created:
                    # Mettre à jour la permission si le partage existe déjà
                    share.permission = permission
                    share.save()
                
                created_shares.append(share)
            except User.DoesNotExist:
                pass
        
        serializer = DocumentShareSerializer(created_shares, many=True)
        return Response({
            "message": f"Document partagé avec {len(created_shares)} utilisateur(s)",
            "shares": serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def unshare(self, request, pk=None):
        """
        Retirer le partage d'un document pour un utilisateur.
        URL : POST /api/documents/{id}/unshare/
        Body: {"user_id": 1}
        """
        document = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut retirer un partage"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {"error": "Veuillez spécifier un utilisateur"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted = DocumentShare.objects.filter(
            document=document,
            shared_with_id=user_id
        ).delete()
        
        # Si plus aucun partage, repasser en privé
        if document.shares.count() == 0 and document.visibility == 'shared':
            document.visibility = 'private'
            document.save()
        
        return Response({
            "message": "Partage retiré avec succès"
        })

    @action(detail=True, methods=['patch'])
    def update_visibility(self, request, pk=None):
        """
        Changer la visibilité d'un document.
        URL : PATCH /api/documents/{id}/update_visibility/
        Body: {"visibility": "private" | "shared" | "public"}
        """
        document = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut modifier la visibilité"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        visibility = request.data.get('visibility')
        if visibility not in ['private', 'shared', 'public']:
            return Response(
                {"error": "Visibilité invalide"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si on passe en privé, supprimer tous les partages
        if visibility == 'private':
            document.shares.all().delete()
        
        document.visibility = visibility
        document.save()
        
        serializer = self.get_serializer(document)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def shared_with_me(self, request):
        """
        Lister uniquement les documents partagés avec moi.
        URL : GET /api/documents/shared_with_me/
        """
        documents = Document.objects.filter(
            shares__shared_with=request.user
        ).distinct()
        
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available_users(self, request):
        """
        Lister les utilisateurs disponibles pour le partage.
        URL : GET /api/documents/available_users/
        """
        # Tous les utilisateurs sauf l'utilisateur courant
        users = User.objects.exclude(id=request.user.id)
        serializer = UserSimpleSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def move_to_folder(self, request, pk=None):
        """
        Déplacer un document vers un dossier.
        URL : POST /api/documents/{id}/move_to_folder/
        Body: {"folder_id": 123} ou {"folder_id": null} pour déplacer à la racine
        """
        document = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut déplacer ce document"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        folder_id = request.data.get('folder_id')
        
        # Si folder_id est null, déplacer à la racine
        if folder_id is None:
            document.folder = None
            document.save()
            return Response({
                "message": "Document déplacé à la racine",
                "document": DocumentSerializer(document, context={'request': request}).data
            })
        
        # Vérifier que le dossier existe
        from folders.models import Folder
        try:
            folder = Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist:
            return Response(
                {"error": "Le dossier de destination n'existe pas"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier que l'utilisateur a accès au dossier de destination
        if folder.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Vous n'avez pas accès à ce dossier"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        document.folder = folder
        document.save()
        
        return Response({
            "message": f"Document déplacé vers {folder.name}",
            "document": DocumentSerializer(document, context={'request': request}).data
        })


class DocumentShareViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les partages de documents"""
    queryset = DocumentShare.objects.all()
    serializer_class = DocumentShareSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Retourne les partages selon l'utilisateur"""
        user = self.request.user
        
        # Si admin, voir tous les partages
        if user.role == 'admin':
            return DocumentShare.objects.all()
        
        # Sinon, voir uniquement:
        # - Les partages que j'ai créés (shared_by)
        # - Les partages dont je suis bénéficiaire (shared_with)
        # - Les partages des documents dont je suis propriétaire
        return DocumentShare.objects.filter(
            Q(shared_by=user) | 
            Q(shared_with=user) |
            Q(document__owner=user)
        ).distinct()
    
    def perform_create(self, serializer):
        """Créer un partage et définir shared_by automatiquement"""
        serializer.save(shared_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_shares(self, request):
        """Documents que j'ai partagés avec d'autres"""
        shares = DocumentShare.objects.filter(shared_by=request.user)
        serializer = self.get_serializer(shares, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def shared_with_me(self, request):
        """Documents partagés avec moi"""
        shares = DocumentShare.objects.filter(shared_with=request.user)
        serializer = self.get_serializer(shares, many=True)
        return Response(serializer.data)


class ShareRequestViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les demandes d'accès aux documents"""
    queryset = ShareRequest.objects.all()
    serializer_class = ShareRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Retourne les demandes selon l'utilisateur"""
        user = self.request.user
        
        # Si admin, voir toutes les demandes
        if user.role == 'admin':
            return ShareRequest.objects.all()
        
        # Sinon, voir uniquement:
        # - Les demandes que j'ai faites (requested_by)
        # - Les demandes pour mes documents (document.owner)
        return ShareRequest.objects.filter(
            Q(requested_by=user) | 
            Q(document__owner=user)
        ).distinct()
    
    def perform_create(self, serializer):
        """Créer une demande d'accès ou réactiver une demande rejetée"""
        document = serializer.validated_data['document']
        
        # Vérifier que l'utilisateur n'a pas déjà accès
        if document.owner == self.request.user:
            raise serializers.ValidationError("Vous êtes déjà propriétaire de ce document")
        
        if document.visibility == 'public':
            raise serializers.ValidationError("Ce document est public, aucune demande nécessaire")
        
        if document.shares.filter(shared_with=self.request.user).exists():
            raise serializers.ValidationError("Vous avez déjà accès à ce document")
        
        # Vérifier s'il existe déjà une demande pour ce document
        existing_request = ShareRequest.objects.filter(
            document=document,
            requested_by=self.request.user
        ).first()
        
        if existing_request:
            # Si demande en attente, bloquer
            if existing_request.status == 'pending':
                raise serializers.ValidationError("Vous avez déjà une demande en attente pour ce document")
            
            # Si demande rejetée, vérifier le nombre de tentatives
            if existing_request.status == 'rejected':
                if existing_request.rejection_count >= 3:
                    raise serializers.ValidationError("Vous avez atteint le nombre maximum de tentatives (3) pour ce document")
                
                # Réactiver la demande
                existing_request.status = 'pending'
                existing_request.requested_permission = serializer.validated_data['requested_permission']
                existing_request.message = serializer.validated_data.get('message', '')
                existing_request.reviewed_at = None
                existing_request.reviewed_by = None
                existing_request.save()
                return
        
        # Créer une nouvelle demande
        serializer.save(requested_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Mes demandes d'accès"""
        requests = ShareRequest.objects.filter(requested_by=request.user)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_for_my_documents(self, request):
        """Demandes en attente pour mes documents"""
        pending_requests = ShareRequest.objects.filter(
            document__owner=request.user,
            status='pending'
        )
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approuver une demande d'accès"""
        share_request = self.get_object()
        
        # Vérifier que l'utilisateur est propriétaire du document ou admin
        if share_request.document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Vous n'avez pas la permission d'approuver cette demande"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que la demande est en attente
        if share_request.status != 'pending':
            return Response(
                {"error": "Cette demande a déjà été traitée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approuver la demande
        from django.utils import timezone
        share_request.status = 'approved'
        share_request.reviewed_by = request.user
        share_request.reviewed_at = timezone.now()
        share_request.save()
        
        # Créer le partage
        DocumentShare.objects.create(
            document=share_request.document,
            shared_with=share_request.requested_by,
            shared_by=request.user,
            permission=share_request.requested_permission
        )
        
        return Response({
            "message": "Demande approuvée et partage créé",
            "request": ShareRequestSerializer(share_request).data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejeter une demande d'accès"""
        share_request = self.get_object()
        
        # Vérifier que l'utilisateur est propriétaire du document ou admin
        if share_request.document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Vous n'avez pas la permission de rejeter cette demande"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que la demande est en attente
        if share_request.status != 'pending':
            return Response(
                {"error": "Cette demande a déjà été traitée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Rejeter la demande
        from django.utils import timezone
        share_request.status = 'rejected'
        share_request.reviewed_by = request.user
        share_request.reviewed_at = timezone.now()
        share_request.rejection_count += 1
        share_request.save()
        
        return Response({
            "message": "Demande rejetée",
            "request": ShareRequestSerializer(share_request).data
        })


# ============================================================================
# VIEWSET POUR LE REGISTRE DE COURRIER
# ============================================================================

class CourrierFilter(filters.FilterSet):
    """
    Filtre personnalisé pour la recherche de courriers.
    Permet de filtrer par date, type, statut, service et recherche globale.
    """
    # Filtres de date
    date_debut = filters.DateFilter(field_name="date_reception", lookup_expr='gte')
    date_fin = filters.DateFilter(field_name="date_reception", lookup_expr='lte')
    
    # Recherche globale (sur plusieurs champs)
    search = filters.CharFilter(method='filter_search')
    
    def filter_search(self, queryset, name, value):
        """
        Recherche dans plusieurs champs simultanément.
        Cherche dans : numéro de registre, objet, expéditeur, destinataire, référence
        """
        return queryset.filter(
            Q(numero_registre__icontains=value) |
            Q(objet__icontains=value) |
            Q(expediteur__icontains=value) |
            Q(destinataire__icontains=value) |
            Q(reference__icontains=value)
        )
    
    class Meta:
        model = Courrier
        fields = {
            'type_courrier': ['exact'],
            'service_concerne': ['exact'],
            'statut': ['exact'],
        }


class CourrierViewSet(viewsets.ModelViewSet):
    """
    ViewSet complet pour gérer le registre de courrier RH.
    
    Fonctionnalités :
    - CRUD complet des courriers
    - Filtrage et recherche avancée
    - Export Excel du registre
    - Statistiques
    - Changement de statut
    
    Permissions : Accessible uniquement par les utilisateurs RH et Admin
    """
    queryset = Courrier.objects.all()
    serializer_class = CourrierSerializer
    permission_classes = [IsAuthenticated, IsRHOrAdmin]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_class = CourrierFilter
    search_fields = ['numero_registre', 'objet', 'expediteur', 'destinataire', 'reference']
    ordering_fields = ['created_at', 'date_reception', 'date_envoi', 'numero_registre', 'statut']
    ordering = ['-created_at']  # Par défaut, les plus récents en premier
    
    def get_serializer_class(self):
        """
        Retourne le serializer approprié selon l'action.
        - Création : CourrierCreateSerializer (simplifié)
        - Mise à jour partielle : CourrierUpdateSerializer
        - Autres : CourrierSerializer (complet)
        """
        if self.action == 'create':
            return CourrierCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CourrierUpdateSerializer
        return CourrierSerializer
    
    def perform_create(self, serializer):
        """
        Enregistrer le courrier et assigner automatiquement l'utilisateur connecté.
        Calculer aussi la taille du fichier uploadé.
        """
        courrier = serializer.save(enregistre_par=self.request.user)
        
        # Déterminer la taille du fichier
        if courrier.fichier:
            courrier.file_size = courrier.fichier.size
            courrier.save()
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Action personnalisée pour uploader un courrier avec son fichier.
        URL : POST /api/courriers/upload/
        """
        serializer = CourrierCreateSerializer(data=request.data)
        if serializer.is_valid():
            courrier = serializer.save(enregistre_par=request.user)
            
            # Déterminer la taille du fichier
            if courrier.fichier:
                courrier.file_size = courrier.fichier.size
                # Déterminer le type de fichier
                file_extension = courrier.fichier.name.split('.')[-1].lower()
                if file_extension in ['pdf']:
                    courrier.file_type = 'pdf'
                elif file_extension in ['jpg', 'jpeg', 'png', 'gif']:
                    courrier.file_type = 'image'
                else:
                    courrier.file_type = file_extension
                courrier.save()
            
            return Response(
                CourrierSerializer(courrier).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """
        Obtenir des statistiques complètes sur les courriers.
        URL : GET /api/courriers/statistiques/
        
        Retourne :
        - Total de courriers
        - Nombre de courriers entrants/sortants
        - Répartition par statut et service
        - Courriers urgents
        - Statistiques de versions
        - Tendances mensuelles (6 derniers mois)
        - Statistiques de partage
        """
        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta
        import calendar
        
        queryset = self.get_queryset()
        
        # Statistiques générales
        stats = {
            'total': queryset.count(),
            'entrants': queryset.filter(type_courrier='entrant').count(),
            'sortants': queryset.filter(type_courrier='sortant').count(),
            'urgents': queryset.filter(urgent=True).count(),
        }
        
        # Répartition par statut
        par_statut = {}
        for statut_key, statut_label in Courrier.STATUS_CHOICES:
            count = queryset.filter(statut=statut_key).count()
            par_statut[statut_key] = {
                'label': statut_label,
                'count': count
            }
        stats['par_statut'] = par_statut
        
        # Répartition par service (seulement ceux qui ont des courriers)
        par_service = {}
        for service_key, service_label in Courrier.SERVICE_CHOICES:
            count = queryset.filter(service_concerne=service_key).count()
            if count > 0:
                par_service[service_key] = {
                    'label': service_label,
                    'count': count
                }
        stats['par_service'] = par_service
        
        # Statistiques de versions
        courriers_avec_versions = queryset.filter(
            Q(courrier_parent__isnull=False) | Q(versions__isnull=False)
        ).distinct().count()
        stats['courriers_avec_versions'] = courriers_avec_versions
        stats['total_versions'] = queryset.filter(courrier_parent__isnull=False).count()
        
        # Tendances mensuelles (6 derniers mois)
        now = timezone.now()
        tendances = []
        for i in range(5, -1, -1):
            # Calculer le premier et dernier jour du mois
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            # Premier jour du mois
            start_date = timezone.datetime(target_year, target_month, 1, tzinfo=now.tzinfo)
            # Dernier jour du mois
            last_day = calendar.monthrange(target_year, target_month)[1]
            end_date = timezone.datetime(target_year, target_month, last_day, 23, 59, 59, tzinfo=now.tzinfo)
            
            # Compter les courriers du mois selon leur date réelle (réception/envoi)
            # Pour les entrants: utiliser date_reception, pour les sortants: date_envoi
            count_entrants = queryset.filter(
                date_reception__gte=start_date,
                date_reception__lte=end_date,
                type_courrier='entrant'
            ).count()
            count_sortants = queryset.filter(
                date_envoi__gte=start_date,
                date_envoi__lte=end_date,
                type_courrier='sortant'
            ).count()
            count_total = count_entrants + count_sortants
            
            # Nom du mois en français
            mois_noms = ['', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
            
            tendances.append({
                'mois': f"{mois_noms[target_month]} {target_year}",
                'total': count_total,
                'entrants': count_entrants,
                'sortants': count_sortants
            })
        
        stats['tendances_mensuelles'] = tendances
        
        # Statistiques de partage (si disponibles)
        try:
            from .models import PartageLog
            stats['partages_total'] = PartageLog.objects.filter(courrier__isnull=False).count()
            stats['partages_email'] = PartageLog.objects.filter(type_partage='email').count()
            stats['partages_whatsapp'] = PartageLog.objects.filter(type_partage='whatsapp').count()
            
            # Partages cette semaine
            semaine_derniere = now - timedelta(days=7)
            stats['partages_cette_semaine'] = PartageLog.objects.filter(
                courrier__isnull=False,
                created_at__gte=semaine_derniere
            ).count()
        except:
            pass
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """
        Exporter le registre de courrier au format Excel.
        URL : GET /api/courriers/export_excel/
        
        Génère un fichier Excel avec toutes les informations des courriers filtrés.
        Le nom du fichier contient la date et l'heure d'export.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from django.http import HttpResponse
        from datetime import datetime
        
        # Appliquer les filtres de la requête
        queryset = self.filter_queryset(self.get_queryset())
        
        # Créer le workbook Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Registre de Courrier"
        
        # Styles pour l'en-tête
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        # Style pour les bordures
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Définir les en-têtes des colonnes
        headers = [
            "N° Registre",
            "Type",
            "Date Réception",
            "Date Envoi",
            "Expéditeur",
            "Destinataire",
            "Objet",
            "Référence",
            "Service Concerné",
            "Statut",
            "Notes",
            "Enregistré par",
            "Date d'enregistrement"
        ]
        
        # Écrire les en-têtes
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Écrire les données
        for row_num, courrier in enumerate(queryset, 2):
            # Colonne 1 : Numéro de registre
            ws.cell(row=row_num, column=1, value=courrier.numero_registre).border = thin_border
            
            # Colonne 2 : Type
            ws.cell(row=row_num, column=2, value=courrier.get_type_courrier_display()).border = thin_border
            
            # Colonne 3 : Date de réception
            date_reception = courrier.date_reception.strftime('%d/%m/%Y') if courrier.date_reception else ''
            ws.cell(row=row_num, column=3, value=date_reception).border = thin_border
            
            # Colonne 4 : Date d'envoi
            date_envoi = courrier.date_envoi.strftime('%d/%m/%Y') if courrier.date_envoi else ''
            ws.cell(row=row_num, column=4, value=date_envoi).border = thin_border
            
            # Colonne 5 : Expéditeur
            ws.cell(row=row_num, column=5, value=courrier.expediteur).border = thin_border
            
            # Colonne 6 : Destinataire
            ws.cell(row=row_num, column=6, value=courrier.destinataire).border = thin_border
            
            # Colonne 7 : Objet
            ws.cell(row=row_num, column=7, value=courrier.objet).border = thin_border
            
            # Colonne 8 : Référence
            ws.cell(row=row_num, column=8, value=courrier.reference).border = thin_border
            
            # Colonne 9 : Service concerné
            service = courrier.get_service_concerne_display() if courrier.service_concerne else ''
            ws.cell(row=row_num, column=9, value=service).border = thin_border
            
            # Colonne 10 : Statut
            ws.cell(row=row_num, column=10, value=courrier.get_statut_display()).border = thin_border
            
            # Colonne 11 : Notes
            ws.cell(row=row_num, column=11, value=courrier.notes).border = thin_border
            
            # Colonne 12 : Enregistré par
            enregistre_par = courrier.enregistre_par.username if courrier.enregistre_par else ''
            ws.cell(row=row_num, column=12, value=enregistre_par).border = thin_border
            
            # Colonne 13 : Date d'enregistrement
            created_at = courrier.created_at.strftime('%d/%m/%Y %H:%M')
            ws.cell(row=row_num, column=13, value=created_at).border = thin_border
        
        # Ajuster automatiquement la largeur des colonnes
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            # Limiter la largeur maximale à 50 caractères
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        
        # Figer la première ligne (en-têtes)
        ws.freeze_panes = 'A2'
        
        # Préparer la réponse HTTP avec le fichier Excel
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Nom du fichier avec date et heure
        filename = f"registre_courrier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Sauvegarder le workbook dans la réponse
        wb.save(response)
        return response
    
    @action(detail=True, methods=['patch'])
    def changer_statut(self, request, pk=None):
        """
        Changer le statut d'un courrier.
        URL : PATCH /api/courriers/{id}/changer_statut/
        Body : {"statut": "traite"} (ou "recu", "en_traitement", "archive")
        """
        courrier = self.get_object()
        nouveau_statut = request.data.get('statut')
        
        # Vérifier que le statut est valide
        statuts_valides = [choice[0] for choice in Courrier.STATUS_CHOICES]
        if nouveau_statut not in statuts_valides:
            return Response(
                {
                    "error": "Statut invalide",
                    "statuts_valides": dict(Courrier.STATUS_CHOICES)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mettre à jour le statut
        courrier.statut = nouveau_statut
        courrier.save()
        
        return Response({
            "message": f"Statut mis à jour : {courrier.get_statut_display()}",
            "courrier": CourrierSerializer(courrier).data
        })
    
    @action(detail=True, methods=['post'])
    def toggle_urgent(self, request, pk=None):
        """
        Marquer/Démarquer un courrier comme urgent.
        URL : POST /api/courriers/{id}/toggle_urgent/
        """
        courrier = self.get_object()
        
        # Basculer l'état urgent
        courrier.urgent = not courrier.urgent
        courrier.save()
        
        return Response({
            "message": f"Courrier {'marqué comme urgent' if courrier.urgent else 'retiré des urgents'}",
            "urgent": courrier.urgent,
            "courrier": CourrierSerializer(courrier).data
        })
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Télécharger le fichier scanné d'un courrier.
        URL : GET /api/courriers/{id}/download/
        """
        courrier = self.get_object()
        
        if not courrier.fichier:
            return Response(
                {"error": "Aucun fichier associé à ce courrier"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Préparer la réponse avec le fichier
        response = FileResponse(courrier.fichier.open('rb'), content_type='application/octet-stream')
        filename = f"{courrier.numero_registre}_{courrier.fichier.name.split('/')[-1]}"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @action(detail=True, methods=['post'])
    def creer_version(self, request, pk=None):
        """
        Créer une nouvelle version d'un courrier existant.
        URL : POST /api/courriers/{id}/creer_version/
        Body (multipart/form-data) : {
            "fichier": <file>,
            "notes": "Notes sur cette version (optionnel)"
        }
        """
        courrier = self.get_object()
        
        # Vérifier qu'un fichier est fourni
        if 'fichier' not in request.FILES:
            return Response(
                {"error": "Le fichier est obligatoire pour créer une nouvelle version"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fichier = request.FILES['fichier']
        notes = request.data.get('notes', '')
        
        try:
            # Créer la nouvelle version
            nouvelle_version = courrier.creer_nouvelle_version(
                fichier=fichier,
                notes=notes,
                enregistre_par=request.user
            )
            
            # Calculer la taille du fichier
            if nouvelle_version.fichier:
                nouvelle_version.file_size = nouvelle_version.fichier.size
                # Déterminer le type de fichier
                file_extension = nouvelle_version.fichier.name.split('.')[-1].lower()
                if file_extension in ['pdf']:
                    nouvelle_version.file_type = 'pdf'
                elif file_extension in ['jpg', 'jpeg', 'png', 'gif']:
                    nouvelle_version.file_type = 'image'
                else:
                    nouvelle_version.file_type = file_extension
                nouvelle_version.save()
            
            return Response({
                "message": f"Nouvelle version créée : {nouvelle_version.get_version_label()}",
                "version": CourrierSerializer(nouvelle_version).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"Erreur lors de la création de la version : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Récupérer toutes les versions d'un courrier.
        URL : GET /api/courriers/{id}/versions/
        
        Retourne toutes les versions du courrier (incluant lui-même et ses versions)
        """
        courrier = self.get_object()
        
        # Récupérer toutes les versions
        toutes_versions = courrier.get_toutes_versions()
        
        # Ajouter le courrier parent si ce n'est pas déjà une version
        if not courrier.courrier_parent:
            # Créer une liste avec le parent et ses versions
            versions_list = [courrier] + list(toutes_versions)
        else:
            # Si c'est une version, récupérer le parent et toutes les versions
            parent = courrier.courrier_parent
            versions_list = [parent] + list(parent.versions.all().order_by('version_number'))
        
        # Sérialiser toutes les versions
        serializer = CourrierSerializer(versions_list, many=True, context={'request': request})
        
        return Response({
            "nombre_versions": len(versions_list),
            "version_actuelle": courrier.get_version_actuelle().version_number if courrier.get_version_actuelle() else None,
            "versions": serializer.data
        })


# ============================================================================
# VIEWSET POUR LES CATÉGORIES DE COURRIER
# ============================================================================

class CategorieViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les catégories de courriers.
    Permet de lister, créer, modifier et supprimer des catégories.
    """
    queryset = Categorie.objects.all()
    serializer_class = CategorieSerializer
    permission_classes = [IsAuthenticated]
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter, rest_filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        """
        Récupère une catégorie existante par son nom ou en crée une nouvelle.
        URL : POST /api/categories/get_or_create/
        Body : { "name": "Devis" }
        """
        name = request.data.get('name', '').strip()
        
        if not name:
            return Response(
                {"error": "Le nom de la catégorie est obligatoire"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Chercher ou créer la catégorie
        categorie, created = Categorie.objects.get_or_create(
            name=name,
            defaults={'description': request.data.get('description', '')}
        )
        
        serializer = self.get_serializer(categorie)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        
        return Response(serializer.data, status=status_code)
