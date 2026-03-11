from django.db import models
from folders.models import Folder
from users.models import User
from tags.models import Tag


class Categorie(models.Model):
    """
    Modèle pour les catégories de courriers (devis, demande, facture, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, help_text="Description de la catégorie")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
    
    def __str__(self):
        return self.name


class Document(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('word', 'Word'),
        ('excel', 'Excel'),
        ('ppt', 'PowerPoint'),
        ('image', 'Image'),
        ('scan', 'Scan'),
    ]

    VISIBILITY_CHOICES = [
        ('private', 'Privé'),
        ('shared', 'Partagé'),
        ('public', 'Public'),
    ]

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_size = models.BigIntegerField(default=0, help_text='Taille du fichier en octets')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    is_favorite = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, help_text='Document archivé/supprimé')
    deleted_at = models.DateTimeField(null=True, blank=True, help_text='Date de suppression/archivage')
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_documents', help_text='Utilisateur qui a supprimé le document')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def soft_delete(self, user):
        """Archiver (supprimer doucement) le document"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self):
        """Restaurer le document depuis les archives"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    file = models.FileField(upload_to='documents/versions/')
    version_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class DocumentShare(models.Model):
    """Modèle pour gérer le partage de documents avec des utilisateurs spécifiques"""
    
    PERMISSION_CHOICES = [
        ('view', 'Lecture seule'),
        ('edit', 'Lecture et modification'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='shares')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_documents')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents_shared')
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='view')
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['document', 'shared_with']
    
    def __str__(self):
        return f"{self.document.title} partagé avec {self.shared_with.username}"


class ShareRequest(models.Model):
    """Modèle pour gérer les demandes d'accès aux documents"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
    ]
    
    PERMISSION_CHOICES = [
        ('view', 'Lecture seule'),
        ('edit', 'Lecture et modification'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_requests')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_requests')
    requested_permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='view')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, help_text='Message de demande')
    rejection_count = models.IntegerField(default=0, help_text='Nombre de fois que la demande a été rejetée')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    
    class Meta:
        unique_together = ['document', 'requested_by']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requested_by.username} demande accès à {self.document.title}"


# ============================================================================
# NOUVEAU MODÈLE POUR LE REGISTRE DE COURRIER RH
# ============================================================================

