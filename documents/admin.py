from django.contrib import admin
from .models import (
    Document, DocumentVersion, DocumentShare, Categorie,
    AffectationCourrier, CommentaireCourrier
)

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


# ============================================================================
# ADMIN POUR LES AFFECTATIONS DE COURRIERS
# ============================================================================

@admin.register(AffectationCourrier)
class AffectationCourrierAdmin(admin.ModelAdmin):
    list_display = ['courrier', 'utilisateur', 'statut', 'date_affectation', 'date_lecture', 'date_traitement']
    list_filter = ['statut', 'date_affectation', 'date_traitement']
    search_fields = ['courrier__numero_registre', 'courrier__objet', 'utilisateur__username', 'utilisateur__email']
    readonly_fields = ['date_affectation', 'date_lecture', 'date_traitement']
    date_hierarchy = 'date_affectation'
    
    fieldsets = (
        ('Affectation', {
            'fields': ('courrier', 'utilisateur', 'affecte_par', 'note')
        }),
        ('Traitement', {
            'fields': ('statut', 'commentaire_traitement', 'motif_rejet')
        }),
        ('Dates', {
            'fields': ('date_affectation', 'date_lecture', 'date_traitement'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CommentaireCourrier)
class CommentaireCourrierAdmin(admin.ModelAdmin):
    list_display = ['affectation', 'auteur', 'date_creation', 'contenu_court']
    list_filter = ['date_creation']
    search_fields = ['affectation__courrier__numero_registre', 'auteur__username', 'contenu']
    readonly_fields = ['date_creation']
    date_hierarchy = 'date_creation'
    
    def contenu_court(self, obj):
        return obj.contenu[:50] + '...' if len(obj.contenu) > 50 else obj.contenu
    contenu_court.short_description = 'Contenu'
