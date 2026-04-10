from rest_framework import serializers
from .models import (
    Document, DocumentVersion, DocumentShare, ShareRequest, 
    Courrier, PartageLog, Categorie, AffectationCourrier, CommentaireCourrier,
    CourrierPieceJointe, ActionLog
)
from users.models import User, Service
from tags.serializers import TagSerializer


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


class DocumentShareSerializer(serializers.ModelSerializer):
    shared_with_username = serializers.ReadOnlyField(source='shared_with.username')
    shared_with_email = serializers.ReadOnlyField(source='shared_with.email')
    shared_by_username = serializers.ReadOnlyField(source='shared_by.username')
    
    class Meta:
        model = DocumentShare
        fields = ['id', 'document', 'shared_with', 'shared_with_username', 'shared_with_email', 
                  'shared_by', 'shared_by_username', 'permission', 'shared_at']
        read_only_fields = ['shared_by', 'shared_at']


class ShareRequestSerializer(serializers.ModelSerializer):
    requested_by_username = serializers.ReadOnlyField(source='requested_by.username')
    requested_by_email = serializers.ReadOnlyField(source='requested_by.email')
    reviewed_by_username = serializers.ReadOnlyField(source='reviewed_by.username')
    document_title = serializers.ReadOnlyField(source='document.title')
    document_owner = serializers.ReadOnlyField(source='document.owner.username')
    document_owner_id = serializers.ReadOnlyField(source='document.owner.id')
    
    class Meta:
        model = ShareRequest
        fields = ['id', 'document', 'document_title', 'document_owner', 'document_owner_id',
                  'requested_by', 'requested_by_username', 'requested_by_email',
                  'requested_permission', 'status', 'message', 'rejection_count',
                  'created_at', 'reviewed_at', 'reviewed_by', 'reviewed_by_username']
        read_only_fields = ['requested_by', 'created_at', 'reviewed_at', 'reviewed_by', 'rejection_count']


class DocumentSerializer(serializers.ModelSerializer):
    owner_name = serializers.ReadOnlyField(source='owner.username') # Pour afficher le nom au lieu de l'ID
    folder_name = serializers.ReadOnlyField(source='folder.name') # Pour afficher le nom du dossier
    tag_list = TagSerializer(source='tags', many=True, read_only=True)  # Afficher les détails des tags
    shares = DocumentShareSerializer(many=True, read_only=True)
    shared_with_count = serializers.SerializerMethodField()
    has_access = serializers.SerializerMethodField()
    has_pending_request = serializers.SerializerMethodField()
    access_request_status = serializers.SerializerMethodField()
    access_request_rejection_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ('owner', 'created_at', 'updated_at')
    
    def get_shared_with_count(self, obj):
        """Retourne le nombre d'utilisateurs avec qui le document est partagé"""
        return obj.shares.count()
    
    def get_has_access(self, obj):
        """Indique si l'utilisateur actuel a accès au document"""
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        user = request.user
        # L'utilisateur a accès si:
        # - Il est propriétaire
        # - Il est administrateur
        # - Le document est public
        # - Le document est partagé avec lui
        return (
            obj.owner == user or 
            user.role == 'admin' or
            obj.visibility == 'public' or 
            obj.shares.filter(shared_with=user).exists()
        )
    
    def get_has_pending_request(self, obj):
        """Indique si l'utilisateur a déjà une demande d'accès en attente pour ce document"""
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


class AffectationCourrierSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple pour afficher les affectations dans les détails d'un courrier"""
    utilisateur_username = serializers.CharField(source='utilisateur.username', read_only=True)
    utilisateur_nom_complet = serializers.SerializerMethodField()
    utilisateur_service = serializers.CharField(source='utilisateur.service.nom', read_only=True, allow_null=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    action_requise_display = serializers.CharField(source='get_action_requise_display', read_only=True)
    niveau_urgence_display = serializers.CharField(source='get_niveau_urgence_display', read_only=True)
    circuit_id = serializers.IntegerField(source='circuit.id', read_only=True, allow_null=True)
    peut_etre_traitee = serializers.SerializerMethodField()

    class Meta:
        model = AffectationCourrier
        fields = [
            'id', 'utilisateur', 'utilisateur_username', 'utilisateur_nom_complet',
            'utilisateur_service', 'statut', 'statut_display', 'action_requise',
            'action_requise_display', 'niveau_urgence', 'niveau_urgence_display',
            'date_echeance', 'note', 'date_affectation', 'date_lecture', 'date_traitement',
            'circuit_id', 'etape_numero', 'peut_etre_traitee',
        ]

    def get_utilisateur_nom_complet(self, obj):
        if obj.utilisateur.first_name and obj.utilisateur.last_name:
            return f"{obj.utilisateur.first_name} {obj.utilisateur.last_name}"
        return obj.utilisateur.username

    def get_peut_etre_traitee(self, obj):
        return obj.peut_etre_traitee()


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
    
    # Affectations de l'ancien système (système simple utilisateur par utilisateur)
    affectations_list = AffectationCourrierSimpleSerializer(source='affectations', many=True, read_only=True)
    
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
            'affectations_list',
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
        # Si le courrier a un circuit, calculer le statut basé sur le circuit
        try:
            if hasattr(obj, 'circuit_affectation') and obj.circuit_affectation:
                affectations_service = obj.circuit_affectation.affectations_service.all()
                
                if not affectations_service.exists():
                    return None
                
                # Compter le nombre d'affectations vues/traitées
                nb_vues = affectations_service.filter(
                    statut__in=['vu', 'en_traitement', 'valide', 'signe']
                ).count()
                
                # Si toutes sont terminées (validées ou signées)
                nb_terminees = affectations_service.filter(
                    statut__in=['valide', 'signe']
                ).count()
                
                if nb_terminees == affectations_service.count():
                    return 'traite'
                elif nb_vues > 0:
                    return 'distribue'  # On retourne 'distribue' avec le compteur dans display
                else:
                    return 'distribue'
        except:
            pass
        
        # Sinon, utiliser l'ancien système (AffectationCourrier)
        latest = obj.affectations.first()  # trié par -date_affectation
        return latest.statut if latest else None

    def get_derniere_affectation_statut_display(self, obj):
        """Retourne le libellé du statut de la dernière affectation"""
        # Si le courrier a un circuit, calculer le libellé basé sur le circuit
        try:
            if hasattr(obj, 'circuit_affectation') and obj.circuit_affectation:
                affectations_service = obj.circuit_affectation.affectations_service.all()
                
                if not affectations_service.exists():
                    return None
                
                # Compter le nombre d'affectations vues/traitées
                nb_vues = affectations_service.filter(
                    statut__in=['vu', 'en_traitement', 'valide', 'signe']
                ).count()
                
                # Si toutes sont terminées (validées ou signées)
                nb_terminees = affectations_service.filter(
                    statut__in=['valide', 'signe']
                ).count()
                
                total = affectations_service.count()
                
                if nb_terminees == total:
                    return 'Traité'
                elif nb_vues > 0:
                    return f'Distribué ({nb_vues})'
                else:
                    return 'Distribué'
        except:
            pass
        
        # Sinon, utiliser l'ancien système (AffectationCourrier)
        latest = obj.affectations.first()
        return latest.get_statut_display() if latest else None

    def get_derniere_affectation_echeance(self, obj):
        """Retourne la date d'échéance de la dernière affectation"""
        # Pour les circuits, ne pas afficher d'échéance (chaque service peut avoir la sienne)
        try:
            if hasattr(obj, 'circuit_affectation') and obj.circuit_affectation:
                return None
        except:
            pass
        
        # Ancien système
        latest = obj.affectations.first()
        return latest.date_echeance.isoformat() if latest and latest.date_echeance else None

    def get_derniere_affectation_action_requise(self, obj):
        """Retourne l'action requise de la dernière affectation"""
        # Pour les circuits, ne pas afficher d'action (chaque service peut avoir la sienne)
        try:
            if hasattr(obj, 'circuit_affectation') and obj.circuit_affectation:
                return None
        except:
            pass
        
        # Ancien système
        latest = obj.affectations.first()
        return latest.action_requise if latest else None

    def get_derniere_affectation_action_requise_display(self, obj):
        """Retourne le libellé de l'action requise de la dernière affectation"""
        # Pour les circuits, ne pas afficher d'action (chaque service peut avoir la sienne)
        try:
            if hasattr(obj, 'circuit_affectation') and obj.circuit_affectation:
                return None
        except:
            pass
        
        # Ancien système
        latest = obj.affectations.first()
        return latest.get_action_requise_display() if latest else None

    def get_a_circuit(self, obj):
        """Retourne True si le courrier a un circuit d'affectation"""
        try:
            return hasattr(obj, 'circuit_affectation') and obj.circuit_affectation is not None
        except:
            return False

    def get_nombre_affectations_circuit(self, obj):
        """Retourne le nombre d'affectations de service dans le circuit"""
        try:
            if hasattr(obj, 'circuit_affectation') and obj.circuit_affectation:
                return obj.circuit_affectation.affectations_service.count()
            return 0
        except:
            return 0

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
            'date_envoi',
            'expediteur',
            'destinataire',
            'objet',
            'reference',
            'reference_structure',
            'categorie',
            'service_concerne',
            'statut',
            'fichier',
            'notes',
            'reponse_a',
            'contenu_lettre',
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


# ============================================================================
# SERIALIZERS POUR LES AFFECTATIONS DE COURRIERS
# ============================================================================

class AffectationCourrierSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les affectations de courriers
    """
    # Informations sur le courrier
    courrier_details = CourrierSerializer(source='courrier', read_only=True)
    courrier_numero = serializers.CharField(source='courrier.numero_registre', read_only=True)
    courrier_objet = serializers.CharField(source='courrier.objet', read_only=True)
    
    # Informations sur l'utilisateur affecté
    utilisateur_username = serializers.CharField(source='utilisateur.username', read_only=True)
    utilisateur_nom_complet = serializers.SerializerMethodField()
    utilisateur_service = serializers.CharField(source='utilisateur.service.nom', read_only=True)
    
    # Informations sur qui a fait l'affectation
    affecte_par_username = serializers.CharField(source='affecte_par.username', read_only=True)
    affecte_par_nom_complet = serializers.SerializerMethodField()
    
    # Statut avec libellé
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    # Action requise avec libellé
    action_requise_display = serializers.CharField(source='get_action_requise_display', read_only=True)

    # Niveau d'urgence avec libellé
    niveau_urgence_display = serializers.CharField(source='get_niveau_urgence_display', read_only=True)
    
    # Compteurs
    nb_commentaires = serializers.SerializerMethodField()
    
    class Meta:
        model = AffectationCourrier
        fields = [
            'id',
            'courrier',
            'courrier_details',
            'courrier_numero',
            'courrier_objet',
            'utilisateur',
            'utilisateur_username',
            'utilisateur_nom_complet',
            'utilisateur_service',
            'affecte_par',
            'affecte_par_username',
            'affecte_par_nom_complet',
            'note',
            'statut',
            'statut_display',
            'action_requise',
            'action_requise_display',
            'niveau_urgence',
            'niveau_urgence_display',
            'date_echeance',
            'commentaire_traitement',
            'motif_rejet',
            'nb_commentaires',
            'date_affectation',
            'date_lecture',
            'date_traitement',
        ]
        read_only_fields = [
            'affecte_par',
            'date_affectation',
            'date_lecture',
            'date_traitement'
        ]
    
    def get_utilisateur_nom_complet(self, obj):
        """Retourne le nom complet de l'utilisateur affecté"""
        if obj.utilisateur.first_name and obj.utilisateur.last_name:
            return f"{obj.utilisateur.first_name} {obj.utilisateur.last_name}"
        return obj.utilisateur.username
    
    def get_affecte_par_nom_complet(self, obj):
        """Retourne le nom complet de celui qui a fait l'affectation"""
        if not obj.affecte_par:
            return None
        if obj.affecte_par.first_name and obj.affecte_par.last_name:
            return f"{obj.affecte_par.first_name} {obj.affecte_par.last_name}"
        return obj.affecte_par.username
    
    def get_nb_commentaires(self, obj):
        """Retourne le nombre de commentaires sur cette affectation"""
        return obj.commentaires.count()


class AffectationCourrierCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer une nouvelle affectation
    """
    class Meta:
        model = AffectationCourrier
        fields = [
            'courrier',
            'utilisateur',
            'note'
        ]


class CommentaireCourrierSerializer(serializers.ModelSerializer):
    """
    Serializer pour les commentaires sur les affectations
    """
    auteur_username = serializers.CharField(source='auteur.username', read_only=True)
    auteur_nom_complet = serializers.SerializerMethodField()
    
    class Meta:
        model = CommentaireCourrier
        fields = [
            'id',
            'affectation',
            'auteur',
            'auteur_username',
            'auteur_nom_complet',
            'contenu',
            'date_creation'
        ]
        read_only_fields = ['auteur', 'date_creation']
    
    def get_auteur_nom_complet(self, obj):
        """Retourne le nom complet de l'auteur du commentaire"""
        if obj.auteur.first_name and obj.auteur.last_name:
            return f"{obj.auteur.first_name} {obj.auteur.last_name}"
        return obj.auteur.username


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
            'document',
            'document_nom',
            'affectation',
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
            'document_nom',
        ]
    
    def get_utilisateur_info(self, obj):
        """Retourne les infos de l'utilisateur en format compact"""
        return {
            'id': obj.utilisateur.id if obj.utilisateur else None,
            'username': obj.utilisateur_username,
            'nom_complet': obj.utilisateur_nom_complet,
        }
