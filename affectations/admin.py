from django.contrib import admin
from .models import Circuit, Affectation


@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    list_display = ['id', 'courrier', 'type_circuit', 'statut', 'cree_par', 'date_creation']
    list_filter = ['type_circuit', 'statut']
    search_fields = ['courrier__numero_registre', 'titre']
    readonly_fields = ['date_creation', 'date_modification']


@admin.register(Affectation)
class AffectationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'courrier', 'destinataire', 'circuit', 'etape_numero',
        'action_requise', 'statut', 'niveau_urgence', 'date_echeance',
    ]
    list_filter = ['statut', 'action_requise', 'niveau_urgence']
    search_fields = ['courrier__numero_registre', 'destinataire__username']
    readonly_fields = ['date_affectation', 'date_lecture', 'date_traitement']
