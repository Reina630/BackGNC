from django.db import models
from users.models import User


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
        ('brouillon', 'Brouillon'),
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
    
    # Référence de la structure externe (organisme, entreprise, etc.)
    reference_structure = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Référence de la structure externe (ex: N°ABC123 de l'organisme X)"
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
    
    # ===== RÉPONSE À UN COURRIER =====
    reponse_a = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reponses',
        help_text="Courrier original auquel ce courrier est une réponse"
    )

    # Contenu de la lettre (HTML) pour les brouillons rédigés sur la plateforme
    contenu_lettre = models.TextField(
        blank=True,
        null=True,
        help_text="Contenu HTML de la lettre rédigée sur la plateforme"
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
        le numéro de registre au format TYPE-ANNÉE-MOIS-NNNN
        Ex: ENT-2026-03-0001 (entrant), SORT-2026-03-0001 (sortant), INT-2026-03-0001 (interne)
        Le compteur est indépendant par type, par année et par mois.
        """
        if not self.numero_registre:
            from django.utils import timezone
            now = timezone.now()
            year = now.year
            month = now.month

            # Préfixe selon le type de courrier
            prefix_map = {
                'entrant': 'CE',
                'sortant': 'CS',
                'interne': 'CI',
            }
            prefix = prefix_map.get(self.type_courrier, 'COU')

            # Dernier numéro pour ce type, cette année et ce mois
            last_courrier = Courrier.objects.filter(
                numero_registre__startswith=f"{prefix}-{year}-{month:02d}-"
            ).order_by('-numero_registre').first()

            if last_courrier:
                # Extraire la partie numérique (4ème segment : TYPE-ANNÉE-MOIS-NNNN)
                last_number = int(last_courrier.numero_registre.split('-')[3])
                new_number = last_number + 1
            else:
                # Premier courrier de ce type pour ce mois
                new_number = 1

            # Générer le numéro avec padding (ex: ENT-2026-03-0001)
            self.numero_registre = f"{prefix}-{year}-{month:02d}-{new_number:04d}"
        
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



class CourrierPieceJointe(models.Model):
    """
    Pièces jointes multiples d'un courrier.
    Un courrier peut avoir plusieurs fichiers attachés.
    """
    courrier = models.ForeignKey(
        Courrier,
        on_delete=models.CASCADE,
        related_name='pieces_jointes',
        help_text="Courrier auquel appartient cette pièce jointe"
    )

    fichier = models.FileField(
        upload_to='courriers/pieces_jointes/%Y/%m/',
        help_text="Fichier joint"
    )

    nom_fichier = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom original du fichier"
    )

    file_type = models.CharField(
        max_length=20,
        default='pdf',
        help_text="Type de fichier (pdf, image, etc.)"
    )

    file_size = models.BigIntegerField(
        default=0,
        help_text="Taille du fichier en octets"
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces_jointes_uploadees',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"

    def __str__(self):
        return f"{self.courrier.numero_registre} - {self.nom_fichier}"


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



class ActionLog(models.Model):
    """
    Modèle générique pour logger toutes les actions des utilisateurs sur la plateforme.
    Sert de journal d'audit complet.
    """
    TYPE_ACTION_CHOICES = [
        # Courriers
        ('courrier_create', 'Création de courrier'),
        ('courrier_update', 'Modification de courrier'),
        ('courrier_delete', 'Suppression de courrier'),
        ('courrier_restore', 'Restauration de courrier'),
        ('courrier_archive', 'Archivage de courrier'),
        
        # Affectations
        ('affectation_create', 'Affectation de courrier'),
        ('affectation_accuse', 'Accusé de réception'),
        ('affectation_start', 'Début de traitement'),
        ('affectation_validate', 'Validation'),
        ('affectation_reject', 'Rejet'),
        ('affectation_sign', 'Signature'),
        ('affectation_renvoye', 'Renvoi de courrier'),
        ('affectation_repondre', 'Réponse au courrier'),
        
        # Partages
        ('partage_email', 'Partage par email'),
        ('partage_whatsapp', 'Partage par WhatsApp'),
        
        # Commentaires
        ('commentaire_add', 'Ajout de commentaire'),
        
        # Utilisateurs
        ('user_login', 'Connexion'),
        ('user_logout', 'Déconnexion'),
        ('user_create', 'Création d\'utilisateur'),
        ('user_update', 'Modification d\'utilisateur'),
        ('user_delete', 'Suppression d\'utilisateur'),
        
        # Autres
        ('urgent_mark', 'Marquage urgent'),
        ('urgent_unmark', 'Retrait marquage urgent'),
    ]
    
    # Informations de l'action
    action_type = models.CharField(max_length=50, choices=TYPE_ACTION_CHOICES)
    description = models.TextField()  # Description lisible de l'action
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='actions_log')
    utilisateur_username = models.CharField(max_length=150)  # Backup si l'utilisateur est supprimé
    utilisateur_nom_complet = models.CharField(max_length=255, blank=True)
    
    # Cibles de l'action (optionnel, selon le type d'action)
    courrier = models.ForeignKey('Courrier', on_delete=models.SET_NULL, null=True, blank=True, related_name='actions_log')
    courrier_numero = models.CharField(max_length=100, blank=True)  # Backup
    
    # Métadonnées
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Données supplémentaires (JSON pour flexibilité)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Log d\'action'
        verbose_name_plural = 'Logs d\'actions'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
            models.Index(fields=['utilisateur', '-timestamp']),
        ]
    
    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.utilisateur_username} - {self.get_action_type_display()}"
    
    @classmethod
    def log_action(cls, action_type, utilisateur, description, courrier=None, request=None, **metadata):
        """
        Méthode utilitaire pour créer un log d'action facilement.
        
        Exemple:
            ActionLog.log_action(
                action_type='courrier_create',
                utilisateur=request.user,
                description=f"Création du courrier {courrier.numero_registre}",
                courrier=courrier,
                request=request
            )
        """
        log = cls(
            action_type=action_type,
            description=description,
            utilisateur=utilisateur,
            utilisateur_username=utilisateur.username,
            utilisateur_nom_complet=utilisateur.get_full_name() or utilisateur.username,
            courrier=courrier,
            courrier_numero=courrier.numero_registre if courrier else '',
            metadata=metadata
        )
        
        # Extraire les infos de la requête HTTP si disponible
        if request:
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                log.ip_address = x_forwarded_for.split(',')[0]
            else:
                log.ip_address = request.META.get('REMOTE_ADDR')
            
            # Get user agent
            log.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limité à 500 chars
        
        log.save()
        return log




