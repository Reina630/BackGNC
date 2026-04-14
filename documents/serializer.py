from rest_framework import serializers
from .models import (
    Courrier, PartageLog, Categorie,
    CourrierPieceJointe, ActionLog
)
from users.models import User, Service


# ============================================================================
# SERIALIZERS POUR LES CATÉGORIES DE COURRIER
# ============================================================================

class CategorieSerializer(serializers.ModelSerializer):
    """
    Serializer pour les catégories de courriers.
    """
    courriers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Categorie
        fields = ['id', 'name', 'description', 'courriers_count', 'created_at']
        read_only_fields = ['created_at']
    
    def get_courriers_count(self, obj):
        """Retourne le nombre de courriers dans cette catégorie"""
        return obj.courriers.count()
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        return obj.access_requests.filter(
            requested_by=request.user,
            status='pending'
        ).exists()
    
    def get_access_request_status(self, obj):
        """Retourne le statut de la dernière demande d'accès de l'utilisateur pour ce document"""
        request = self.context.get('request')
        if not request or not request.user:
            return None
        
        last_request = obj.access_requests.filter(
            requested_by=request.user
        ).order_by('-created_at').first()
        
    
    def get_access_request_rejection_count(self, obj):
        """Retourne le nombre de rejets de la demande d'accès de l'utilisateur"""
        request = self.context.get('request')
        if not request or not request.user:
            return 0
        
        last_request = obj.access_requests.filter(
            requested_by=request.user
        ).order_by('-created_at').first()
        
        return last_request.rejection_count if last_request else 0
        return last_request.status if last_request else None


class UserSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple pour lister les utilisateurs disponibles pour le partage"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ServiceSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple pour les services"""
    class Meta:
        model = Service
        fields = ['id', 'nom', 'description']


class AffectationV2SimpleSerializer(serializers.Serializer):
    """Serializer simple pour les affectations v2 (pour inclusion dans Courrier)"""
    id = serializers.SerializerMethodField()
    circuit = serializers.SerializerMethodField()
    destinataire = serializers.SerializerMethodField()
    destinataire_nom = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    service_nom = serializers.SerializerMethodField()
    action_requise = serializers.CharField(read_only=True)
    niveau_urgence = serializers.CharField(read_only=True)
    statut = serializers.CharField(read_only=True)
    date_echeance = serializers.DateTimeField(allow_null=True, read_only=True)
    date_traitement = serializers.DateTimeField(allow_null=True, read_only=True)
    etape_numero = serializers.IntegerField(read_only=True)
    peut_traiter = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.id

    def get_circuit(self, obj):
        return obj.circuit.id if obj.circuit else None

    def get_destinataire(self, obj):
        return obj.destinataire.id if obj.destinataire else None

    def get_destinataire_nom(self, obj):
        if obj.destinataire:
            return obj.destinataire.get_full_name() or obj.destinataire.username
        return None

    def get_service(self, obj):
        return obj.service.id if obj.service else None

    def get_service_nom(self, obj):
        return obj.service.nom if obj.service else None

    def get_peut_traiter(self, obj):
        return obj.peut_etre_traitee()


# ============================================================================
# SERIALIZERS POUR LE REGISTRE DE COURRIER
# ============================================================================

class CourrierPieceJointeSerializer(serializers.ModelSerializer):
    fichier_url = serializers.SerializerMethodField()

    class Meta:
        model = CourrierPieceJointe
        fields = ['id', 'fichier', 'fichier_url', 'nom_fichier', 'file_type', 'file_size', 'created_at']
        read_only_fields = ['id', 'file_size', 'created_at']

    def get_fichier_url(self, obj):
        if obj.fichier:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.fichier.url)
            return obj.fichier.url
        return None


class CourrierSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Courrier.
    Inclut les informations détaillées et les champs calculés.
    """
    # Ajouter les noms lisibles pour les choix
    type_courrier_display = serializers.CharField(source='get_type_courrier_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    service_concerne_display = serializers.CharField(source='get_service_concerne_display', read_only=True)
    mode_reception_display = serializers.CharField(source='get_mode_reception_display', read_only=True)
    mode_envoi_display = serializers.CharField(source='get_mode_envoi_display', read_only=True)
    service_emetteur_display = serializers.CharField(source='get_service_emetteur_display', read_only=True)
    service_destinataire_display = serializers.CharField(source='get_service_destinataire_display', read_only=True)
    
    # Informations sur l'utilisateur qui a enregistré le courrier
    enregistre_par_details = UserSimpleSerializer(source='enregistre_par', read_only=True)
    enregistre_par_nom = serializers.CharField(source='enregistre_par.username', read_only=True)
    
    # Informations sur la catégorie
    categorie_details = CategorieSerializer(source='categorie', read_only=True)
    categorie_name = serializers.CharField(source='categorie.name', read_only=True)
    
    # Date principale (date_reception pour entrant, date_envoi pour sortant)
    date_principale = serializers.SerializerMethodField()
    
    # URL complète du fichier
    fichier_url = serializers.SerializerMethodField()
    
    # Pièces jointes multiples
    pieces_jointes = CourrierPieceJointeSerializer(many=True, read_only=True)
    
    # Gestion des versions
    version_label = serializers.SerializerMethodField()
    nombre_versions = serializers.SerializerMethodField()
    courrier_parent_numero = serializers.CharField(source='courrier_parent.numero_registre', read_only=True)

    # Informations sur le courrier "en réponse à"
    reponse_a_numero = serializers.CharField(source='reponse_a.numero_registre', read_only=True)
    reponse_a_objet = serializers.CharField(source='reponse_a.objet', read_only=True)

    # Dernière affectation (statut de traitement)
    derniere_affectation_statut = serializers.SerializerMethodField()
    derniere_affectation_statut_display = serializers.SerializerMethodField()
    derniere_affectation_echeance = serializers.SerializerMethodField()
    derniere_affectation_action_requise = serializers.SerializerMethodField()
    derniere_affectation_action_requise_display = serializers.SerializerMethodField()
    
    # Informations sur le circuit d'affectation
    a_circuit = serializers.SerializerMethodField()
    nombre_affectations_circuit = serializers.SerializerMethodField()
    
    # Affectations du nouveau système v2 (circuits)
    affectations_v2 = serializers.SerializerMethodField()
    
    class Meta:
        model = Courrier
        fields = [
            'id',
            'numero_registre',
            'type_courrier',
            'type_courrier_display',
            'date_reception',
            'mode_reception',
            'mode_reception_display',
            'date_envoi',
            'mode_envoi',
            'mode_envoi_display',
            'date_circulation',
            'date_principale',
            'expediteur',
            'destinataire',
            'service_emetteur',
            'service_emetteur_display',
            'service_destinataire',
            'service_destinataire_display',
            'objet',
            'reference',
            'reference_structure',
            'categorie',
            'categorie_name',
            'categorie_details',
            'service_concerne',
            'service_concerne_display',
            'statut',
            'statut_display',
            'fichier',
            'fichier_url',
            'file_type',
            'file_size',
            'pieces_jointes',
            'notes',
            'urgent',
            'enregistre_par',
            'enregistre_par_nom',
            'enregistre_par_details',
            # Champs de version
            'courrier_parent',
            'courrier_parent_numero',
            'version_number',
            'version_label',
            'est_version_actuelle',
            'nombre_versions',
            # Champs de réponse
            'reponse_a',
            'reponse_a_numero',
            'reponse_a_objet',
            'contenu_lettre',
            # Statut de la dernière affectation
            'derniere_affectation_statut',
            'derniere_affectation_statut_display',
            'derniere_affectation_echeance',
            'derniere_affectation_action_requise',
            'derniere_affectation_action_requise_display',
            # Informations sur le circuit d'affectation
            'a_circuit',
            'nombre_affectations_circuit',
            'affectations_v2',
            'created_at',
            'updated_at'
        ]
        # Ces champs ne peuvent pas être modifiés par l'utilisateur
        read_only_fields = [
            'id',
            'numero_registre',
            'created_at',
            'updated_at',
            'enregistre_par',
            'file_size'
        ]
    
    def get_date_principale(self, obj):
        """
        Retourne la date principale du courrier selon son type.
        Pour un courrier entrant : date de réception.
        Pour un courrier sortant : date d'envoi.
        """
        date = obj.get_date_principale()
        return date.isoformat() if date else None
    
    def get_fichier_url(self, obj):
        """
        Retourne l'URL complète du fichier
        """
        if obj.fichier:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.fichier.url)
            return obj.fichier.url
        return None
    
    def get_version_label(self, obj):
        """Retourne le label de version (V1, V2, V3...)"""
        return obj.get_version_label()
    
    def get_nombre_versions(self, obj):
        """Retourne le nombre total de versions de ce courrier"""
        if obj.courrier_parent:
            return obj.courrier_parent.versions.count() + 1
        else:
            return obj.versions.count() + 1

    def get_derniere_affectation_statut(self, obj):
        """Retourne le statut de la dernière affectation active"""
        # Utiliser le nouveau système v2
        latest = obj.affectations_v2.first()  # trié par -date_affectation
        return latest.statut if latest else None

    def get_derniere_affectation_statut_display(self, obj):
        """Retourne le libellé du statut de la dernière affectation"""
        # Utiliser le nouveau système v2
        latest = obj.affectations_v2.first()
        return latest.get_statut_display() if latest else None

    def get_derniere_affectation_echeance(self, obj):
        """Retourne la date d'échéance de la dernière affectation"""
        # Nouveau système v2
        latest = obj.affectations_v2.first()
        return latest.date_echeance.isoformat() if latest and latest.date_echeance else None

    def get_derniere_affectation_action_requise(self, obj):
        """Retourne l'action requise de la dernière affectation"""
        # Nouveau système v2
        latest = obj.affectations_v2.first()
        return latest.action_requise if latest else None

    def get_derniere_affectation_action_requise_display(self, obj):
        """Retourne le libellé de l'action requise de la dernière affectation"""
        # Nouveau système v2
        latest = obj.affectations_v2.first()
        return latest.get_action_requise_display() if latest else None

    def get_a_circuit(self, obj):
        """Retourne True si le courrier a un circuit d'affectation"""
        return obj.circuits_v2.exists()

    def get_nombre_affectations_circuit(self, obj):
        """Retourne le nombre total d'affectations dans tous les circuits"""
        return obj.affectations_v2.count()

    def get_affectations_v2(self, obj):
        """Retourne les affectations du circuit v2 si elles existent"""
        try:
            # Récupérer le circuit v2 (related_name='circuits_v2')
            circuit = obj.circuits_v2.first()
            if circuit:
                # Récupérer toutes les affectations du circuit (related_name='affectations')
                affectations = circuit.affectations.select_related(
                    'destinataire', 'service'
                ).all()
                return AffectationV2SimpleSerializer(affectations, many=True).data
            return []
        except Exception as e:
            # Log l'erreur mais ne pas casser la sérialisation
            print(f"Erreur get_affectations_v2: {e}")
            return []


class CourrierCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'un nouveau courrier.
    Simplifié pour ne demander que les champs essentiels.
    """
    class Meta:
        model = Courrier
        fields = [
            'type_courrier',
            'date_reception',
            'mode_reception',
            'date_envoi',
            'mode_envoi',
            'date_circulation',
            'expediteur',
            'destinataire',
            'service_emetteur',
            'service_destinataire',
            'objet',
            'reference',
            'reference_structure',
            'categorie',
            'service_concerne',
            'statut',
            'fichier',
            'notes',
            'reponse_a',
            'urgent',
        ]
    
    def validate(self, data):
        """
        Validation personnalisée pour s'assurer que:
        - Un courrier entrant a une date de réception
        - Un courrier sortant a une date d'envoi (sauf brouillon)
        """
        type_courrier = data.get('type_courrier')
        date_reception = data.get('date_reception')
        date_envoi = data.get('date_envoi')
        statut = data.get('statut', 'recu')
        
        if type_courrier == 'entrant' and not date_reception:
            raise serializers.ValidationError({
                'date_reception': 'La date de réception est obligatoire pour un courrier entrant.'
            })
        
        # Les brouillons sortants peuvent être enregistrés sans date d'envoi définitive
        if type_courrier == 'sortant' and not date_envoi and statut != 'brouillon':
            raise serializers.ValidationError({
                'date_envoi': "La date d'envoi est obligatoire pour un courrier sortant."
            })
        
        return data


class CourrierUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour d'un courrier existant.
    Les champs essentiels peuvent être modifiés sauf le numéro de registre.
    Le fichier peut également être remplacé.
    """
    class Meta:
        model = Courrier
        fields = [
            'type_courrier',
            'date_reception',
            'date_envoi',
            'expediteur',
            'destinataire',
            'objet',
            'reference',
            'reference_structure',
            'categorie',
            'service_concerne',
            'statut',
            'notes',
            'fichier'
        ]


