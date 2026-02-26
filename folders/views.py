from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import models
from . import serializers as sz
from documents.models import Document
from documents.serializer import DocumentSerializer


class FolderViewSet(viewsets.ModelViewSet):
    queryset = models.Folder.objects.all()
    serializer_class = sz.FolderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Retourne tous les dossiers.
        Le champ 'has_access' dans le serializer indique si l'utilisateur y a accès.
        """
        queryset = models.Folder.objects.all()
        
        # Filtrer par parent si spécifié
        parent_id = self.request.query_params.get('parent', None)
        if parent_id is not None:
            if parent_id == 'null' or parent_id == '':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        return queryset.order_by('created_at')

    def perform_create(self, serializer):
        """Associer automatiquement le propriétaire lors de la création"""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def contents(self, request, pk=None):
        """
        Récupérer le contenu d'un dossier (sous-dossiers et documents).
        URL : GET /api/folders/{id}/contents/
        """
        folder = self.get_object()
        
        # Vérifier que l'utilisateur a accès
        if folder.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Accès refusé"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Récupérer les sous-dossiers
        subfolders = models.Folder.objects.filter(parent=folder)
        subfolders_serializer = sz.FolderSerializer(subfolders, many=True, context={'request': request})
        
        # Récupérer les documents
        documents = Document.objects.filter(folder=folder)
        documents_serializer = DocumentSerializer(documents, many=True, context={'request': request})
        
        return Response({
            "folder": sz.FolderSerializer(folder, context={'request': request}).data,
            "subfolders": subfolders_serializer.data,
            "documents": documents_serializer.data
        })

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Récupérer l'arborescence complète des dossiers.
        URL : GET /api/folders/tree/
        """
        # Récupérer tous les dossiers racines (sans parent)
        root_folders = models.Folder.objects.filter(
            parent__isnull=True
        )
        
        serializer = sz.FolderTreeSerializer(root_folders, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """
        Déplacer un dossier vers un autre dossier parent.
        URL : POST /api/folders/{id}/move/
        Body: {"parent_id": 123} ou {"parent_id": null} pour la racine
        """
        folder = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire ou admin
        if folder.owner != request.user and request.user.role != 'admin':
            return Response(
                {"error": "Seul le propriétaire ou un administrateur peut déplacer ce dossier"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        parent_id = request.data.get('parent_id')
        
        # Si parent_id est null, déplacer à la racine
        if parent_id is None:
            folder.parent = None
            folder.save()
            return Response({
                "message": "Dossier déplacé à la racine",
                "folder": sz.FolderSerializer(folder).data
            })
        
        # Vérifier que le dossier de destination existe
        try:
            parent_folder = models.Folder.objects.get(id=parent_id)
        except models.Folder.DoesNotExist:
            return Response(
                {"error": "Le dossier de destination n'existe pas"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier qu'on ne déplace pas un dossier dans lui-même
        if folder.id == parent_folder.id:
            return Response(
                {"error": "Impossible de déplacer un dossier dans lui-même"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier qu'on ne crée pas de boucle (déplacer dans un de ses sous-dossiers)
        current = parent_folder
        while current:
            if current.id == folder.id:
                return Response(
                    {"error": "Impossible de déplacer un dossier dans un de ses sous-dossiers"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            current = current.parent
        
        # Vérifier que le dossier n'est pas déjà dans ce parent
        if folder.parent == parent_folder:
            return Response(
                {"error": "Le dossier est déjà dans ce dossier"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        folder.parent = parent_folder
        folder.save()
        
        return Response({
            "message": "Dossier déplacé avec succès",
            "folder": sz.FolderSerializer(folder).data
        })

    @action(detail=True, methods=['get'])
    def path(self, request, pk=None):
        """
        Récupérer le chemin complet d'un dossier.
        URL : GET /api/folders/{id}/path/
        """
        folder = self.get_object()
        
        path = []
        current = folder
        while current:
            path.insert(0, {
                'id': current.id,
                'name': current.name
            })
            current = current.parent
        
        return Response({"path": path})
