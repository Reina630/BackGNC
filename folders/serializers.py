from rest_framework import serializers as sz
from . import models

class FolderSerializer(sz.ModelSerializer):
    owner_name = sz.CharField(source='owner.username', read_only=True)
    subfolders_count = sz.SerializerMethodField()
    documents_count = sz.SerializerMethodField()
    path = sz.SerializerMethodField()
    is_owner = sz.SerializerMethodField()
    has_access = sz.SerializerMethodField()
    
    class Meta:
        model = models.Folder
        fields = [
            'id', 'name', 'parent', 'owner', 'owner_name',
            'created_at', 'subfolders_count', 'documents_count', 'path', 'is_owner', 'has_access'
        ]
        read_only_fields = ['id', 'owner', 'created_at']
    
    def get_subfolders_count(self, obj):
        return obj.subfolders.count()
    
    def get_documents_count(self, obj):
        return obj.document_set.count()
    
    def get_path(self, obj):
        """Retourne le chemin complet du dossier"""
        path = []
        current = obj
        while current:
            path.insert(0, {'id': current.id, 'name': current.name})
            current = current.parent
        return path
    
    def get_is_owner(self, obj):
        """Indique si l'utilisateur actuel est propriétaire du dossier"""
        request = self.context.get('request')
        if not request or not request.user:
            return False
        return obj.owner == request.user
    
    def get_has_access(self, obj):
        """Indique si l'utilisateur actuel a accès au dossier"""
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        user = request.user
        # L'utilisateur a accès si:
        # - Il est propriétaire
        # - Il est administrateur
        return obj.owner == user or user.role == 'admin'

class FolderTreeSerializer(sz.ModelSerializer):
    """Serializer pour l'arborescence complète"""
    owner_name = sz.CharField(source='owner.username', read_only=True)
    subfolders = sz.SerializerMethodField()
    documents_count = sz.SerializerMethodField()
    has_access = sz.SerializerMethodField()
    
    class Meta:
        model = models.Folder
        fields = [
            'id', 'name', 'parent', 'owner', 'owner_name',
            'created_at', 'subfolders', 'documents_count', 'has_access'
        ]
        read_only_fields = ['id', 'owner', 'created_at']
    
    def get_subfolders(self, obj):
        """Récursion pour obtenir tous les sous-dossiers"""
        subfolders = obj.subfolders.all()
        return FolderTreeSerializer(subfolders, many=True, context=self.context).data
    
    def get_documents_count(self, obj):
        return obj.document_set.count()
    
    def get_has_access(self, obj):
        """Indique si l'utilisateur actuel a accès au dossier"""
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        user = request.user
        # L'utilisateur a accès si:
        # - Il est propriétaire
        # - Il est administrateur
        return obj.owner == user or user.role == 'admin'
