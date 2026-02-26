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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


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
    
    # Date d'envoi (pour courrier sortant)
    date_envoi = models.DateField(
        null=True, 
        blank=True, 
        help_text="Date d'envoi du courrier sortant"
    )
    
    # ===== PARTIES PRENANTES =====
    expediteur = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Nom ou organisation de l'expéditeur"
    )
    
    destinataire = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Nom ou organisation du destinataire"
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
        (date de réception pour entrant, date d'envoi pour sortant)
        """
        if self.type_courrier == 'entrant':
            return self.date_reception
        else:
            return self.date_envoi
    
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
            date_envoi=parent.date_envoi,
            expediteur=parent.expediteur,
            destinataire=parent.destinataire,
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