class Courrier(models.Model):
    """
    Modèle pour le registre de courrier RH.
    Permet d'enregistrer et suivre les courriers entrants et sortants.
    """
    
    # Choix pour le type de courrier
    TYPE_CHOICES = [
        ('entrant', 'Courrier Entrant'),
        ('sortant', 'Courrier Sortant'),
        ('interne', 'Courrier Interne'),
    ]
    
    # Choix pour le statut de traitement
    STATUS_CHOICES = [
        ('recu', 'Reçu'),
        ('en_traitement', 'En traitement'),
        ('traite', 'Traité'),
        ('archive', 'Archivé'),
    ]
    
    # Choix pour les services concernés
    SERVICE_CHOICES = [
        ('rh', 'Ressources Humaines'),
        ('comptabilite', 'Comptabilité'),
        ('direction', 'Direction'),
        ('technique', 'Service Technique'),
        ('commercial', 'Commercial'),
        ('juridique', 'Juridique'),
        ('informatique', 'Informatique'),
        ('logistique', 'Logistique'),
        ('autre', 'Autre'),
    ]
    
    # Choix pour le mode de réception/envoi
    MODE_CHOICES = [
        ('postal', 'Courrier postal'),
        ('email', 'Email'),
        ('fax', 'Fax'),
        ('main_propre', 'Remise en main propre'),
        ('coursier', 'Coursier'),
        ('autre', 'Autre'),
    ]
    
    # ===== IDENTIFICATION =====
    # Numéro unique généré automatiquement (ex: 2026-0001, 2026-0002...)
    numero_registre = models.CharField(
        max_length=50, 
        unique=True, 
        editable=False,
        help_text="Numéro d'enregistrement généré automatiquement"
    )
    
    # ===== TYPE ET DATES =====
    type_courrier = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES,
        help_text="Type de courrier (entrant ou sortant)"
    )
    
    # Date de réception (pour courrier entrant)
    date_reception = models.DateField(
        null=True, 
        blank=True, 
        help_text="Date de réception du courrier entrant"
    )
    
    # Mode de réception (pour courrier entrant)
    mode_reception = models.CharField(
        max_length=50,
        choices=MODE_CHOICES,
        blank=True,
        default='',
        help_text="Mode de réception du courrier entrant"
    )
    
    # Date d'envoi (pour courrier sortant)
    date_envoi = models.DateField(
        null=True, 
        blank=True, 
        help_text="Date d'envoi du courrier sortant"
    )
    
    # Mode d'envoi (pour courrier sortant)
    mode_envoi = models.CharField(
        max_length=50,
        choices=MODE_CHOICES,
        blank=True,
        default='',
        help_text="Mode d'envoi du courrier sortant"
    )
    
    # Date de circulation (pour courrier interne)
    date_circulation = models.DateField(
        null=True,
        blank=True,
        help_text="Date de circulation du courrier interne"
    )
    
    # ===== PARTIES PRENANTES =====
    expediteur = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Nom ou organisation de l'expéditeur (courrier entrant)"
    )
    
    destinataire = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Nom ou organisation du destinataire (courrier sortant)"
    )
    
    # Service émetteur (pour courrier interne)
    service_emetteur = models.CharField(
        max_length=50,
        choices=SERVICE_CHOICES,
        blank=True,
        default='',
        help_text="Service émetteur (courrier interne)"
    )
    
    # Service destinataire (pour courrier interne)
    service_destinataire = models.CharField(
        max_length=50,
        choices=SERVICE_CHOICES,
        blank=True,
        default='',
        help_text="Service destinataire (courrier interne)"
    )
    
    # ===== CONTENU =====
    objet = models.CharField(
        max_length=500, 
        help_text="Objet ou sujet du courrier"
    )
    
    reference = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Référence du courrier (ex: N°123/DIR/2026)"
    )
    
    # Catégorie du courrier (devis, demande, facture, etc.)
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courriers',
        help_text="Catégorie du courrier (devis, demande, facture, etc.)"
    )
    
    # ===== SERVICE ET TRAITEMENT =====
    service_concerne = models.CharField(
        max_length=50, 
        choices=SERVICE_CHOICES, 
        blank=True,
        help_text="Service concerné par ce courrier"
    )
    
    statut = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='recu',
        help_text="Statut de traitement du courrier"
    )
    
    # ===== FICHIER SCANNÉ =====
    fichier = models.FileField(
        upload_to='courriers/%Y/%m/',
        help_text="Fichier scanné du courrier (PDF, image, etc.)"
    )
    
    file_type = models.CharField(
        max_length=20, 
        default='pdf',
        help_text="Type de fichier"
    )
    
    file_size = models.BigIntegerField(
        default=0,
        help_text="Taille du fichier en octets"
    )
    
    # ===== NOTES ET OBSERVATIONS =====
    notes = models.TextField(
        blank=True, 
        help_text="Notes internes ou observations"
    )
    
    # ===== MARQUAGE URGENT =====
    urgent = models.BooleanField(
        default=False,
        help_text="Marquer ce courrier comme urgent/prioritaire"
    )
    
    # ===== GESTION DES VERSIONS =====
    # Courrier parent pour créer une hiérarchie de versions
    courrier_parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='versions',
        help_text="Courrier parent pour les versions successives"
    )
    
    # Numéro de version (1, 2, 3...)
    version_number = models.IntegerField(
        default=1,
        help_text="Numéro de version du courrier"
    )
    
    # Est-ce la version actuelle/active ?
    est_version_actuelle = models.BooleanField(
        default=True,
        help_text="Indique si c'est la version active du courrier"
    )
    
    # ===== MÉTADONNÉES =====
    # Utilisateur qui a enregistré le courrier (normalement la RH)
    enregistre_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='courriers_enregistres',
        help_text="Utilisateur ayant enregistré ce courrier"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date et heure d'enregistrement"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date et heure de dernière modification"
    )
    
    # ===== ARCHIVAGE (SOFT DELETE) =====
    is_deleted = models.BooleanField(default=False, help_text='Courrier archivé/supprimé')
    deleted_at = models.DateTimeField(null=True, blank=True, help_text='Date de suppression')
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_courriers', help_text='Utilisateur qui a supprimé le courrier')
    
    class Meta:
        ordering = ['-created_at']  # Tri par date décroissante (plus récent en premier)
        verbose_name = "Courrier"
        verbose_name_plural = "Courriers"
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['numero_registre']),
            models.Index(fields=['type_courrier', 'statut']),
        ]
    
    def save(self, *args, **kwargs):
        """
        Surcharge de la méthode save pour générer automatiquement
        le numéro de registre au format ANNÉE-NNNN
        """
        if not self.numero_registre:
            from django.utils import timezone
            year = timezone.now().year
            
            # Compter les courriers de l'année en cours
            last_courrier = Courrier.objects.filter(
                numero_registre__startswith=f"{year}-"
            ).order_by('-numero_registre').first()
            
            if last_courrier:
                # Extraire le numéro et incrémenter
                last_number = int(last_courrier.numero_registre.split('-')[1])
                new_number = last_number + 1
            else:
                # Premier courrier de l'année
                new_number = 1
            
            # Générer le numéro avec padding (ex: 2026-0001)
            self.numero_registre = f"{year}-{new_number:04d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_registre} - {self.objet[:50]}"
    
    def get_date_principale(self):
        """
        Retourne la date principale du courrier
        (date de réception pour entrant, date d'envoi pour sortant, date de circulation pour interne)
        """
        if self.type_courrier == 'entrant':
            return self.date_reception
        elif self.type_courrier == 'sortant':
            return self.date_envoi
        else:  # interne
            return self.date_circulation
    
    def get_version_label(self):
        """
        Retourne le label de version (ex: "V1", "V2", "V3")
        """
        return f"V{self.version_number}"
    
    def get_toutes_versions(self):
        """
        Retourne toutes les versions de ce courrier (incluant lui-même si c'est le parent)
        """
        if self.courrier_parent:
            # Si c'est une version, retourner toutes les versions du parent
            return self.courrier_parent.versions.all().order_by('version_number')
        else:
            # Si c'est le parent, retourner toutes ses versions
            return self.versions.all().order_by('version_number')
    
    def get_version_actuelle(self):
        """
        Retourne la version actuelle/active d'un courrier
        """
        if self.courrier_parent:
            # Si c'est une version, chercher dans les versions du parent
            return self.courrier_parent.versions.filter(est_version_actuelle=True).first()
        else:
            # Si c'est le parent
            if self.est_version_actuelle:
                return self
            return self.versions.filter(est_version_actuelle=True).first()
    
    def creer_nouvelle_version(self, fichier, notes="", enregistre_par=None):
        """
        Créer une nouvelle version de ce courrier
        """
        # Déterminer le courrier parent
        parent = self.courrier_parent if self.courrier_parent else self
        
        # Trouver le numéro de version suivant
        derniere_version = parent.versions.order_by('-version_number').first()
        nouveau_numero = (derniere_version.version_number + 1) if derniere_version else 2
        
        # Désactiver toutes les versions précédentes
        parent.versions.update(est_version_actuelle=False)
        if not parent.courrier_parent:
            parent.est_version_actuelle = False
            parent.save()
        
        # Créer la nouvelle version
        nouvelle_version = Courrier.objects.create(
            courrier_parent=parent,
            version_number=nouveau_numero,
            est_version_actuelle=True,
            type_courrier=parent.type_courrier,
            date_reception=parent.date_reception,
            mode_reception=parent.mode_reception,
            date_envoi=parent.date_envoi,
            mode_envoi=parent.mode_envoi,
            date_circulation=parent.date_circulation,
            expediteur=parent.expediteur,
            destinataire=parent.destinataire,
            service_emetteur=parent.service_emetteur,
            service_destinataire=parent.service_destinataire,
            objet=parent.objet,
            reference=parent.reference,
            service_concerne=parent.service_concerne,
            statut=parent.statut,
            fichier=fichier,
            notes=notes,
            urgent=parent.urgent,
            enregistre_par=enregistre_par or parent.enregistre_par,
        )
        
        return nouvelle_version
    
    def soft_delete(self, user):
        """Archiver le courrier (soft delete)"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self):
        """Restaurer un courrier archivé"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    
    @staticmethod
    def get_service_code_from_name(service_name: str) -> str:
        """
        Mapper le nom d'un service vers son code correspondant
        @param service_name: Nom du service (ex: "Ressources Humaines", "Direction Générale")
        @return: Code du service (ex: "rh", "direction")
        """
        # Mapping exact des services
        service_mapping = {
            'Ressources Humaines': 'rh',
            'RH': 'rh',
            'Comptabilité': 'comptabilite', 
            'Direction': 'direction',
            'Direction Générale': 'direction',
            'DG': 'direction',
            'Service Technique': 'technique',
            'Technique': 'technique',
            'Commercial': 'commercial',
            'Juridique': 'juridique',
            'Informatique': 'informatique',
            'IT': 'informatique',
            'Logistique': 'logistique',
        }
        
        # Essayer correspondance exacte
        if service_name in service_mapping:
            return service_mapping[service_name]
        
        # Essayer correspondance partielle (insensible à la casse)
        service_name_lower = service_name.lower()
        for key, value in service_mapping.items():
            if key.lower() in service_name_lower or service_name_lower in key.lower():
                return value
        
        # Par défaut, retourner 'autre'
        return 'autre'


