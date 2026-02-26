from django.contrib import admin
from .models import Courrier


@admin.register(Courrier)
class CourrierAdmin(admin.ModelAdmin):
    list_display = ['reference', 'type', 'objet', 'statut', 'expediteur', 'destinataire', 'created_at']
    list_filter = ['type', 'statut', 'categorie', 'created_at']
    search_fields = ['reference', 'objet', 'expediteur', 'destinataire', 'description']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('reference', 'type', 'objet', 'description', 'statut')
        }),
        ('Courrier entrant', {
            'fields': ('expediteur', 'date_reception'),
            'classes': ('collapse',)
        }),
        ('Courrier sortant', {
            'fields': ('destinataire', 'date_envoi', 'mode_envoi', 'reponse_a'),
            'classes': ('collapse',)
        }),
        ('Classification', {
            'fields': ('categorie', 'service')
        }),
        ('Fichier', {
            'fields': ('fichier',)
        }),
        ('Métadonnées', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
