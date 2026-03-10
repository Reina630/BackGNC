from rest_framework import serializers
from .models import (
    Document, DocumentVersion, DocumentShare, ShareRequest, 
    Courrier, PartageLog, Categorie, AffectationCourrier, CommentaireCourrier
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


# ============================================================================
# SERIALIZERS POUR LE REGISTRE DE COURRIER
# ============================================================================

class CourrierSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Courrier.
    Inclut les informations détaillées et les champs calculés.
    """
    # Ajouter les noms lisibles pour les choix
    type_courrier_display = serializers.CharField(source='get_type_courrier_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    service_concerne_display = serializers.CharField(source='get_service_concerne_display', read_only=True)
    
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
    
    # Gestion des versions
    version_label = serializers.SerializerMethodField()
    nombre_versions = serializers.SerializerMethodField()
    courrier_parent_numero = serializers.CharField(source='courrier_parent.numero_registre', read_only=True)
    
    class Meta:
        model = Courrier
        fields = [
            'id',
            'numero_registre',
            'type_courrier',
            'type_courrier_display',
            'date_reception',
            'date_envoi',
            'date_principale',
            'expediteur',
            'destinataire',
            'objet',
            'reference',
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
            # Si c'est une version, compter les versions du parent + le parent
            return obj.courrier_parent.versions.count() + 1
        else:
            # Si c'est le parent, compter ses versions + lui-même
            return obj.versions.count() + 1


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
            'categorie',
            'service_concerne',
            'statut',
            'fichier',
            'notes'
        ]
    
    def validate(self, data):
        """
        Validation personnalisée pour s'assurer que:
        - Un courrier entrant a une date de réception
        - Un courrier sortant a une date d'envoi
        """
        type_courrier = data.get('type_courrier')
        date_reception = data.get('date_reception')
        date_envoi = data.get('date_envoi')
        
        if type_courrier == 'entrant' and not date_reception:
            raise serializers.ValidationError({
                'date_reception': 'La date de réception est obligatoire pour un courrier entrant.'
            })
        
        if type_courrier == 'sortant' and not date_envoi:
            raise serializers.ValidationError({
                'date_envoi': "La date d'envoi est obligatoire pour un courrier sortant."
            })
        
        return data


class CourrierUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour d'un courrier existant.
    Les champs essentiels peuvent être modifiés sauf le numéro de registre.
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
            'categorie',
            'service_concerne',
            'statut',
            'notes'
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