# ===== PARTAGE DE COURRIERS =====

class UserSimpleSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les utilisateurs"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']


class PartageLogSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'historique des partages de courriers
    """
    # Informations sur le courrier partagé
    courrier_numero = serializers.ReadOnlyField(source='courrier.numero_registre')
    courrier_objet = serializers.ReadOnlyField(source='courrier.objet')
    courrier_type = serializers.ReadOnlyField(source='courrier.type_courrier')
    courrier_type_display = serializers.ReadOnlyField(source='courrier.get_type_courrier_display')
    
    # Informations sur l'utilisateur qui a partagé
    partage_par_nom = serializers.ReadOnlyField(source='partage_par.username')
    partage_par_email = serializers.ReadOnlyField(source='partage_par.email')
    partage_par_details = UserSimpleSerializer(source='partage_par', read_only=True)
    
    # Display pour le type de partage
    type_partage_display = serializers.ReadOnlyField(source='get_type_partage_display')
    
    class Meta:
        model = PartageLog
        fields = [
            'id',
            'courrier',
            'courrier_numero',
            'courrier_objet',
            'courrier_type',
            'courrier_type_display',
            'type_partage',
            'type_partage_display',
            'destinataire',
            'message',
            'partage_par',
            'partage_par_nom',
            'partage_par_email',
            'partage_par_details',
            'created_at',
        ]
        read_only_fields = ['partage_par', 'created_at']


class PartageLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer un nouveau partage
    """
    class Meta:
        model = PartageLog
        fields = [
            'courrier',
            'type_partage',
            'destinataire',
            'message',
        ]
    
    def validate_type_partage(self, value):
        """Valider que le type de partage est valide"""
        if value not in ['email', 'whatsapp']:
            raise serializers.ValidationError("Type de partage invalide. Utilisez 'email' ou 'whatsapp'.")
        return value
    
    def validate_destinataire(self, value):
        """Valider le format du destinataire selon le type"""
        if not value or not value.strip():
            raise serializers.ValidationError("Le destinataire est obligatoire.")
        return value.strip()



class ServiceSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple pour les services
    """
    nb_utilisateurs = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = ['id', 'nom', 'description', 'nb_utilisateurs']
    
    def get_nb_utilisateurs(self, obj):
        """Retourne le nombre d'utilisateurs dans ce service"""
        return obj.utilisateurs.count()


# ============================================================================
# SERIALIZERS POUR LES LOGS D'ACTIONS (AUDIT)
# ============================================================================

class ActionLogSerializer(serializers.ModelSerializer):
    """
    Serializer pour les logs d'actions (journal d'audit)
    """
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    utilisateur_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ActionLog
        fields = [
            'id',
            'action_type',
            'action_type_display',
            'description',
            'utilisateur',
            'utilisateur_username',
            'utilisateur_nom_complet',
            'utilisateur_info',
            'courrier',
            'courrier_numero',
            'timestamp',
            'ip_address',
            'metadata',
        ]
        read_only_fields = [
            'id',
            'timestamp',
            'utilisateur_username',
            'utilisateur_nom_complet',
            'courrier_numero',
        ]
    
    def get_utilisateur_info(self, obj):
        """Retourne les infos de l'utilisateur en format compact"""
        return {
            'id': obj.utilisateur.id if obj.utilisateur else None,
            'username': obj.utilisateur_username,
            'nom_complet': obj.utilisateur_nom_complet,
        }
