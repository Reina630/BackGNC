from django.contrib import admin
from .models import Document, DocumentVersion, DocumentShare, Categorie

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'file_type', 'visibility', 'is_favorite', 'created_at']
    list_filter = ['file_type', 'visibility', 'is_favorite', 'created_at']
    search_fields = ['title', 'owner__username']

@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'created_at', 'updated_by']
    list_filter = ['created_at']

@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = ['document', 'shared_with', 'shared_by', 'permission', 'shared_at']
    list_filter = ['permission', 'shared_at']
    search_fields = ['document__title', 'shared_with__username', 'shared_by__username']