class FichierCourrierVersion(models.Model):
    """
    Modèle pour stocker les différentes versions d'un fichier de courrier.
    Permet de garder l'historique des modifications (signature, annotation, etc.)
    sans créer de nouvelles entrées de courrier.
    """
    courrier = models.ForeignKey(
        Courrier,
        on_delete=models.CASCADE,
        related_name='fichier_versions',
        help_text="Courrier auquel appartient cette version"
    )
    
    fichier = models.FileField(
        upload_to='courriers/versions/%Y/%m/',
        help_text="Fichier de cette version"
    )
    
    version_number = models.PositiveIntegerField(
        help_text="Numéro de version (1, 2, 3...)"
    )
    
    notes_version = models.TextField(
        blank=True,
        help_text="Notes décrivant cette version (ex: 'Signé par X', 'Annoté le...')"
    )
    
    est_version_actuelle = models.BooleanField(
        default=False,
        help_text="Indique si c'est la version active affichée"
    )
    
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions_courrier_crees',
        help_text="Utilisateur ayant créé cette version"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date et heure de création de cette version"
    )
    
    class Meta:
        ordering = ['-version_number']
        verbose_name = "Version de fichier courrier"
        verbose_name_plural = "Versions de fichiers courrier"
        unique_together = ['courrier', 'version_number']
    
    def __str__(self):
        return f"{self.courrier.numero_registre} - V{self.version_number}"


