import mimetypes
import json
import io
import os
from datetime import datetime

from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

# Imports pour la signature PDF
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from PIL import Image
# Create your views here.
from rest_framework import viewsets, status
from rest_framework import filters as rest_filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import DocumentFilter
from .models import (
    Document, DocumentVersion, DocumentShare, ShareRequest,
    Courrier, PartageLog, Categorie, AffectationCourrier, CommentaireCourrier,
    CourrierPieceJointe, ActionLog
)
from .serializer import (
    DocumentSerializer, 
    DocumentShareSerializer, 
    UserSimpleSerializer, 
    ShareRequestSerializer,
    CourrierSerializer,
    CourrierCreateSerializer,
    CourrierUpdateSerializer,
    
    CategorieSerializer,
    AffectationCourrierSerializer,
    CommentaireCourrierSerializer,
    ServiceSimpleSerializer
)
from users.models import User, Service
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
        Retourne tous les documents non supprimés.
        Le champ 'has_access' dans le serializer indique si l'utilisateur y a accès.
        """
        # Par défaut, on n'affiche que les documents non supprimés
        return Document.objects.filter(is_deleted=False)


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

    def destroy(self, request, *args, **kwargs):
        """
        Archiver (soft delete) un document au lieu de le supprimer complètement.
        URL : DELETE /api/documents/{id}/
        """
        document = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut archiver ce document"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Archiver le document (soft delete)
        document.soft_delete(request.user)
        
        return Response({
            "message": "Document archivé avec succès"
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def archives(self, request):
        """
        Récupérer tous les documents archivés (supprimés) accessibles par l'utilisateur.
        URL : GET /api/documents/archives/
        """
        # Récupérer tous les documents supprimés
        user = request.user
        
        if user.role == 'admin':
            # Les admins voient tous les documents archivés
            archived_docs = Document.objects.filter(is_deleted=True)
        else:
            # Les utilisateurs ne voient que leurs propres documents archivés
            archived_docs = Document.objects.filter(is_deleted=True, owner=user)
        
        # Appliquer les filtres de recherche si nécessaire
        search_query = request.query_params.get('search', None)
        if search_query:
            archived_docs = archived_docs.filter(title__icontains=search_query)
        
        # Trier par date de suppression (plus récent en premier)
        archived_docs = archived_docs.order_by('-deleted_at')
        
        serializer = self.get_serializer(archived_docs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restaurer un document archivé.
        URL : POST /api/documents/{id}/restore/
        """
        # Récupérer le document même s'il est supprimé
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier que le document est bien archivé
        if not document.is_deleted:
            return Response(
                {"error": "Ce document n'est pas archivé"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut restaurer ce document"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Restaurer le document
        document.restore()
        
        serializer = self.get_serializer(document)
        return Response({
            "message": "Document restauré avec succès",
            "document": serializer.data
        })

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Récupérer toutes les versions d'un document.
        URL : GET /api/documents/{id}/versions/
        """
        document = self.get_object()
        versions = document.versions.all().order_by('-version_number')
        
        # Créer une réponse simple avec les infos des versions
        versions_data = []
        for version in versions:
            versions_data.append({
                'id': version.id,
                'version_number': version.version_number,
                'created_at': version.created_at,
                'updated_by': version.updated_by.get_full_name() if version.updated_by else 'Inconnu',
                'file_url': request.build_absolute_uri(version.file.url) if version.file else None,
                'file_name': version.file.name.split('/')[-1] if version.file else None,
            })
        
        return Response(versions_data)

    @action(detail=True, methods=['post'])
    def restore_version(self, request, pk=None):
        """
        Restaurer une version spécifique d'un document.
        URL : POST /api/documents/{id}/restore_version/
        Body: {"version_id": 123}
        """
        document = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if document.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut restaurer une version"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        version_id = request.data.get('version_id')
        if not version_id:
            return Response(
                {"error": "version_id requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            version = DocumentVersion.objects.get(id=version_id, document=document)
        except DocumentVersion.DoesNotExist:
            return Response(
                {"error": "Version non trouvée"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Créer une nouvelle version avec le fichier de la version restaurée
        max_version = document.versions.aggregate(models.Max('version_number'))['version_number__max'] or 0
        new_version_number = max_version + 1
        
        # Sauvegarder l'ancien fichier avant de le remplacer
        old_file = document.file
        
        # Copier le fichier de la version à restaurer
        from django.core.files.base import ContentFile
        document.file.save(
            version.file.name.split('/')[-1],
            ContentFile(version.file.read()),
            save=False
        )
        document.save()
        
        # Créer une nouvelle version avec le nouveau fichier
        DocumentVersion.objects.create(
            document=document,
            file=document.file,
            version_number=new_version_number,
            updated_by=request.user
        )
        
        serializer = self.get_serializer(document)
        return Response({
            "message": f"Version {version.version_number} restaurée comme version {new_version_number}",
            "document": serializer.data
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
    
    # Filtre par service (accepte l'ID du service depuis la table Service)
    service = filters.NumberFilter(method='filter_by_service')
    
    # Recherche globale (sur plusieurs champs)
    search = filters.CharFilter(method='filter_search')
    
    def filter_by_service(self, queryset, name, value):
        """
        Filtrer par service en utilisant l'ID du service depuis la table Service.
        Convertit l'ID en code pour filtrer sur le champ service_concerne.
        """
        try:
            service = Service.objects.get(id=value)
            # Mapper le nom du service vers son code
            service_code = Courrier.get_service_code_from_name(service.nom)
            if service_code:
                return queryset.filter(service_concerne=service_code)
            return queryset
        except Service.DoesNotExist:
            return queryset.none()
    
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
            'urgent': ['exact'],
        }


class CourrierViewSet(viewsets.ModelViewSet):
    """
    ViewSet complet pour gérer le registre de courrier RH.
    
    Fonctionnalités :
    - CRUD complet des courriers (RH/Admin seulement)
    - Filtrage et recherche avancée (RH/Admin seulement)
    - Export Excel du registre (RH/Admin seulement)
    - Statistiques (RH/Admin seulement)
    - Mes affectations (Tous les utilisateurs authentifiés)
    - Services disponibles (Tous les utilisateurs authentifiés)
    - Affectation par service (RH/Admin seulement)
    
    Permissions variables selon l'action
    """
    queryset = Courrier.objects.all()
    serializer_class = CourrierSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_class = CourrierFilter
    search_fields = ['numero_registre', 'objet', 'expediteur', 'destinataire', 'reference']
    ordering_fields = ['created_at', 'date_reception', 'date_envoi', 'numero_registre', 'statut']
    ordering = ['-created_at']  # Par défaut, les plus récents en premier
    
    def get_permissions(self):
        """
        Permissions variables selon l'action :
        - Actions accessibles à tous les utilisateurs authentifiés : list, retrieve, mes_affectations, services_disponibles, mes_courriers
        - Autres actions : RH et Admin seulement
        """
        if self.action in ['list', 'retrieve', 'mes_affectations', 'services_disponibles', 'mes_courriers']:
            # Actions accessibles aux utilisateurs normaux
            permission_classes = [IsAuthenticated]
        else:
            # Actions réservées aux RH et Admin
            permission_classes = [IsAuthenticated, IsRHOrAdmin]
        
        return [permission() for permission in permission_classes]
    
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
    
    def get_queryset(self):
        """
        Retourne les courriers en filtrant les courriers supprimés par défaut.
        Filtre aussi selon le rôle de l'utilisateur :
        - RH/Admin : tous les courriers
        - Autres : courriers de leur service ou qui leur sont affectés
        L'action 'archives' et 'restore' peuvent accéder aux courriers supprimés.
        """
        user = self.request.user
        
        # Pour l'action archives et restore, on veut les courriers supprimés
        if self.action in ['archives', 'restore']:
            return Courrier.objects.filter(is_deleted=True)
        
        # Par défaut, on ne montre que les courriers non supprimés
        queryset = Courrier.objects.filter(is_deleted=False).select_related(
            'circuit_affectation'
        ).prefetch_related(
            'circuit_affectation__affectations_service',
            'circuit_affectation__affectations_service__service',
            'affectations',
            'affectations__utilisateur',
            'affectations__utilisateur__service',
            'circuits_v2',
            'circuits_v2__affectations',
            'circuits_v2__affectations__destinataire',
            'circuits_v2__affectations__service',
            'affectations_v2',
            'affectations_v2__destinataire',
            'affectations_v2__service',
        )
        
        # Filtrage selon le rôle pour list et retrieve
        if self.action in ['list', 'retrieve']:
            if user.role not in ['rh', 'admin']:
                # Utilisateurs normaux voient :
                # - Courriers de leur service (si service défini)
                # - Courriers qui leur sont affectés (ancien système)
                # - Courriers qui leur sont affectés (nouveau système v2)
                # - Courriers qu'ils ont créés
                from django.db.models import Q
                filters = Q(enregistre_par=user) | Q(affectations__utilisateur=user) | Q(affectations_v2__destinataire=user)
                if user.service:
                    filters |= Q(service_concerne=user.service)
                queryset = queryset.filter(filters).distinct()
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Enregistrer le courrier et assigner automatiquement l'utilisateur connecté.
        Calculer aussi la taille du fichier uploadé.
        Créer les pièces jointes supplémentaires si fournies.
        """
        courrier = serializer.save(enregistre_par=self.request.user)

        # Déterminer la taille du fichier principal
        if courrier.fichier:
            courrier.file_size = courrier.fichier.size
            courrier.save()

        # Traiter les pièces jointes multiples (fichiers[])
        fichiers_supplementaires = self.request.FILES.getlist('fichiers')
        for f in fichiers_supplementaires:
            ext = f.name.split('.')[-1].lower()
            if ext == 'pdf':
                ftype = 'pdf'
            elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                ftype = 'image'
            else:
                ftype = ext
            CourrierPieceJointe.objects.create(
                courrier=courrier,
                fichier=f,
                nom_fichier=f.name,
                file_type=ftype,
                file_size=f.size,
                uploaded_by=self.request.user,
            )

        ActionLog.log_action(
            action_type='courrier_create',
            utilisateur=self.request.user,
            description=f"Courrier {courrier.numero_registre} enregistré : {courrier.objet}",
            courrier=courrier,
            request=self.request,
        )

    def perform_update(self, serializer):
        """Logger la modification d'un courrier."""
        courrier = serializer.save()
        ActionLog.log_action(
            action_type='courrier_update',
            utilisateur=self.request.user,
            description=f"Courrier {courrier.numero_registre} modifié : {courrier.objet}",
            courrier=courrier,
            request=self.request,
        )

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
        - Total de courriers avec variation %
        - Nombre de courriers entrants/sortants
        - Répartition par statut et service
        - Courriers urgents avec détails
        - Flux de traitement (lifecycle)
        - Statistiques de versions
        - Tendances mensuelles (6 derniers mois)
        - Statistiques de partage
        - Charge de travail par service
        """
        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta
        import calendar
        
        queryset = self.get_queryset()
        now = timezone.now()
        
        # Période actuelle (30 derniers jours)
        periode_actuelle_debut = now - timedelta(days=30)
        periode_precedente_debut = now - timedelta(days=60)
        periode_precedente_fin = periode_actuelle_debut
        
        # Courriers période actuelle
        courriers_actuels = queryset.filter(created_at__gte=periode_actuelle_debut)
        total_actuel = courriers_actuels.count()
        
        # Courriers période précédente (pour comparaison)
        courriers_precedents = queryset.filter(
            created_at__gte=periode_precedente_debut,
            created_at__lt=periode_precedente_fin
        )
        total_precedent = courriers_precedents.count()
        
        # Calculer variations en %
        def calculer_variation(actuel, precedent):
            if precedent == 0:
                return 100 if actuel > 0 else 0
            return round(((actuel - precedent) / precedent) * 100, 1)
        
        # Statistiques générales avec variations
        stats = {
            'total': queryset.count(),
            'total_30j': total_actuel,
            'variation_total': calculer_variation(total_actuel, total_precedent),
            
            'entrants': queryset.filter(type_courrier='entrant').count(),
            'entrants_30j': courriers_actuels.filter(type_courrier='entrant').count(),
            'variation_entrants': calculer_variation(
                courriers_actuels.filter(type_courrier='entrant').count(),
                courriers_precedents.filter(type_courrier='entrant').count()
            ),
            
            'sortants': queryset.filter(type_courrier='sortant').count(),
            'sortants_30j': courriers_actuels.filter(type_courrier='sortant').count(),
            'variation_sortants': calculer_variation(
                courriers_actuels.filter(type_courrier='sortant').count(),
                courriers_precedents.filter(type_courrier='sortant').count()
            ),
            
            'urgents': queryset.filter(urgent=True).count(),
            'urgents_30j': courriers_actuels.filter(urgent=True).count(),
            'variation_urgents': calculer_variation(
                courriers_actuels.filter(urgent=True).count(),
                courriers_precedents.filter(urgent=True).count()
            ),
        }
        
        # Flux de traitement (Lifecycle Flow)
        # On dérive chaque étape depuis les affectations, pas depuis courrier.statut
        # car ce champ ne contient pas de valeur 'affecte'.
        from affectations.models import Affectation as AffectationV2

        # IDs de tous les courriers du queryset ayant ≥1 affectation active (non renvoyée/rejetée)
        ids_avec_affectation_v2 = set(
            AffectationV2.objects.filter(courrier__in=queryset)
            .exclude(statut__in=['renvoye', 'rejete'])
            .values_list('courrier_id', flat=True)
        )
        ids_avec_affectation_v1 = set(
            AffectationCourrier.objects.filter(courrier__in=queryset)
            .values_list('courrier_id', flat=True)
        )
        ids_avec_affectation = ids_avec_affectation_v2 | ids_avec_affectation_v1

        # "En traitement" = courriers avec ≥1 affectation en_traitement
        ids_en_traitement = set(
            AffectationV2.objects.filter(courrier__in=queryset, statut='en_traitement')
            .values_list('courrier_id', flat=True)
        ) | set(
            AffectationCourrier.objects.filter(courrier__in=queryset, statut='en_traitement')
            .values_list('courrier_id', flat=True)
        )

        nb_enregistres = queryset.exclude(statut='archive').count()
        nb_affectes    = len(ids_avec_affectation)
        nb_en_traitement = len(ids_en_traitement)
        nb_traites     = queryset.filter(statut='traite').count()
        nb_archives    = queryset.filter(statut='archive').count()

        lifecycle_flow = {
            'recu': {
                'label': 'Enregistrés',
                'count': nb_enregistres,
                'color': '#dc2626'
            },
            'affecte': {
                'label': 'Affectés',
                'count': nb_affectes,
                'color': '#f59e0b'
            },
            'en_traitement': {
                'label': 'En traitement',
                'count': nb_en_traitement,
                'color': '#3b82f6'
            },
            'traite': {
                'label': 'Validés',
                'count': nb_traites,
                'color': '#10b981'
            },
            'archive': {
                'label': 'Archivés',
                'count': nb_archives,
                'color': '#6b7280'
            }
        }
        stats['lifecycle_flow'] = lifecycle_flow
        
        # Répartition par statut
        par_statut = {}
        for statut_key, statut_label in Courrier.STATUS_CHOICES:
            count = queryset.filter(statut=statut_key).count()
            par_statut[statut_key] = {
                'label': statut_label,
                'count': count
            }
        stats['par_statut'] = par_statut
        
        # Répartition par service avec charge de travail
        par_service = {}
        total_courriers_services = queryset.exclude(service_concerne='').count()
        for service_key, service_label in Courrier.SERVICE_CHOICES:
            if service_key:  # Ignorer les valeurs vides
                count = queryset.filter(service_concerne=service_key).count()
                en_traitement = queryset.filter(
                    service_concerne=service_key,
                    statut__in=['recu', 'affecte', 'en_traitement']
                ).count()
                if count > 0:
                    pourcentage = round((count / total_courriers_services * 100), 1) if total_courriers_services > 0 else 0
                    par_service[service_key] = {
                        'label': service_label,
                        'count': count,
                        'en_traitement': en_traitement,
                        'pourcentage': pourcentage
                    }
        stats['par_service'] = par_service
        
        # Distribution par type (pour le graphique en camembert)
        distribution_types = [
            {
                'name': 'Entrants',
                'value': stats['entrants'],
                'percentage': round((stats['entrants'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0
            },
            {
                'name': 'Sortants',
                'value': stats['sortants'],
                'percentage': round((stats['sortants'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0
            },
        ]
        # Ajouter internes si > 0
        count_internes = queryset.filter(type_courrier='interne').count()
        if count_internes > 0:
            distribution_types.append({
                'name': 'Internes',
                'value': count_internes,
                'percentage': round((count_internes / stats['total'] * 100), 1) if stats['total'] > 0 else 0
            })
        stats['distribution_types'] = distribution_types
        
        # Courriers urgents avec détails complets
        courriers_urgents = queryset.filter(urgent=True).exclude(
            statut__in=['traite', 'archive']
        ).order_by('-created_at')[:5]
        
        urgents_details = []
        for courrier in courriers_urgents:
            # Calculer le temps écoulé
            temps_ecoule = now - courrier.created_at
            if temps_ecoule.days > 0:
                temps_str = f"{temps_ecoule.days}j"
            else:
                heures = temps_ecoule.seconds // 3600
                temps_str = f"{heures}h"
            
            urgents_details.append({
                'id': courrier.id,
                'numero_registre': courrier.numero_registre,
                'objet': courrier.objet[:100] if courrier.objet else 'Sans objet',
                'expediteur': courrier.expediteur if hasattr(courrier, 'expediteur') else '',
                'service': dict(Courrier.SERVICE_CHOICES).get(courrier.service_concerne, 'Non défini'),
                'service_key': courrier.service_concerne,
                'statut': courrier.get_statut_display(),
                'statut_key': courrier.statut,
                'temps_ecoule': temps_str,
                'created_at': courrier.created_at.isoformat()
            })
        stats['urgents_details'] = urgents_details
        
        # Statistiques de versions
        courriers_avec_versions = queryset.filter(
            Q(courrier_parent__isnull=False) | Q(versions__isnull=False)
        ).distinct().count()
        stats['courriers_avec_versions'] = courriers_avec_versions
        stats['total_versions'] = queryset.filter(courrier_parent__isnull=False).count()
        
        # Tendances mensuelles (6 derniers mois)
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
            
            # Compter les courriers du mois
            count_entrants = queryset.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                type_courrier='entrant'
            ).count()
            count_sortants = queryset.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                type_courrier='sortant'
            ).count()
            count_total = count_entrants + count_sortants
            
            # Nom du mois en français
            mois_noms = ['', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
            
            tendances.append({
                'mois': f"{mois_noms[target_month]} {target_year}",
                'count': count_total,
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
        
        # ========================================
        # Format adapté pour le nouveau design dashboard
        # ========================================
        
        # 1. KPIs (4 cards) - format design
        recus_aujourdhui = queryset.filter(created_at__date=now.date()).count()
        recus_hier = queryset.filter(created_at__date=(now - timedelta(days=1)).date()).count()
        en_attente = queryset.filter(statut__in=['recu', 'affecte', 'en_traitement']).count()
        en_attente_avant = courriers_precedents.filter(statut__in=['recu', 'affecte', 'en_traitement']).count()

        # Urgents = affectations v2 avec niveau_urgence critique ou élevé, non terminées
        # (même source que urgentItems, donc les deux chiffres seront cohérents)
        from affectations.models import Affectation as _AffV2
        nb_urgents = _AffV2.objects.filter(
            niveau_urgence__in=['critique', 'eleve']
        ).exclude(
            statut__in=['valide', 'signe', 'rejete', 'renvoye']
        ).values('courrier_id').distinct().count()

        stats['kpis'] = [
            {
                'label': 'Total courriers',
                'value': f"{total_actuel:,}".replace(',', ' '),
                'change': f"{'+' if stats['variation_total'] >= 0 else ''}{stats['variation_total']}%",
                'positive': stats['variation_total'] >= 0,
                'color': 'bg-sky-50/80 border-sky-100'
            },
            {
                'label': 'Reçus aujourd\'hui',
                'value': str(recus_aujourdhui),
                'change': f"+{round(((recus_aujourdhui - recus_hier) / recus_hier * 100) if recus_hier > 0 else 0)}%",
                'positive': True,
                'color': 'bg-sky-50/80 border-sky-100'
            },
            {
                'label': 'En attente',
                'value': str(en_attente),
                'change': f"{'+' if calculer_variation(en_attente, en_attente_avant) >= 0 else ''}{calculer_variation(en_attente, en_attente_avant)}%",
                'positive': calculer_variation(en_attente, en_attente_avant) <= 0,
                'color': 'bg-amber-50/80 border-amber-100'
            },
            {
                'label': 'Urgents',
                'value': str(nb_urgents),
                'change': 'Élevé' if nb_urgents > 10 else ('Moyen' if nb_urgents > 0 else 'Normal'),
                'positive': False,
                'color': 'bg-red-50/80 border-red-100'
            }
        ]
        
        # 2. Lifecycle - format array (design)
        stats['lifecycle'] = [
            {
                'label': lifecycle_flow['recu']['label'],
                'count': lifecycle_flow['recu']['count'],
                'color': lifecycle_flow['recu']['color']
            },
            {
                'label': lifecycle_flow['affecte']['label'],
                'count': lifecycle_flow['affecte']['count'],
                'color': '#38bdf8'  # sky-400
            },
            {
                'label': lifecycle_flow['en_traitement']['label'],
                'count': lifecycle_flow['en_traitement']['count'],
                'color': '#1d4ed8'  # blue-700
            },
            {
                'label': lifecycle_flow['traite']['label'],
                'count': lifecycle_flow['traite']['count'],
                'color': lifecycle_flow['traite']['color']
            },
            {
                'label': lifecycle_flow['archive']['label'],
                'count': lifecycle_flow['archive']['count'],
                'color': lifecycle_flow['archive']['color']
            }
        ]
        
        # 3. Distribution par type - format design avec percentages
        stats['distribution'] = []
        total_types = stats['total'] if stats['total'] > 0 else 1
        
        # Utiliser les catégories de courrier si disponibles
        try:
            from .models import CategorieCourrier
            categories = CategorieCourrier.objects.all()[:3]
            if categories.exists():
                colors = ['#800020', '#505f76', '#c3c6d6']
                for idx, cat in enumerate(categories):
                    count = queryset.filter(categorie=cat).count()
                    percent = round((count / total_types * 100), 0)
                    stats['distribution'].append({
                        'name': cat.nom,
                        'percent': int(percent),
                        'color': colors[idx] if idx < len(colors) else '#94a3b8'
                    })
            else:
                # Fallback: utiliser les types de courrier
                stats['distribution'] = [
                    {
                        'name': 'Entrants',
                        'percent': round((stats['entrants'] / total_types * 100), 0),
                        'color': '#800020'
                    },
                    {
                        'name': 'Sortants',
                        'percent': round((stats['sortants'] / total_types * 100), 0),
                        'color': '#505f76'
                    },
                    {
                        'name': 'Internes',
                        'percent': round((count_internes / total_types * 100), 0),
                        'color': '#c3c6d6'
                    }
                ]
        except:
            stats['distribution'] = [
                {
                    'name': 'Entrants',
                    'percent': round((stats['entrants'] / total_types * 100), 0),
                    'color': '#800020'
                },
                {
                    'name': 'Sortants',
                    'percent': round((stats['sortants'] / total_types * 100), 0),
                    'color': '#505f76'
                },
                {
                    'name': 'Internes',
                    'percent': round((count_internes / total_types * 100), 0),
                    'color': '#c3c6d6'
                }
            ]
        
        # 4. urgent Items - format design (basé sur affectations critiques)
        from affectations.models import Affectation
        
        # Combiner affectations de l'ancien et nouveau système
        # Ancien système : AffectationCourrier avec niveau_urgence='critique'
        affectations_critiques_old = AffectationCourrier.objects.filter(
            niveau_urgence='critique'
        ).exclude(
            statut__in=['valide', 'signe']  # Exclure les affectations déjà traitées/signées
        ).select_related('courrier', 'utilisateur').order_by('-date_affectation')
        
        # Nouveau système : Affectation v2 avec niveau_urgence='critique' ou 'eleve'
        affectations_critiques_v2 = Affectation.objects.filter(
            niveau_urgence__in=['critique', 'eleve']
        ).exclude(
            statut__in=['valide', 'signe']  # Exclure les affectations déjà traitées/signées
        ).select_related('courrier', 'destinataire', 'service').order_by('-date_affectation')
        
        stats['urgentItems'] = []
        
        # Ajouter affectations de l'ancien système
        for affectation in affectations_critiques_old:
            # Calculer le temps écoulé depuis l'affectation
            temps_ecoule = now - affectation.date_affectation
            if temps_ecoule.days > 0:
                temps_str = f"{temps_ecoule.days}j"
            else:
                heures = temps_ecoule.seconds // 3600
                temps_str = f"{heures}h"
            
            # Créer le subtitle avec le statut et l'utilisateur
            subtitle = f"Affecté à {affectation.utilisateur.get_full_name() or affectation.utilisateur.username} · {temps_str}"
            
            stats['urgentItems'].append({
                'id': affectation.courrier.id,
                'affectation_id': affectation.id,
                'title': affectation.courrier.objet[:60] if affectation.courrier.objet else 'Sans objet',
                'subtitle': subtitle,
                'department': dict(Courrier.SERVICE_CHOICES).get(affectation.courrier.service_concerne, 'Non défini'),
                'numero_registre': affectation.courrier.numero_registre,
                'statut_affectation': affectation.get_statut_display(),
                'niveau_urgence': affectation.get_niveau_urgence_display(),
                'status': 'critique'
            })
        
        # Ajouter affectations du nouveau système v2
        for affectation in affectations_critiques_v2:
            # Calculer le temps écoulé depuis l'affectation
            temps_ecoule = now - affectation.date_affectation
            if temps_ecoule.days > 0:
                temps_str = f"{temps_ecoule.days}j"
            else:
                heures = temps_ecoule.seconds // 3600
                temps_str = f"{heures}h"
            
            # Créer le subtitle avec le statut et l'utilisateur
            subtitle = f"Affecté à {affectation.destinataire.get_full_name() or affectation.destinataire.username} · {temps_str}"
            
            # Déterminer le service (utiliser affectation.service si disponible, sinon service du courrier)
            if affectation.service:
                department = affectation.service.nom
            else:
                department = dict(Courrier.SERVICE_CHOICES).get(affectation.courrier.service_concerne, 'Non défini')
            
            stats['urgentItems'].append({
                'id': affectation.courrier.id,
                'affectation_id': affectation.id,
                'title': affectation.courrier.objet[:60] if affectation.courrier.objet else 'Sans objet',
                'subtitle': subtitle,
                'department': department,
                'numero_registre': affectation.courrier.numero_registre,
                'statut_affectation': affectation.get_statut_display(),
                'niveau_urgence': affectation.get_niveau_urgence_display(),
                'status': 'critique' if affectation.niveau_urgence == 'critique' else 'urgent'
            })
        
        # Limiter à 10 items et trier par date décroissante
        stats['urgentItems'] = sorted(stats['urgentItems'], key=lambda x: x.get('affectation_id', 0), reverse=True)[:10]
        
        # 5. Recent Mails - format design
        courriers_recents = queryset.order_by('-created_at')[:3]
        stats['recentMails'] = []
        
        icon_map = {
            'entrant': 'Inbox',
            'sortant': 'Send',
            'interne': 'Mail'
        }
        
        icon_color_map = {
            'entrant': 'bg-blue-50 text-blue-600',
            'sortant': 'bg-emerald-50 text-emerald-600',
            'interne': 'bg-purple-50 text-purple-600'
        }
        
        status_map = {
            'recu': 'pending',
            'affecte': 'pending',
            'en_traitement': 'in_progress',
            'traite': 'completed',
            'archive': 'completed'
        }
        
        for courrier in courriers_recents:
            # Format date relative
            diff = now - courrier.created_at
            if diff.days == 0:
                received_str = courrier.created_at.strftime('%H:%M')
            elif diff.days == 1:
                received_str = "Hier, " + courrier.created_at.strftime('%H:%M')
            else:
                received_str = courrier.created_at.strftime('%d %b, %H:%M')
            
            # Déterminer si urgent
            mail_status = status_map.get(courrier.statut, 'pending')
            if courrier.urgent:
                mail_status = 'urgent'
                
            stats['recentMails'].append({
                'id': courrier.id,
                'subject': courrier.objet[:60] if courrier.objet else 'Sans objet',
                'sender': courrier.expediteur if courrier.type_courrier == 'entrant' else courrier.destinataire,
                'received': received_str,
                'department': courrier.categorie.name if courrier.categorie else courrier.get_type_courrier_display(),
                'status': mail_status,
                'icon': icon_map.get(courrier.type_courrier, 'Mail'),
                'iconColor': icon_color_map.get(courrier.type_courrier, 'bg-slate-50 text-slate-600')
            })
        
        # 6. Service Workload - format design
        # Combiner la charge de travail des courriers (service_concerne) et des affectations v2 (service)
        from collections import defaultdict
        
        # Charge basée sur service_concerne du courrier
        charge_par_service = defaultdict(lambda: {'count': 0, 'label': '', 'en_traitement': 0})
        
        for service_key, service_label in Courrier.SERVICE_CHOICES:
            if service_key:  # Ignorer les valeurs vides
                count = queryset.filter(service_concerne=service_key).count()
                en_traitement = queryset.filter(
                    service_concerne=service_key,
                    statut__in=['recu', 'affecte', 'en_traitement']
                ).count()
                if count > 0:
                    charge_par_service[service_key] = {
                        'count': count,
                        'label': service_label,
                        'en_traitement': en_traitement
                    }
        
        # Ajouter la charge basée sur les affectations v2 en cours
        from users.models import Service
        affectations_actives_v2 = Affectation.objects.exclude(
            statut__in=['valide', 'signe', 'rejete', 'renvoye']
        ).select_related('service')
        
        for affectation in affectations_actives_v2:
            if affectation.service:
                service_nom = affectation.service.nom
                # Ajouter à la charge du service
                if service_nom not in charge_par_service:
                    charge_par_service[service_nom] = {
                        'count': 0,
                        'label': service_nom,
                        'en_traitement': 0
                    }
                charge_par_service[service_nom]['count'] += 1
                charge_par_service[service_nom]['en_traitement'] += 1
        
        # Calculer les pourcentages
        total_courriers_services = sum(s['count'] for s in charge_par_service.values())
        
        stats['serviceWorkload'] = []
        colors = ['bg-[#800020]', 'bg-emerald-500', 'bg-amber-500', 'bg-slate-500']
        
        # Trier par count décroissant et prendre top 4
        services_sorted = sorted(
            [(key, data) for key, data in charge_par_service.items()],
            key=lambda x: x[1]['count'],
            reverse=True
        )[:4]
        
        for idx, (key, service_data) in enumerate(services_sorted):
            pourcentage = round((service_data['count'] / total_courriers_services * 100), 1) if total_courriers_services > 0 else 0
            stats['serviceWorkload'].append({
                'name': service_data['label'],
                'percent': int(pourcentage),
                'color': colors[idx] if idx < len(colors) else 'bg-slate-400'
            })
        
        # 7. Weekly Trend - 7 derniers jours
        stats['weeklyTrend'] = []
        jours_fr = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        
        for i in range(6, -1, -1):  # 7 jours en arrière
            date_jour = (now - timedelta(days=i)).date()
            count_jour = queryset.filter(created_at__date=date_jour).count()
            
            # Calculer le % relatif (max = 100%)
            jour_semaine_idx = date_jour.weekday()  # 0=Lundi, 6=Dimanche
            
            stats['weeklyTrend'].append({
                'day': jours_fr[jour_semaine_idx],
                'value': count_jour
            })
        
        # Normaliser les valeurs de weeklyTrend en pourcentages (0-100)
        max_val = max([t['value'] for t in stats['weeklyTrend']]) if stats['weeklyTrend'] else 1
        if max_val > 0:
            for trend in stats['weeklyTrend']:
                trend['value'] = round((trend['value'] / max_val) * 100)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'], url_path='search-courriers')
    def search_courriers(self, request):
        """
        Rechercher des courriers pour la liste déroulante.
        URL : GET /api/courriers/search-courriers/?q=texte&type=entrant
        
        Paramètres optionnels:
        - q : texte de recherche (numero_registre, objet, expediteur, destinataire)
        - type : filtrer par type de courrier (entrant, sortant, interne)
        - exclude : ID de courrier à exclure (utile pour éviter auto-référence)
        
        Retourne une liste simplifiée de courriers avec :
        - id, numero_registre, objet, type_courrier, type_courrier_display, date_principale
        
        Limité à 50 résultats max pour les performances.
        """
        from django.db.models import Q
        
        queryset = self.get_queryset()
        
        # Recherche par texte
        q = request.query_params.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(numero_registre__icontains=q) |
                Q(objet__icontains=q) |
                Q(expediteur__icontains=q) |
                Q(destinataire__icontains=q) |
                Q(reference__icontains=q) |
                Q(reference_structure__icontains=q)
            )
        
        # Filtrer par type
        type_courrier = request.query_params.get('type', '').strip()
        if type_courrier in ['entrant', 'sortant', 'interne']:
            queryset = queryset.filter(type_courrier=type_courrier)
        
        # Exclure un courrier spécifique (pour éviter auto-référence)
        exclude_id = request.query_params.get('exclude', '').strip()
        if exclude_id and exclude_id.isdigit():
            queryset = queryset.exclude(id=int(exclude_id))
        
        # Limiter à 50 résultats et trier par date décroissante
        courriers = queryset.order_by('-created_at')[:50]
        
        # Construire la réponse simplifiée
        results = []
        for courrier in courriers:
            results.append({
                'id': courrier.id,
                'numero_registre': courrier.numero_registre,
                'objet': courrier.objet,
                'type_courrier': courrier.type_courrier,
                'type_courrier_display': courrier.get_type_courrier_display(),
                'date_principale': courrier.get_date_principale().isoformat() if courrier.get_date_principale() else None,
                'expediteur': courrier.expediteur,
                'destinataire': courrier.destinataire,
            })
        
        return Response(results)
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """
        Exporter le registre de courrier au format Excel.
        URL : GET /api/courriers/export_excel/
        Paramètre optionnel : fields=numero_registre,type_courrier,...
        
        Génère un fichier Excel avec les colonnes sélectionnées.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from django.http import HttpResponse
        from datetime import datetime
        
        # Appliquer les filtres de la requête
        queryset = self.filter_queryset(self.get_queryset())

        # Filtres supplémentaires non couverts par filter_queryset
        concerne = request.query_params.get('concerne', '').strip()
        expediteur = request.query_params.get('expediteur', '').strip()
        destinataire = request.query_params.get('destinataire', '').strip()
        if concerne:
            queryset = queryset.filter(
                Q(expediteur__icontains=concerne) | Q(destinataire__icontains=concerne)
            )
        if expediteur:
            queryset = queryset.filter(expediteur__icontains=expediteur)
        if destinataire:
            queryset = queryset.filter(destinataire__icontains=destinataire)

        # Définition de toutes les colonnes disponibles : clé → (label, getter)
        ALL_COLUMNS = [
            ('numero_registre',  "N° Registre",           lambda c: c.numero_registre),
            ('type_courrier',    "Type",                   lambda c: c.get_type_courrier_display()),
            ('date_reception',   "Date Réception",         lambda c: c.date_reception.strftime('%d/%m/%Y') if c.date_reception else ''),
            ('mode_reception',   "Mode de réception",      lambda c: c.get_mode_reception_display() if c.mode_reception else ''),
            ('date_envoi',       "Date Envoi",             lambda c: c.date_envoi.strftime('%d/%m/%Y') if c.date_envoi else ''),
            ('mode_envoi',       "Mode d'envoi",           lambda c: c.get_mode_envoi_display() if c.mode_envoi else ''),
            ('expediteur',       "Expéditeur",             lambda c: c.expediteur),
            ('destinataire',     "Destinataire",           lambda c: c.destinataire),
            ('objet',            "Objet",                  lambda c: c.objet),
            ('reference',        "Référence",              lambda c: c.reference),
            ('categorie',        "Catégorie",              lambda c: c.categorie.nom if c.categorie else ''),
            ('service_concerne', "Service Concerné",       lambda c: c.get_service_concerne_display() if c.service_concerne else ''),
            ('statut',           "Statut",                 lambda c: c.get_statut_display()),
            ('urgent',           "Urgent",                 lambda c: 'Oui' if c.urgent else 'Non'),
            ('notes',            "Notes",                  lambda c: c.notes),
            ('enregistre_par',   "Enregistré par",         lambda c: c.enregistre_par.username if c.enregistre_par else ''),
            ('created_at',       "Date d'enregistrement",  lambda c: c.created_at.strftime('%d/%m/%Y %H:%M')),
        ]

        # Filtrer les colonnes selon le param ?fields= (si fourni)
        requested = request.query_params.get('fields', '')
        if requested:
            requested_keys = [f.strip() for f in requested.split(',') if f.strip()]
            key_order = {k: i for i, k in enumerate(requested_keys)}
            columns = [col for col in ALL_COLUMNS if col[0] in requested_keys]
            columns.sort(key=lambda col: key_order.get(col[0], 999))
        else:
            # Par défaut : toutes les colonnes sauf mode_reception, mode_envoi, categorie, urgent
            default_keys = {'numero_registre','type_courrier','date_reception','date_envoi',
                            'expediteur','destinataire','objet','reference',
                            'service_concerne','statut','notes','enregistre_par','created_at'}
            columns = [col for col in ALL_COLUMNS if col[0] in default_keys]

        # Créer le workbook Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Registre de Courrier"
        
        # Styles pour l'en-tête
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'),  bottom=Side(style='thin')
        )
        
        # Écrire les en-têtes
        for col_num, (_, label, _getter) in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_num, value=label)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Écrire les données
        for row_num, courrier in enumerate(queryset, 2):
            for col_num, (_key, _label, getter) in enumerate(columns, 1):
                try:
                    value = getter(courrier)
                except Exception:
                    value = ''
                ws.cell(row=row_num, column=col_num, value=value).border = thin_border
        
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
        ancien_statut = courrier.statut
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
        
        # Si le statut passe à "traité", notifier les personnes concernées
        if nouveau_statut == 'traite' and ancien_statut != 'traite':
            from users.utils import creer_notification
            
            # Récupérer tous ceux qui ont affecté ce courrier
            affecteurs = courrier.affectations.filter(affecte_par__isnull=False).values_list('affecte_par', flat=True).distinct()
            
            for affecteur_id in affecteurs:
                try:
                    creer_notification(
                        utilisateur=affecteur_id,
                        type_notif='courrier_affecte',
                        titre=f'Courrier traité: {courrier.numero_registre}',
                        message=f'Le courrier "{courrier.objet}" a été marqué comme traité par {request.user.get_full_name() or request.user.username}.',
                        courrier_id=courrier.id,
                    )
                except Exception as e:
                    print(f"Erreur lors de la création de notification: {e}")
        
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
    
    @action(detail=True, methods=['post'])
    def affecter_service(self, request, pk=None):
        """
        Affecter un courrier à tous les utilisateurs d'un service.
        Crée un Circuit simultané + une Affectation par utilisateur du service
        (table affectations.Affectation — seule table d'affectation de référence).

        URL : POST /api/courriers/{id}/affecter_service/
        Body JSON :
        {
            "service_id": 1,
            "note": "...",
            "niveau_urgence": "normal|faible|eleve|critique",
            "date_echeance": "2026-03-20",
            "action_requise": "informatif|a_signer|..."
        }
        """
        from affectations.models import Circuit, Affectation
        from users.models import Notification

        try:
            courrier = self.get_object()
            service_id = request.data.get('service_id')
            note = request.data.get('note', '')
            niveau_urgence = request.data.get('niveau_urgence', 'normal')
            date_echeance = request.data.get('date_echeance') or None
            action_requise = request.data.get('action_requise', 'informatif')

            if not service_id:
                return Response(
                    {'error': 'service_id est requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                service = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
                return Response(
                    {'error': 'Service introuvable'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Récupérer les utilisateurs actifs du service
            utilisateurs_service = User.objects.filter(service=service, is_active=True)

            if not utilisateurs_service.exists():
                return Response(
                    {'error': f'Aucun utilisateur actif trouvé dans le service {service.nom}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Créer un circuit simultané pour ce courrier
            circuit = Circuit.objects.create(
                courrier=courrier,
                type_circuit='simultane',
                titre=f'Affectation au service {service.nom}',
                cree_par=request.user,
            )

            # Créer une affectation par utilisateur du service
            affectations_creees = []
            for utilisateur in utilisateurs_service:
                affectation = Affectation.objects.create(
                    circuit=circuit,
                    courrier=courrier,
                    destinataire=utilisateur,
                    service=service,
                    affecte_par=request.user,
                    action_requise=action_requise,
                    niveau_urgence=niveau_urgence,
                    date_echeance=date_echeance,
                    note_instruction=note,
                    etape_numero=1,
                    statut='distribue',
                )
                affectations_creees.append(affectation)

                # Notification
                Notification.objects.create(
                    utilisateur=utilisateur,
                    type='courrier_affecte',
                    titre=f'Nouveau courrier affecté : {courrier.numero_registre}',
                    message=(
                        f'Le courrier "{courrier.objet}" a été affecté à votre service '
                        f'({service.nom}). Action requise : {affectation.get_action_requise_display()}'
                    ),
                    courrier_id=courrier.id,
                )

            # Mettre à jour le statut et le service du courrier
            if courrier.statut == 'recu':
                courrier.statut = 'en_traitement'
            service_code = Courrier.get_service_code_from_name(service.nom)
            courrier.service_concerne = service_code
            courrier.save()

            ActionLog.log_action(
                action_type='affectation_create',
                utilisateur=request.user,
                description=(
                    f"Courrier {courrier.numero_registre} affecté au service {service.nom} "
                    f"via circuit #{circuit.id} ({len(affectations_creees)} affectation(s))"
                ),
                courrier=courrier,
                request=request,
            )

            return Response({
                'message': f'Courrier affecté à {len(affectations_creees)} utilisateur(s) du service {service.nom}',
                'circuit_id': circuit.id,
                'service_nom': service.nom,
                'service_code': service_code,
                'utilisateurs_affectes': len(affectations_creees),
                'courrier_numero': courrier.numero_registre,
                'courrier_statut': courrier.statut,
                'courrier_service_concerne': courrier.service_concerne,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def mes_affectations(self, request):
        """
        Récupérer les affectations de courriers pour l'utilisateur connecté.
        URL : GET /api/courriers/mes_affectations/
        """
        affectations = AffectationCourrier.objects.filter(
            utilisateur=request.user
        ).select_related('courrier', 'affecte_par').order_by('-date_affectation')
        
        serializer = AffectationCourrierSerializer(affectations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def mes_courriers(self, request):
        """
        Récupérer les courriers affectés à l'utilisateur connecté.
        URL : GET /api/courriers/mes_courriers/

        Utilise uniquement affectations.Affectation (table de référence).
        """
        from django.db.models import Q
        from affectations.models import Affectation

        # IDs des courriers affectés au user (nouveau système, seule source de vérité)
        courriers_ids = set(
            Affectation.objects
            .filter(destinataire=request.user)
            .exclude(statut='renvoye')
            .values_list('courrier_id', flat=True)
        )

        # Récupérer les courriers correspondants
        courriers = Courrier.objects.filter(id__in=courriers_ids).order_by('-created_at')

        # Filtres optionnels
        search = request.query_params.get('search')
        if search:
            courriers = courriers.filter(
                Q(numero_registre__icontains=search) |
                Q(objet__icontains=search) |
                Q(expediteur__icontains=search) |
                Q(destinataire__icontains=search)
            )

        ordering = request.query_params.get('ordering')
        if ordering:
            courriers = courriers.order_by(ordering)

        serializer = CourrierSerializer(courriers, many=True)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Archiver (soft delete) un courrier au lieu de le supprimer complètement.
        URL : DELETE /api/courriers/{id}/
        """
        courrier = self.get_object()
        
        # Archiver le courrier (soft delete)
        courrier.soft_delete(request.user)
        ActionLog.log_action(
            action_type='courrier_archive',
            utilisateur=request.user,
            description=f"Courrier {courrier.numero_registre} archivé : {courrier.objet}",
            courrier=courrier,
            request=request,
        )
        return Response({
            "message": "Courrier archivé avec succès"
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def archives(self, request):
        """
        Récupérer tous les courriers archivés (supprimés) accessibles par l'utilisateur.
        URL : GET /api/courriers/archives/
        """
        # Récupérer tous les courriers supprimés
        user = request.user
        
        if user.role == 'admin' or user.role == 'rh':
            # Les admins et RH voient tous les courriers archivés
            archived_courriers = Courrier.objects.filter(is_deleted=True)
        else:
            # Les utilisateurs ne voient que leurs propres courriers archivés
            archived_courriers = Courrier.objects.filter(is_deleted=True, enregistre_par=user)
        
        # Appliquer les filtres de recherche si nécessaire
        search_query = request.query_params.get('search', None)
        if search_query:
            archived_courriers = archived_courriers.filter(
                Q(numero_registre__icontains=search_query) |
                Q(objet__icontains=search_query) |
                Q(expediteur__icontains=search_query) |
                Q(destinataire__icontains=search_query)
            )
        
        # Trier par date de suppression (plus récent en premier)
        archived_courriers = archived_courriers.order_by('-deleted_at')
        
        serializer = self.get_serializer(archived_courriers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restaurer un courrier archivé.
        URL : POST /api/courriers/{id}/restore/
        """
        # Récupérer le courrier même s'il est supprimé
        try:
            courrier = Courrier.objects.get(pk=pk)
        except Courrier.DoesNotExist:
            return Response(
                {"error": "Courrier non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier que le courrier est bien archivé
        if not courrier.is_deleted:
            return Response(
                {"error": "Ce courrier n'est pas archivé"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restaurer le courrier
        courrier.restore()
        ActionLog.log_action(
            action_type='courrier_restore',
            utilisateur=request.user,
            description=f"Courrier {courrier.numero_registre} restauré depuis les archives.",
            courrier=courrier,
            request=request,
        )
        serializer = self.get_serializer(courrier)
        return Response({
            "message": "Courrier restauré avec succès",
            "courrier": serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='archives-status')
    def archives_status(self, request):
        """
        Récupérer tous les courriers avec statut='archive' (courriers traités et classés).
        URL : GET /api/courriers/archives-status/
        """
        user = request.user
        
        # Récupérer les courriers archivés (statut='archive') et non supprimés
        if user.role == 'admin' or user.role == 'rh':
            # Les admins et RH voient tous les courriers archivés
            archived_courriers = Courrier.objects.filter(statut='archive', is_deleted=False)
        else:
            # Les utilisateurs ne voient que leurs propres courriers archivés
            archived_courriers = Courrier.objects.filter(
                statut='archive', 
                is_deleted=False, 
                enregistre_par=user
            )
        
        # Appliquer les filtres de recherche si nécessaire
        search_query = request.query_params.get('search', None)
        if search_query:
            archived_courriers = archived_courriers.filter(
                Q(numero_registre__icontains=search_query) |
                Q(objet__icontains=search_query) |
                Q(expediteur__icontains=search_query) |
                Q(destinataire__icontains=search_query)
            )
        
        # Trier par date de création (plus récent en premier)
        ordering = request.query_params.get('ordering', '-created_at')
        archived_courriers = archived_courriers.order_by(ordering)
        
        serializer = self.get_serializer(archived_courriers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Récupérer toutes les versions d'un courrier.
        URL : GET /api/courriers/{id}/versions/
        """
        courrier = self.get_object()
        
        # Récupérer toutes les versions de ce courrier
        if courrier.courrier_parent:
            # Si c'est une version, récupérer toutes les versions du parent
            parent = courrier.courrier_parent
            versions = Courrier.objects.filter(
                Q(id=parent.id) | Q(courrier_parent=parent)
            ).order_by('version_number')
        else:
            # Si c'est le parent, récupérer lui-même et toutes ses versions
            versions = Courrier.objects.filter(
                Q(id=courrier.id) | Q(courrier_parent=courrier)
            ).order_by('version_number')
        
        serializer = self.get_serializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def services_disponibles(self, request):
        """
        Liste des services disponibles pour l'affectation.
        URL : GET /api/courriers/services_disponibles/
        """
        services = Service.objects.all().order_by('nom')
        serializer = ServiceSimpleSerializer(services, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='pieces_jointes')
    def ajouter_piece_jointe(self, request, pk=None):
        """
        Ajouter une ou plusieurs pièces jointes à un courrier existant.
        URL : POST /api/courriers/{id}/pieces_jointes/
        """
        courrier = self.get_object()
        fichiers = request.FILES.getlist('fichiers')
        if not fichiers:
            return Response({'error': 'Aucun fichier fourni.'}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        for f in fichiers:
            ext = f.name.split('.')[-1].lower()
            if ext == 'pdf':
                ftype = 'pdf'
            elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                ftype = 'image'
            else:
                ftype = ext
            pj = CourrierPieceJointe.objects.create(
                courrier=courrier,
                fichier=f,
                nom_fichier=f.name,
                file_type=ftype,
                file_size=f.size,
                uploaded_by=request.user,
            )
            created.append(pj)

        from .serializer import CourrierPieceJointeSerializer
        serializer = CourrierPieceJointeSerializer(created, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'pieces_jointes/(?P<pj_id>\d+)')
    def supprimer_piece_jointe(self, request, pk=None, pj_id=None):
        """
        Supprimer une pièce jointe d'un courrier.
        URL : DELETE /api/courriers/{id}/pieces_jointes/{pj_id}/
        """
        courrier = self.get_object()
        try:
            pj = CourrierPieceJointe.objects.get(id=pj_id, courrier=courrier)
        except CourrierPieceJointe.DoesNotExist:
            return Response({'error': 'Pièce jointe introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        pj.fichier.delete(save=False)  # Supprimer le fichier physique
        pj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


# ============================================================================
# UTILITAIRES POUR LA SIGNATURE ÉLECTRONIQUE
# ============================================================================

def appliquer_signature_pdf(pdf_path, signature_path, position_x, position_y, largeur, hauteur, page_height=842):
    """
    Applique une signature électronique sur un PDF.
    
    Args:
        pdf_path: Chemin vers le PDF original
        signature_path: Chemin vers l'image de signature
        position_x: Position X (en pixels frontend)
        position_y: Position Y (en pixels frontend)
        largeur: Largeur de la signature (en pixels)
        hauteur: Hauteur de la signature (en pixels)
        page_height: Hauteur de la zone d'affichage frontend (défaut: 1200px)
    
    Returns:
        BytesIO contenant le PDF signé
    """
    # Convertir les coordonnées frontend (pixels) vers coordonnées PDF (points)
    # PDF utilise points (72 points = 1 inch) et origine en bas-gauche
    # Frontend utilise pixels et origine en haut-gauche
    
    # Facteur de conversion : hauteur de page PDF standard (A4) = 842 points
    pdf_page_height = 842  # Points pour A4
    scale_factor = pdf_page_height / page_height  # page_height = 1200px frontend
    
    # Convertir position et dimensions
    x_pdf = position_x * scale_factor
    y_pdf = pdf_page_height - (position_y * scale_factor) - (hauteur * scale_factor)
    w_pdf = largeur * scale_factor
    h_pdf = hauteur * scale_factor
    
    # Créer un PDF temporaire avec juste la signature
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # Vérifier que le fichier de signature existe
    import os
    if not os.path.exists(signature_path):
        raise FileNotFoundError(f"Le fichier de signature n'existe pas : {signature_path}")
    
    # Ajouter l'image de signature
    try:
        # Utiliser un chemin absolu avec normalisation
        signature_abs_path = os.path.abspath(signature_path)
        img = ImageReader(signature_abs_path)
        can.drawImage(img, x_pdf, y_pdf, width=w_pdf, height=h_pdf, mask='auto')
    except Exception as e:
        print(f"Erreur lors de l'ajout de l'image: {e}")
        raise Exception(f"Impossible de charger l'image de signature : {str(e)}")
    
    can.save()
    packet.seek(0)
    
    # Lire le PDF original
    existing_pdf = PdfReader(open(pdf_path, "rb"))
    signature_pdf = PdfReader(packet)
    
    # Créer le PDF de sortie
    output = PdfWriter()
    
    # Fusionner la signature avec la première page
    page = existing_pdf.pages[0]
    page.merge_page(signature_pdf.pages[0])
    output.add_page(page)
    
    # Ajouter les autres pages sans modification
    for i in range(1, len(existing_pdf.pages)):
        output.add_page(existing_pdf.pages[i])
    
    # Écrire dans un BytesIO
    output_stream = io.BytesIO()
    output.write(output_stream)
    output_stream.seek(0)
    
    return output_stream


# ============================================================================
# VIEWSETS POUR LES AFFECTATIONS DE COURRIERS
# ============================================================================

class AffectationCourrierViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les affectations de courriers.
    
    Fonctionnalités :
    - CRUD complet des affectations
    - Marquer comme lu
    - Valider/Rejeter/Signer
    - Ajouter des commentaires
    """
    queryset = AffectationCourrier.objects.all()
    serializer_class = AffectationCourrierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, rest_filters.OrderingFilter]
    ordering_fields = ['date_affectation', 'date_lecture', 'statut']
    ordering = ['-date_affectation']
    
    def get_queryset(self):
        """
        Filtrer les affectations selon l'utilisateur :
        - Utilisateurs normaux : seulement leurs affectations
        - RH/Admin : toutes les affectations
        """
        user = self.request.user
        queryset = AffectationCourrier.objects.select_related(
            'courrier', 
            'utilisateur', 
            'utilisateur__service',
            'affecte_par'
        )
        
        if user.role in ['rh', 'admin']:
            return queryset
        else:
            return queryset.filter(utilisateur=user)
    
    @action(detail=True, methods=['post'])
    def marquer_lu(self, request, pk=None):
        """
        Marquer une affectation comme lue.
        URL : POST /api/affectations/{id}/marquer_lu/
        """
        affectation = self.get_object()
        
        # Vérifier que c'est bien l'utilisateur concerné
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        affectation.marquer_comme_lu()
        
        serializer = self.get_serializer(affectation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def commencer_traitement(self, request, pk=None):
        """
        L'utilisateur clique "Traiter" après avoir vu le courrier.
        - informatif  → directement 'valide'
        - autres      → 'en_traitement'
        URL : POST /api/affectations/{id}/commencer_traitement/
        """
        affectation = self.get_object()
        
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if affectation.statut not in ['distribue', 'vu', 'en_attente', 'lu']:
            return Response(
                {'error': 'Cette affectation ne peut plus être mise en traitement'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        affectation.traiter()
        ActionLog.log_action(
            action_type='affectation_start',
            utilisateur=request.user,
            description=f"Traitement commencé pour le courrier {affectation.courrier.numero_registre}",
            courrier=affectation.courrier,
            affectation=affectation,
            request=request,
        )
        serializer = self.get_serializer(affectation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def renvoyer(self, request, pk=None):
        """
        L'utilisateur renvoie le courrier.
        URL : POST /api/affectations/{id}/renvoyer/
        Body : { "commentaire": "..." }  (optionnel)
        """
        affectation = self.get_object()
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        commentaire = request.data.get('commentaire', '')
        affectation.renvoyer(commentaire)
        ActionLog.log_action(
            action_type='affectation_renvoye',
            utilisateur=request.user,
            description=f"Courrier {affectation.courrier.numero_registre} renvoyé",
            courrier=affectation.courrier,
            affectation=affectation,
            request=request,
        )
        serializer = self.get_serializer(affectation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accuser_reception(self, request, pk=None):
        """
        Accuser réception d'un courrier.
        URL : POST /api/affectations/{id}/accuser_reception/
        Body : { "commentaire": "Réceptionné" }  (optionnel)
        """
        affectation = self.get_object()
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        if affectation.statut not in ['vu', 'distribue', 'en_attente', 'lu']:
            return Response(
                {'error': 'Action non autorisée pour ce statut'},
                status=status.HTTP_400_BAD_REQUEST
            )
        commentaire = request.data.get('commentaire', '')
        affectation.accuser_reception(commentaire)
        ActionLog.log_action(
            action_type='affectation_accuse',
            utilisateur=request.user,
            description=f"Accusé de réception pour le courrier {affectation.courrier.numero_registre}",
            courrier=affectation.courrier,
            affectation=affectation,
            request=request,
        )
        serializer = self.get_serializer(affectation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def repondre(self, request, pk=None):
        """
        Répondre à un courrier.
        URL : POST /api/affectations/{id}/repondre/
        Body : { "commentaire": "Réponse ..." }  (optionnel)
        """
        affectation = self.get_object()
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        if affectation.statut not in ['vu', 'distribue', 'en_attente', 'lu']:
            return Response(
                {'error': 'Action non autorisée pour ce statut'},
                status=status.HTTP_400_BAD_REQUEST
            )
        commentaire = request.data.get('commentaire', '')
        affectation.repondre(commentaire)
        ActionLog.log_action(
            action_type='affectation_repondre',
            utilisateur=request.user,
            description=f"Réponse enregistrée pour le courrier {affectation.courrier.numero_registre}",
            courrier=affectation.courrier,
            affectation=affectation,
            request=request,
        )
        serializer = self.get_serializer(affectation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        """
        Valider une affectation de courrier.
        URL : POST /api/affectations/{id}/valider/
        Body : { "commentaire": "Validé après vérification" }
        """
        affectation = self.get_object()
        
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        commentaire = request.data.get('commentaire', '')
        affectation.valider(commentaire)
        ActionLog.log_action(
            action_type='affectation_validate',
            utilisateur=request.user,
            description=f"Courrier {affectation.courrier.numero_registre} validé",
            courrier=affectation.courrier,
            affectation=affectation,
            request=request,
        )
        serializer = self.get_serializer(affectation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        """
        Rejeter une affectation de courrier.
        URL : POST /api/affectations/{id}/rejeter/
        Body : { "motif": "Document incomplet" }
        """
        affectation = self.get_object()
        
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        motif = request.data.get('motif', '')
        if not motif:
            return Response(
                {'error': 'Le motif de rejet est obligatoire'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        affectation.rejeter(motif)
        ActionLog.log_action(
            action_type='affectation_reject',
            utilisateur=request.user,
            description=f"Courrier {affectation.courrier.numero_registre} rejeté : {motif}",
            courrier=affectation.courrier,
            affectation=affectation,
            request=request,
        )
        serializer = self.get_serializer(affectation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def signer(self, request, pk=None):
        """
        Signer électroniquement une affectation de courrier.
        URL : POST /api/affectations/{id}/signer/
        Body : { 
            "commentaire": "Signé électroniquement",
            "position": {"x": 100, "y": 200},
            "size": {"width": 200, "height": 80}
        }
        """
        affectation = self.get_object()
        
        if affectation.utilisateur != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que vos propres affectations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que l'utilisateur a une signature configurée
        if not request.user.signature_electronique:
            return Response(
                {'error': 'Vous devez configurer votre signature électronique'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        commentaire = request.data.get('commentaire', 'Signé électroniquement')
        position = request.data.get('position', {})
        size = request.data.get('size', {})
        
        # Récupérer le courrier associé
        courrier = affectation.courrier
        
        # Vérifier que le courrier a un fichier PDF
        if not courrier.fichier:
            return Response(
                {'error': 'Ce courrier n\'a pas de fichier PDF'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Appliquer la signature sur le PDF
            pdf_signe = appliquer_signature_pdf(
                pdf_path=courrier.fichier.path,
                signature_path=request.user.signature_electronique.path,
                position_x=position.get('x', 100),
                position_y=position.get('y', 100),
                largeur=size.get('width', 200),
                hauteur=size.get('height', 80),
                page_height=1200  # Hauteur du conteneur frontend
            )
            
            # Import du modèle FichierCourrierVersion
            from documents.models import FichierCourrierVersion
            
            # Déterminer le numéro de la nouvelle version
            derniere_version = courrier.fichier_versions.order_by('-version_number').first()
            
            if derniere_version:
                nouveau_numero = derniere_version.version_number + 1
            else:
                # Première version : sauvegarder d'abord le fichier original comme V1
                from django.core.files.base import File
                with open(courrier.fichier.path, 'rb') as f:
                    fichier_original = File(f)
                    fichier_content = fichier_original.read()
                    
                FichierCourrierVersion.objects.create(
                    courrier=courrier,
                    fichier=ContentFile(fichier_content, name=f"{courrier.numero_registre}_v1.pdf"),
                    version_number=1,
                    notes_version="Version originale",
                    est_version_actuelle=False,  # L'originale n'est plus actuelle
                    cree_par=courrier.enregistre_par
                )
                nouveau_numero = 2
            
            # Désactiver toutes les versions précédentes
            courrier.fichier_versions.update(est_version_actuelle=False)
            
            # Créer la nouvelle version avec le PDF signé
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{courrier.numero_registre}_v{nouveau_numero}_{timestamp}.pdf"
            notes_version = f"Signé par {request.user.get_full_name() or request.user.username} le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
            
            pdf_signe_file = ContentFile(pdf_signe.read(), name=filename)
            
            FichierCourrierVersion.objects.create(
                courrier=courrier,
                fichier=pdf_signe_file,
                version_number=nouveau_numero,
                notes_version=notes_version,
                est_version_actuelle=True,
                cree_par=request.user
            )
            
            # Remplacer le fichier principal du courrier par le fichier signé
            # Sauvegarder d'abord le nom d'origine pour le delete
            ancien_fichier = courrier.fichier.name
            
            # Créer une nouvelle copie pour le champ principal
            pdf_signe.seek(0)  # Reset file pointer
            courrier.fichier.save(filename, ContentFile(pdf_signe.read()), save=False)
            courrier.save()
            
            # Optionnel : supprimer l'ancien fichier principal (pas les versions)
            # depuis le système de fichiers pour économiser l'espace
            # (décommenter si souhaité)
            # import os
            # if ancien_fichier and os.path.exists(ancien_fichier):
            #     os.remove(ancien_fichier)
            
            # Marquer l'affectation comme signée
            affectation.signer(commentaire)
            ActionLog.log_action(
                action_type='affectation_sign',
                utilisateur=request.user,
                description=f"Courrier {courrier.numero_registre} signé électroniquement",
                courrier=courrier,
                affectation=affectation,
                request=request,
            )
            print(f"✅ Version {nouveau_numero} créée pour le courrier {courrier.numero_registre}")
            
            serializer = self.get_serializer(affectation)
            return Response(serializer.data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Erreur lors de l\'application de la signature: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get', 'post'])
    def commentaires(self, request, pk=None):
        """
        Récupérer (GET) ou ajouter (POST) des commentaires sur une affectation.
        URL : 
        - GET /api/affectations/{id}/commentaires/
        - POST /api/affectations/{id}/commentaires/
        Body (POST) : { "contenu": "Mon commentaire..." }
        """
        affectation = self.get_object()
        
        if request.method == 'GET':
            commentaires = affectation.commentaires.all()
            serializer = CommentaireCourrierSerializer(commentaires, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            contenu = request.data.get('contenu', '').strip()
            
            if not contenu:
                return Response(
                    {'error': 'Le contenu du commentaire est obligatoire'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            commentaire = CommentaireCourrier.objects.create(
                affectation=affectation,
                auteur=request.user,
                contenu=contenu
            )
            ActionLog.log_action(
                action_type='commentaire_add',
                utilisateur=request.user,
                description=f"Commentaire ajouté sur le courrier {affectation.courrier.numero_registre}",
                courrier=affectation.courrier,
                affectation=affectation,
                request=request,
            )
            from users.utils import creer_notification
            
            # Récupérer tous les utilisateurs actifs sauf l'auteur du commentaire
            utilisateurs_concernes = User.objects.filter(
                is_active=True
            ).exclude(id=request.user.id)
            
            print(f"Nb utilisateurs à notifier: {utilisateurs_concernes.count()}")  # Debug
            
            for utilisateur in utilisateurs_concernes:
                try:
                    notif = creer_notification(
                        utilisateur=utilisateur,
                        type_notif='commentaire',
                        titre=f'Nouveau commentaire: {affectation.courrier.numero_registre}',
                        message=f'{request.user.get_full_name() or request.user.username} a ajouté un commentaire sur le courrier "{affectation.courrier.objet}".',
                        courrier_id=affectation.courrier.id,
                    )
                    print(f"Notification créée pour {utilisateur.username}: {notif.id}")  # Debug
                except Exception as e:
                    print(f"Erreur lors de la création de notification pour {utilisateur.username}: {e}")
            
            serializer = CommentaireCourrierSerializer(commentaire)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    


