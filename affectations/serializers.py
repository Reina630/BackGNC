from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Circuit, Affectation
from users.models import Service

User = get_user_model()


# ============================================================================
# Serializers utilitaires
# ============================================================================

class UserMiniSerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'nom_complet', 'email', 'role']

    def get_nom_complet(self, obj):
        return obj.get_full_name() or obj.username


class ServiceMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'nom']


# ============================================================================
# Affectation
# ============================================================================

class AffectationSerializer(serializers.ModelSerializer):
    destinataire_detail = UserMiniSerializer(source='destinataire', read_only=True)
    affecte_par_detail = UserMiniSerializer(source='affecte_par', read_only=True)
    service_detail = ServiceMiniSerializer(source='service', read_only=True)
    peut_traiter = serializers.SerializerMethodField()
    courrier_numero = serializers.CharField(source='courrier.numero_registre', read_only=True)
    courrier_objet = serializers.CharField(source='courrier.objet', read_only=True)

    class Meta:
        model = Affectation
        fields = [
            'id',
            'circuit',
            'courrier', 'courrier_numero', 'courrier_objet',
            # Configuration
            'destinataire', 'destinataire_detail',
            'service', 'service_detail',
            'affecte_par', 'affecte_par_detail',
            'action_requise',
            'note_instruction',
            'niveau_urgence',
            'date_echeance',
            'etape_numero',
            # Traitement
            'statut',
            'commentaire_traitement',
            'motif_rejet',
            # Dates
            'date_affectation',
            'date_lecture',
            'date_traitement',
            # Extra
            'metadata',
            'peut_traiter',
        ]
        read_only_fields = [
            'affecte_par', 'date_affectation', 'date_lecture', 'date_traitement',
            'statut', 'commentaire_traitement', 'motif_rejet',
        ]

    def get_peut_traiter(self, obj):
        return obj.peut_etre_traitee()


class AffectationWriteSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une affectation individuelle."""

    class Meta:
        model = Affectation
        fields = [
            'destinataire',
            'service',
            'action_requise',
            'note_instruction',
            'niveau_urgence',
            'date_echeance',
            'etape_numero',
            'metadata',
        ]


# ============================================================================
# Circuit
# ============================================================================

class CircuitSerializer(serializers.ModelSerializer):
    affectations = AffectationSerializer(many=True, read_only=True)
    cree_par_detail = UserMiniSerializer(source='cree_par', read_only=True)
    courrier_numero = serializers.CharField(source='courrier.numero_registre', read_only=True)
    courrier_objet = serializers.CharField(source='courrier.objet', read_only=True)
    etape_actuelle = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Circuit
        fields = [
            'id',
            'courrier', 'courrier_numero', 'courrier_objet',
            'type_circuit',
            'statut',
            'titre',
            'instructions_generales',
            'cree_par', 'cree_par_detail',
            'date_creation', 'date_modification',
            'metadata',
            'etape_actuelle',
            'progress',
            'affectations',
        ]
        read_only_fields = ['cree_par', 'statut', 'date_creation', 'date_modification']

    def get_etape_actuelle(self, obj):
        return obj.get_etape_actuelle()

    def get_progress(self, obj):
        """Retourne les stats de progression du circuit."""
        affectations = obj.affectations.all()
        total = affectations.count()
        if total == 0:
            return {'total': 0, 'terminees': 0, 'pourcentage': 0}
        statuts_termines = {'valide', 'rejete', 'signe', 'renvoye'}
        terminees = sum(1 for a in affectations if a.statut in statuts_termines)
        return {
            'total': total,
            'terminees': terminees,
            'pourcentage': round(terminees / total * 100),
        }


class CircuitCreateSerializer(serializers.Serializer):
    """
    Serializer pour créer un circuit complet en une seule requête.

    Payload attendu :
    {
        "courrier": <id>,
        "type_circuit": "simultane" | "sequentiel",
        "titre": "...",                          (optionnel)
        "instructions_generales": "...",         (optionnel)
        "affectations": [
            {
                "destinataire": <user_id>,
                "service": <service_id>,         (optionnel)
                "action_requise": "a_signer",
                "note_instruction": "Veuillez signer ce courrier avant le ...",
                "niveau_urgence": "eleve",
                "date_echeance": "2026-04-10T17:00:00Z",
                "etape_numero": 1,               (1 pour tous en simultané)
                "metadata": {}
            },
            ...
        ]
    }
    """
    courrier = serializers.PrimaryKeyRelatedField(
        queryset=__import__('documents.models', fromlist=['Courrier']).Courrier.objects.all()
    )
    type_circuit = serializers.ChoiceField(choices=Circuit.TYPE_CHOICES, default='simultane')
    titre = serializers.CharField(max_length=255, required=False, allow_blank=True)
    instructions_generales = serializers.CharField(required=False, allow_blank=True)
    affectations = AffectationWriteSerializer(many=True)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_affectations(self, affectations):
        if not affectations:
            raise serializers.ValidationError("Un circuit doit contenir au moins une affectation.")
        
        # Valider que chaque affectation a au moins un service
        for aff in affectations:
            if not aff.get('service'):
                raise serializers.ValidationError("Chaque affectation doit avoir un service.")
        
        return affectations

    def create(self, validated_data):
        from users.models import Notification
        
        affectations_data = validated_data.pop('affectations')
        request = self.context.get('request')
        user = request.user if request else None

        circuit = Circuit.objects.create(cree_par=user, **validated_data)

        for aff_data in affectations_data:
            service = aff_data.get('service')
            destinataire = aff_data.pop('destinataire', None)
            
            if destinataire:
                # Affectation à un utilisateur spécifique
                affectation = Affectation.objects.create(
                    circuit=circuit,
                    courrier=circuit.courrier,
                    affecte_par=user,
                    destinataire=destinataire,
                    **aff_data,
                )
                
                # Créer une notification pour le destinataire
                Notification.objects.create(
                    utilisateur=destinataire,
                    type='courrier_affecte',
                    titre=f'Nouveau courrier affecté : {circuit.courrier.numero_registre}',
                    message=f'Le courrier "{circuit.courrier.objet}" vous a été affecté. Action requise : {affectation.get_action_requise_display()}',
                    courrier_id=circuit.courrier.id,
                )
            else:
                # Affectation à tous les utilisateurs du service
                users_in_service = User.objects.filter(service=service, is_active=True)
                
                if not users_in_service.exists():
                    raise serializers.ValidationError(
                        f"Aucun utilisateur actif trouvé pour le service {service.nom}"
                    )
                
                for user_dest in users_in_service:
                    affectation = Affectation.objects.create(
                        circuit=circuit,
                        courrier=circuit.courrier,
                        affecte_par=user,
                        destinataire=user_dest,
                        service=service,
                        **aff_data,
                    )
                    
                    # Créer une notification pour chaque destinataire
                    Notification.objects.create(
                        utilisateur=user_dest,
                        type='courrier_affecte',
                        titre=f'Nouveau courrier affecté : {circuit.courrier.numero_registre}',
                        message=f'Le courrier "{circuit.courrier.objet}" a été affecté à votre service ({service.nom}). Action requise : {affectation.get_action_requise_display()}',
                        courrier_id=circuit.courrier.id,
                    )

        return circuit