class PartageLog(models.Model):
    """
    Modèle pour tracer tous les partages de courriers
    Permet de garder un historique des partages par email ou WhatsApp
    """
    
    TYPE_PARTAGE_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    # Courrier partagé
    courrier = models.ForeignKey(
        Courrier,
        on_delete=models.CASCADE,
        related_name='partages',
        help_text="Courrier qui a été partagé"
    )
    
    # Type de partage
    type_partage = models.CharField(
        max_length=20,
        choices=TYPE_PARTAGE_CHOICES,
        help_text="Méthode de partage utilisée"
    )
    
    # Destinataire
    destinataire = models.CharField(
        max_length=255,
        help_text="Email ou numéro de téléphone du destinataire"
    )
    
    # Message optionnel
    message = models.TextField(
        blank=True,
        help_text="Message d'accompagnement du partage"
    )
    
    # Utilisateur qui a partagé
    partage_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='partages_effectues',
        help_text="Utilisateur ayant effectué le partage"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date et heure du partage"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Partage de courrier"
        verbose_name_plural = "Partages de courriers"
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['courrier', 'type_partage']),
        ]
    
    def __str__(self):
        return f"Partage {self.type_partage} - {self.courrier.numero_registre} vers {self.destinataire}"


# ============================================================================
# MODÈLE POUR L'AFFECTATION DES COURRIERS AUX UTILISATEURS
# ============================================================================

class AffectationCourrier(models.Model):
    """
    Modèle pour gérer l'affectation des courriers aux utilisateurs via la plateforme
    """
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('lu', 'Lu'),
        ('en_traitement', 'En traitement'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
        ('signe', 'Signé'),
    ]
    
    # Relations
    courrier = models.ForeignKey(Courrier, on_delete=models.CASCADE, related_name='affectations')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courriers_affectes')
    affecte_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='affectations_creees')
    
    # Informations
    note = models.TextField(blank=True, help_text="Note de l'affecteur")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    commentaire_traitement = models.TextField(blank=True, help_text="Commentaire de l'utilisateur lors du traitement")
    motif_rejet = models.TextField(blank=True, help_text="Motif en cas de rejet")
    
    # Métadonnées
    date_affectation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True, help_text="Date de première lecture")
    date_traitement = models.DateTimeField(null=True, blank=True, help_text="Date de validation/rejet/signature")
    
    class Meta:
        ordering = ['-date_affectation']
        verbose_name = 'Affectation de courrier'
        verbose_name_plural = 'Affectations de courriers'
        indexes = [
            models.Index(fields=['utilisateur', 'statut']),
            models.Index(fields=['-date_affectation']),
        ]
        # Pas de contrainte d'unicité car un même courrier peut être affecté à plusieurs utilisateurs
    
    def __str__(self):
        return f"{self.courrier.numero_registre} → {self.utilisateur.username} ({self.get_statut_display()})"
    
    def marquer_comme_lu(self):
        """Marque l'affectation comme lue"""
        if not self.date_lecture:
            from django.utils import timezone
            self.date_lecture = timezone.now()
            if self.statut == 'en_attente':
                self.statut = 'lu'
            self.save()
    
    def valider(self, commentaire=''):
        """Valide le courrier"""
        from django.utils import timezone
        self.statut = 'valide'
        self.commentaire_traitement = commentaire
        self.date_traitement = timezone.now()
        self.save()
        # Mettre à jour le statut du courrier vers "traité"
        self._update_courrier_statut()
    
    def rejeter(self, motif=''):
        """Rejette le courrier"""
        from django.utils import timezone
        self.statut = 'rejete'
        self.motif_rejet = motif
        self.date_traitement = timezone.now()
        self.save()
        # Mettre à jour le statut du courrier vers "traité"
        self._update_courrier_statut()
    
    def signer(self, commentaire=''):
        """Signe le courrier électroniquement"""
        from django.utils import timezone
        self.statut = 'signe'
        self.commentaire_traitement = commentaire
        self.date_traitement = timezone.now()
        self.save()
        # Mettre à jour le statut du courrier vers "traité"
        self._update_courrier_statut()
    
    def _update_courrier_statut(self):
        """
        Met à jour le statut du courrier associé à cette affectation.
        Si toutes les affectations ont été traitées (validé/rejeté/signé), 
        le courrier passe à "traité".
        """
        # Vérifier si toutes les affectations du courrier sont traitées
        affectations = self.courrier.affectations.all()
        statuts_traites = ['valide', 'rejete', 'signe']
        
        # Si toutes les affectations sont dans un statut "traité"
        if all(aff.statut in statuts_traites for aff in affectations):
            self.courrier.statut = 'traite'
            self.courrier.save()


class CommentaireCourrier(models.Model):
    """
    Modèle pour les commentaires sur les affectations de courriers
    """
    affectation = models.ForeignKey(AffectationCourrier, on_delete=models.CASCADE, related_name='commentaires')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'Commentaire'
        verbose_name_plural = 'Commentaires'
    
    def __str__(self):
        return f"Commentaire de {self.auteur.username} sur {self.affectation.courrier.numero_registre}"
