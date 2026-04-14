"""
Script de génération de courriers PDF réalistes pour la démo
Génère 6 courriers professionnels couvrant 3 scénarios de test :
1. Archivage direct avec OCR (3 courriers)
2. Affectation informative simple (1 courrier)
3. Traitement avec réponse (2 courriers liés)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from datetime import datetime, timedelta
import os

# Couleurs de l'entreprise
COLOR_PRIMARY = HexColor('#7c2235')
COLOR_SECONDARY = HexColor('#2c3e50')
COLOR_LIGHT = HexColor('#ecf0f1')

def create_letterhead_imanged(c, width, height):
    """En-tête IMANGED - Pour courriers internes et sortants"""
    # Bandeau supérieur
    c.setFillColor(COLOR_PRIMARY)
    c.rect(0, height - 3*cm, width, 3*cm, fill=True, stroke=False)
    
    # Logo/Nom de l'entreprise
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(2*cm, height - 2*cm, "IMANGED")
    
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height - 2.5*cm, "Système de Gestion Électronique des Documents")
    
    # Coordonnées
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 2*cm, height - 1.5*cm, "123 Avenue de l'Innovation")
    c.drawRightString(width - 2*cm, height - 1.8*cm, "Casablanca, Maroc")
    c.drawRightString(width - 2*cm, height - 2.1*cm, "Tél: +212 5 22 XX XX XX")
    c.drawRightString(width - 2*cm, height - 2.4*cm, "contact@imanged.ma")
    
    # Ligne de séparation
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(2)
    c.line(2*cm, height - 3.5*cm, width - 2*cm, height - 3.5*cm)

def create_letterhead_bureau_equipement(c, width, height):
    """En-tête Bureau Équipement Pro - Simple et professionnel"""
    # Bandeau simple
    c.setFillColor(HexColor('#34495e'))
    c.rect(0, height - 2.5*cm, width, 2.5*cm, fill=True, stroke=False)
    
    # Nom de l'entreprise
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(2*cm, height - 1.7*cm, "Bureau Équipement Pro")
    
    c.setFont("Helvetica", 9)
    c.drawString(2*cm, height - 2.1*cm, "Fournitures et Mobilier de Bureau")
    
    # Coordonnées à droite
    c.setFont("Helvetica", 7)
    c.drawRightString(width - 2*cm, height - 1.3*cm, "45 Rue des Artisans, Casablanca")
    c.drawRightString(width - 2*cm, height - 1.6*cm, "Tél: +212 5 22 45 67 89")
    c.drawRightString(width - 2*cm, height - 1.9*cm, "contact@bureau-equipement.ma")
    
    # Ligne de séparation
    c.setStrokeColor(HexColor('#e67e22'))
    c.setLineWidth(3)
    c.line(2*cm, height - 3*cm, width - 2*cm, height - 3*cm)

def create_letterhead_ministere(c, width, height):
    """En-tête Ministère du Travail - Style officiel gouvernemental"""
    # Bordure dorée top
    c.setFillColor(HexColor('#d4af37'))
    c.rect(0, height - 0.5*cm, width, 0.5*cm, fill=True, stroke=False)
    
    # Fond gris clair
    c.setFillColor(HexColor('#f8f9fa'))
    c.rect(0, height - 3*cm, width, 2.5*cm, fill=True, stroke=False)
    
    # Armoiries simulées (cercle)
    c.setFillColor(HexColor('#c0392b'))
    c.circle(3*cm, height - 1.8*cm, 0.7*cm, fill=True, stroke=False)
    c.setFillColor(HexColor('#f1c40f'))
    c.circle(3*cm, height - 1.8*cm, 0.5*cm, fill=True, stroke=False)
    
    # Nom du ministère
    c.setFillColor(HexColor('#2c3e50'))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(4.5*cm, height - 1.4*cm, "ROYAUME DU MAROC")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(4.5*cm, height - 1.9*cm, "Ministère du Travail et de l'Insertion Professionnelle")
    c.setFont("Helvetica", 10)
    c.drawString(4.5*cm, height - 2.4*cm, "Direction Régionale de Casablanca-Settat")
    
    # Ligne de séparation
    c.setStrokeColor(HexColor('#d4af37'))
    c.setLineWidth(2)
    c.line(2*cm, height - 3.3*cm, width - 2*cm, height - 3.3*cm)

def create_letterhead_techschool(c, width, height):
    """En-tête TechSchool Morocco - Style moderne/tech"""
    # Dégradé simulé avec bandes
    c.setFillColor(HexColor('#3498db'))
    c.rect(0, height - 3*cm, width, 3*cm, fill=True, stroke=False)
    
    c.setFillColor(HexColor('#2980b9'))
    c.rect(0, height - 2*cm, width, 1*cm, fill=True, stroke=False)
    
    # Logo stylisé (carrés)
    c.setFillColor(HexColor('#ffffff'))
    c.rect(2*cm, height - 2.3*cm, 0.4*cm, 0.4*cm, fill=True, stroke=False)
    c.rect(2.5*cm, height - 2.3*cm, 0.4*cm, 0.4*cm, fill=True, stroke=False)
    c.rect(2*cm, height - 2.8*cm, 0.4*cm, 0.4*cm, fill=True, stroke=False)
    c.rect(2.5*cm, height - 2.8*cm, 0.4*cm, 0.4*cm, fill=True, stroke=False)
    
    # Nom
    c.setFont("Helvetica-Bold", 22)
    c.drawString(3.5*cm, height - 2.2*cm, "TechSchool Morocco")
    
    c.setFont("Helvetica", 11)
    c.drawString(3.5*cm, height - 2.7*cm, "Centre de Formation & Innovation Digitale")
    
    # Coordonnées
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 2*cm, height - 1.8*cm, "89 Boulevard Moulay Slimane, Casablanca")
    c.drawRightString(width - 2*cm, height - 2.1*cm, "Tél: +212 5 22 98 76 54")
    c.drawRightString(width - 2*cm, height - 2.4*cm, "www.techschool.ma")
    
    # Ligne de séparation
    c.setStrokeColor(HexColor('#f39c12'))
    c.setLineWidth(4)
    c.line(2*cm, height - 3.3*cm, width - 2*cm, height - 3.3*cm)

def create_footer(c, width, height, page_num=1):
    """Crée le pied de page"""
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(1)
    c.line(2*cm, 2*cm, width - 2*cm, 2*cm)
    
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 1.5*cm, f"IMANGED - Document confidentiel - Page {page_num}")

def generate_courrier_1(output_path):
    """
    Courrier 1: Demande de fournitures bureau
    Type: Entrant (de Bureau Équipement Pro)
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    create_letterhead_bureau_equipement(c, width, height)
    
    # Informations du courrier (bien visibles pour l'OCR)
    y_pos = height - 4.5*cm
    
    # Cadre avec les métadonnées
    c.setFillColor(COLOR_LIGHT)
    c.rect(2*cm, y_pos - 2.5*cm, width - 4*cm, 2.3*cm, fill=True, stroke=True)
    
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 10)
    
    y_meta = y_pos - 0.7*cm
    c.drawString(2.5*cm, y_meta, "N° REGISTRE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "ENT-2024-001")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12*cm, y_meta, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(14*cm, y_meta, "15/03/2024")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "RÉFÉRENCE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "DF/BUR/2024/047")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "OBJET:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "Demande de fournitures de bureau - Service Comptabilité")
    
    # Expéditeur
    y_pos -= 4*cm
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "EXPÉDITEUR:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Bureau Équipement Pro")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "45 Rue des Artisans, Casablanca")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "Tél: +212 5 22 XX XX XX")
    
    # Destinataire
    y_pos -= 1.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "DESTINATAIRE:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Direction des Achats")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "IMANGED")
    
    # Corps du courrier
    y_pos -= 1.5*cm
    c.setFont("Helvetica", 10)
    
    content = [
        "Madame, Monsieur,",
        "",
        "Suite à votre demande du 10 mars 2024, nous avons le plaisir de vous transmettre notre",
        "proposition commerciale pour la fourniture de matériel de bureau.",
        "",
        "Notre offre comprend:",
        "  • Ramettes de papier A4 (80g) - Quantité: 50 cartons",
        "  • Stylos à bille (bleu/noir/rouge) - Quantité: 200 unités",
        "  • Classeurs à levier - Quantité: 100 unités",
        "  • Agrafeuses professionnelles - Quantité: 20 unités",
        "",
        "Prix total HT: 12 500,00 DH",
        "TVA 20%: 2 500,00 DH",
        "Total TTC: 15 000,00 DH",
        "",
        "Délai de livraison: 5 jours ouvrables",
        "Conditions de paiement: 30 jours net",
        "",
        "Nous restons à votre disposition pour tout complément d'information.",
        "",
        "Cordialement,",
        "",
        "Ahmed BENCHEKROUN",
        "Responsable Commercial",
        "Bureau Équipement Pro"
    ]
    
    for line in content:
        c.drawString(2*cm, y_pos, line)
        y_pos -= 0.5*cm
    
    create_footer(c, width, height)
    c.save()
    print(f"✓ Courrier 1 généré: {output_path}")

def generate_courrier_2(output_path):
    """
    Courrier 2: Convocation réunion
    Type: Interne (IMANGED)
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    create_letterhead_imanged(c, width, height)
    
    y_pos = height - 5*cm
    
    # Cadre métadonnées
    c.setFillColor(COLOR_LIGHT)
    c.rect(2*cm, y_pos - 2.5*cm, width - 4*cm, 2.3*cm, fill=True, stroke=True)
    
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 10)
    
    y_meta = y_pos - 0.7*cm
    c.drawString(2.5*cm, y_meta, "N° REGISTRE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "INT-2024-015")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12*cm, y_meta, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(14*cm, y_meta, "20/03/2024")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "RÉFÉRENCE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "DG/RH/2024/089")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "OBJET:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "Convocation - Réunion annuelle de planification stratégique")
    
    # Expéditeur
    y_pos -= 4*cm
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "ÉMETTEUR:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Direction Générale")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "IMANGED")
    
    # Destinataires
    y_pos -= 1.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "DESTINATAIRES:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Tous les chefs de service")
    
    # Corps
    y_pos -= 1.5*cm
    c.setFont("Helvetica", 10)
    
    content = [
        "Mesdames, Messieurs les Chefs de Service,",
        "",
        "J'ai l'honneur de vous convoquer à la réunion annuelle de planification stratégique qui se",
        "tiendra selon les modalités suivantes:",
        "",
        "  DATE: Mercredi 25 mars 2024",
        "  HEURE: 09h00 - 13h00",
        "  LIEU: Salle de conférence - Bâtiment principal",
        "",
        "ORDRE DU JOUR:",
        "",
        "  1. Bilan de l'année 2024 (30 min)",
        "  2. Présentation des objectifs 2025 (45 min)",
        "  3. Budget prévisionnel par service (45 min)",
        "  4. Pause café (15 min)",
        "  5. Nouveaux projets et initiatives (60 min)",
        "  6. Questions diverses (30 min)",
        "",
        "DOCUMENTS À PRÉPARER:",
        "  • Rapport d'activité 2024 de votre service",
        "  • Proposition de budget 2025",
        "  • Liste des besoins en ressources humaines",
        "",
        "Merci de confirmer votre présence avant le 22 mars 2024 par email à:",
        "secretariat.dg@imanged.ma",
        "",
        "Cordialement,",
        "",
        "Fatima ALAOUI",
        "Directrice Générale"
    ]
    
    for line in content:
        c.drawString(2*cm, y_pos, line)
        y_pos -= 0.5*cm
    
    create_footer(c, width, height)
    c.save()
    print(f"✓ Courrier 2 généré: {output_path}")

def generate_courrier_3(output_path):
    """
    Courrier 3: Réponse à une réclamation client
    Type: Sortant (IMANGED)
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    create_letterhead_imanged(c, width, height)
    
    y_pos = height - 5*cm
    
    # Cadre métadonnées
    c.setFillColor(COLOR_LIGHT)
    c.rect(2*cm, y_pos - 2.5*cm, width - 4*cm, 2.3*cm, fill=True, stroke=True)
    
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 10)
    
    y_meta = y_pos - 0.7*cm
    c.drawString(2.5*cm, y_meta, "N° REGISTRE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "SOR-2024-042")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12*cm, y_meta, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(14*cm, y_meta, "22/03/2024")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "RÉFÉRENCE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "SAV/CLIENT/2024/125")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "OBJET:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "Réponse à réclamation - Dossier client n°45789")
    
    # Expéditeur
    y_pos -= 4*cm
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "EXPÉDITEUR:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Service Client")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "IMANGED")
    
    # Destinataire
    y_pos -= 1.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "DESTINATAIRE:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Monsieur Youssef TAZI")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "Société DIGISOFT")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "78 Boulevard Zerktouni, Casablanca")
    
    # Corps
    y_pos -= 1.5*cm
    c.setFont("Helvetica", 10)
    
    content = [
        "Monsieur,",
        "",
        "Nous accusons réception de votre courrier du 18 mars 2024 concernant un",
        "dysfonctionnement de notre application IMANGED.",
        "",
        "Après analyse approfondie de votre réclamation, nous tenons à vous présenter nos",
        "excuses pour les désagréments occasionnés.",
        "",
        "PROBLÈME IDENTIFIÉ:",
        "  Le module de génération de rapports présentait effectivement un bug lors de",
        "  l'export de documents volumineux (>50 pages).",
        "",
        "ACTIONS CORRECTIVES:",
        "  • Correction du bug déployée le 20/03/2024",
        "  • Tests de validation effectués avec succès",
        "  • Mise à jour automatique planifiée pour votre installation",
        "",
        "MESURES COMPENSATOIRES:",
        "  • Extension gratuite de 3 mois de votre licence Premium",
        "  • Session de formation personnalisée offerte",
        "  • Support prioritaire pendant 6 mois",
        "",
        "Notre équipe technique reste à votre disposition pour toute question au:",
        "support@imanged.ma ou +212 5 22 XX XX XX",
        "",
        "Nous vous remercions de votre confiance et compréhension.",
        "",
        "Veuillez agréer, Monsieur, l'expression de nos salutations distinguées.",
        "",
        "",
        "Karim BENJELLOUN",
        "Responsable Service Client",
        "IMANGED"
    ]
    
    for line in content:
        c.drawString(2*cm, y_pos, line)
        y_pos -= 0.5*cm
    
    create_footer(c, width, height)
    c.save()
    print(f"✓ Courrier 3 généré: {output_path}")

def generate_courrier_4(output_path):
    """
    Courrier 4: Information simple - Changement d'horaires
    Type: Entrant (de Ministère du Travail)
    Scénario: Affectation à un service à titre informatif puis archivage
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    create_letterhead_ministere(c, width, height)
    
    y_pos = height - 4.8*cm
    
    # Cadre métadonnées
    c.setFillColor(COLOR_LIGHT)
    c.rect(2*cm, y_pos - 2.5*cm, width - 4*cm, 2.3*cm, fill=True, stroke=True)
    
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 10)
    
    y_meta = y_pos - 0.7*cm
    c.drawString(2.5*cm, y_meta, "N° REGISTRE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "ENT-2024-025")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12*cm, y_meta, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(14*cm, y_meta, "25/03/2024")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "RÉFÉRENCE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "MIN/TRAV/2024/158")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "OBJET:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "Circulaire - Nouveaux horaires d'été 2024")
    
    # Expéditeur
    y_pos -= 4*cm
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "EXPÉDITEUR:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Ministère du Travail")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "Direction Régionale de Casablanca")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "Place Mohammed V, Casablanca")
    
    # Destinataire
    y_pos -= 1.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "DESTINATAIRE:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Toutes les entreprises de la région")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "(Communication à diffuser)")
    
    # Corps
    y_pos -= 1.5*cm
    c.setFont("Helvetica", 10)
    
    content = [
        "Mesdames, Messieurs,",
        "",
        "Nous avons l'honneur de porter à votre connaissance les nouveaux horaires de travail",
        "applicables pendant la période estivale 2024.",
        "",
        "PÉRIODE CONCERNÉE:",
        "  Du 1er juin 2024 au 30 septembre 2024",
        "",
        "NOUVEAUX HORAIRES RECOMMANDÉS:",
        "  • Lundi au Jeudi: 08h00 - 16h00 (pause 12h00-13h00)",
        "  • Vendredi: 08h00 - 12h00",
        "",
        "OBJECTIFS:",
        "  • Amélioration du bien-être des employés durant les fortes chaleurs",
        "  • Optimisation de la consommation énergétique",
        "  • Meilleure conciliation vie professionnelle/personnelle",
        "",
        "DISPOSITIONS:",
        "  Les entreprises sont invitées à adapter ces horaires selon leurs contraintes",
        "  opérationnelles tout en respectant le volume horaire hebdomadaire réglementaire.",
        "",
        "Cette circulaire est transmise à titre informatif. Aucune action particulière n'est",
        "requise de votre part, sauf si vous souhaitez solliciter un avis technique auprès",
        "de nos services.",
        "",
        "Pour toute information complémentaire:",
        "contact.regional@ministere-travail.ma",
        "",
        "Cordialement,",
        "",
        "Hassan NACIRI",
        "Directeur Régional",
        "Ministère du Travail - Casablanca"
    ]
    
    for line in content:
        c.drawString(2*cm, y_pos, line)
        y_pos -= 0.5*cm
    
    create_footer(c, width, height)
    c.save()
    print(f"✓ Courrier 4 généré: {output_path}")

def generate_courrier_5(output_path):
    """
    Courrier 5: Demande de partenariat
    Type: Entrant (de TechSchool Morocco)
    Scénario: Affectation avec demande de traitement et réponse
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    create_letterhead_techschool(c, width, height)
    
    y_pos = height - 4.8*cm
    
    # Cadre métadonnées
    c.setFillColor(COLOR_LIGHT)
    c.rect(2*cm, y_pos - 2.5*cm, width - 4*cm, 2.3*cm, fill=True, stroke=True)
    
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 10)
    
    y_meta = y_pos - 0.7*cm
    c.drawString(2.5*cm, y_meta, "N° REGISTRE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "ENT-2024-033")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12*cm, y_meta, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(14*cm, y_meta, "28/03/2024")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "RÉFÉRENCE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "TECH/INNOV/2024/089")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "OBJET:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "Demande de partenariat - Formation digitale")
    
    # Badge "RÉPONSE REQUISE"
    c.setFillColor(HexColor('#e74c3c'))
    c.rect(width - 6*cm, y_pos - 1*cm, 3.5*cm, 0.8*cm, fill=True, stroke=False)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width - 4.25*cm, y_pos - 0.7*cm, "RÉPONSE REQUISE")
    
    # Expéditeur
    y_pos -= 4.5*cm
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "EXPÉDITEUR:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "TechSchool Morocco")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "Centre de Formation Digitale")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "89 Boulevard Moulay Slimane, Casablanca")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "Tél: +212 5 22 XX XX XX")
    
    # Destinataire
    y_pos -= 1.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "DESTINATAIRE:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Direction des Ressources Humaines")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "IMANGED")
    
    # Corps
    y_pos -= 1.5*cm
    c.setFont("Helvetica", 10)
    
    content = [
        "Madame, Monsieur,",
        "",
        "TechSchool Morocco, leader dans la formation digitale, souhaite établir un partenariat",
        "stratégique avec IMANGED pour développer les compétences de vos équipes.",
        "",
        "NOTRE PROPOSITION:",
        "",
        "1. FORMATIONS PROPOSÉES:",
        "   • Gestion électronique de documents avancée (3 jours)",
        "   • Transformation digitale des processus métiers (2 jours)",
        "   • Cybersécurité et protection des données (2 jours)",
        "   • Analytics et reporting digital (1 jour)",
        "",
        "2. MODALITÉS:",
        "   • Sessions en présentiel ou à distance",
        "   • Adaptation du contenu à vos besoins spécifiques",
        "   • Certification reconnue à l'issue de la formation",
        "   • Support post-formation pendant 3 mois",
        "",
        "3. TARIFS PRÉFÉRENTIELS PARTENAIRE:",
        "   • 20% de réduction sur toutes nos formations",
        "   • Gratuité pour 1 participant à partir de 5 inscrits",
        "   • Plan de paiement échelonné possible",
        "",
        "PROCHAINES ÉTAPES:",
        "Nous serions ravis de vous présenter notre offre détaillée lors d'un rendez-vous.",
        "Merci de nous confirmer votre intérêt et vos disponibilités avant le 15 avril 2024.",
        "",
        "Dans l'attente de vous lire,",
        "",
        "Salma BENNANI",
        "Directrice Commerciale",
        "TechSchool Morocco",
        "Email: s.bennani@techschool.ma"
    ]
    
    for line in content:
        c.drawString(2*cm, y_pos, line)
        y_pos -= 0.5*cm
    
    create_footer(c, width, height)
    c.save()
    print(f"✓ Courrier 5 généré: {output_path}")

def generate_courrier_6(output_path):
    """
    Courrier 6: Réponse à la demande de partenariat
    Type: Sortant (IMANGED)
    Scénario: Réponse positive avec proposition de RDV
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    create_letterhead_imanged(c, width, height)
    
    y_pos = height - 5*cm
    
    # Cadre métadonnées
    c.setFillColor(COLOR_LIGHT)
    c.rect(2*cm, y_pos - 2.5*cm, width - 4*cm, 2.3*cm, fill=True, stroke=True)
    
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 10)
    
    y_meta = y_pos - 0.7*cm
    c.drawString(2.5*cm, y_meta, "N° REGISTRE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "SOR-2024-055")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12*cm, y_meta, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(14*cm, y_meta, "05/04/2024")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "RÉFÉRENCE:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "RH/FORM/2024/012")
    
    y_meta -= 0.6*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, y_meta, "OBJET:")
    c.setFont("Helvetica", 10)
    c.drawString(5.5*cm, y_meta, "RE: Demande de partenariat - Accord de principe")
    
    # Référence au courrier précédent
    y_pos -= 4*cm
    c.setFillColor(HexColor('#3498db'))
    c.rect(2*cm, y_pos - 0.7*cm, width - 4*cm, 0.6*cm, fill=True, stroke=False)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(2.5*cm, y_pos - 0.4*cm, "En réponse à votre courrier réf: TECH/INNOV/2024/089 du 28/03/2024")
    
    # Expéditeur
    y_pos -= 1.5*cm
    c.setFillColor(COLOR_SECONDARY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "EXPÉDITEUR:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Direction des Ressources Humaines")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "IMANGED")
    
    # Destinataire
    y_pos -= 1.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y_pos, "DESTINATAIRE:")
    
    c.setFont("Helvetica", 10)
    y_pos -= 0.5*cm
    c.drawString(2*cm, y_pos, "Madame Salma BENNANI")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "Directrice Commerciale")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "TechSchool Morocco")
    y_pos -= 0.4*cm
    c.drawString(2*cm, y_pos, "89 Boulevard Moulay Slimane, Casablanca")
    
    # Corps
    y_pos -= 1.5*cm
    c.setFont("Helvetica", 10)
    
    content = [
        "Madame,",
        "",
        "Nous avons bien reçu votre proposition de partenariat du 28 mars 2024 et vous en",
        "remercions vivement.",
        "",
        "Après étude de votre offre par notre comité de direction, nous avons le plaisir de vous",
        "informer de notre ACCORD DE PRINCIPE pour établir ce partenariat.",
        "",
        "POINTS D'INTÉRÊT PARTICULIER:",
        "  • Formation GED avancée (priorité haute)",
        "  • Transformation digitale des processus",
        "  • Cybersécurité (dans le cadre de notre mise en conformité RGPD)",
        "",
        "BESOINS IMMÉDIATS:",
        "  • 15 collaborateurs à former en priorité",
        "  • Démarrage souhaité: Mai 2024",
        "  • Préférence pour sessions en présentiel",
        "",
        "PROCHAINE ÉTAPE:",
        "Nous vous proposons une réunion de cadrage pour:",
        "  1. Détailler nos besoins spécifiques",
        "  2. Adapter le programme de formation",
        "  3. Établir un calendrier précis",
        "  4. Finaliser les aspects contractuels",
        "",
        "Nos disponibilités:",
        "  • Mardi 16 avril 2024 à 10h00",
        "  • Jeudi 18 avril 2024 à 14h00",
        "  • Vendredi 19 avril 2024 à 09h30",
        "",
        "Merci de nous confirmer la date qui vous convient.",
        "",
        "Dans l'attente de notre collaboration,",
        "",
        "Nadia KHALDI",
        "Directrice des Ressources Humaines",
        "IMANGED",
        "Email: n.khaldi@imanged.ma",
        "Tél: +212 5 22 XX XX XX"
    ]
    
    for line in content:
        c.drawString(2*cm, y_pos, line)
        y_pos -= 0.5*cm
    
    create_footer(c, width, height)
    c.save()
    print(f"✓ Courrier 6 généré: {output_path}")

def main():
    """Génère tous les courriers de démo"""
    output_dir = os.path.join(os.path.dirname(__file__), "demo_courriers")
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "="*70)
    print("  GÉNÉRATION DES COURRIERS DE DÉMO - Scénarios de test")
    print("="*70 + "\n")
    
    # Scénario 1: Archivage direct (3 courriers)
    print("📦 SCÉNARIO 1: Archivage direct (OCR)")
    print("-" * 70)
    courrier_1 = os.path.join(output_dir, "COURRIER_1_Demande_Fournitures.pdf")
    courrier_2 = os.path.join(output_dir, "COURRIER_2_Convocation_Reunion.pdf")
    courrier_3 = os.path.join(output_dir, "COURRIER_3_Reponse_Reclamation.pdf")
    
    generate_courrier_1(courrier_1)
    generate_courrier_2(courrier_2)
    generate_courrier_3(courrier_3)
    
    # Scénario 2: Affectation informative simple
    print("\n📋 SCÉNARIO 2: Affectation à titre informatif")
    print("-" * 70)
    courrier_4 = os.path.join(output_dir, "COURRIER_4_Info_Horaires_Ete.pdf")
    generate_courrier_4(courrier_4)
    
    # Scénario 3: Courrier avec demande de réponse
    print("\n💬 SCÉNARIO 3: Traitement avec réponse")
    print("-" * 70)
    courrier_5 = os.path.join(output_dir, "COURRIER_5_Demande_Partenariat.pdf")
    courrier_6 = os.path.join(output_dir, "COURRIER_6_Reponse_Partenariat.pdf")
    generate_courrier_5(courrier_5)
    generate_courrier_6(courrier_6)
    
    print("\n" + "="*70)
    print(f"✅ 6 courriers générés dans: {output_dir}")
    print("="*70 + "\n")
    
    print("📖 GUIDE DES SCÉNARIOS DE DÉMO:\n")
    
    print("1️⃣  ARCHIVAGE DIRECT (Courriers 1-3):")
    print("   → Montre la puissance de l'OCR")
    print("   → Archiver directement 3 anciens courriers")
    print("   → L'OCR extrait: N°, Date, Référence, Objet, Expéditeur/Destinataire\n")
    
    print("2️⃣  AFFECTATION INFORMATIVE (Courrier 4):")
    print("   → Courrier d'information simple")
    print("   → Affecter au service concerné à titre informatif")
    print("   → Marquer comme lu et archiver")
    print("   → Workflow: Création → Affectation → Lecture → Archive\n")
    
    print("3️⃣  TRAITEMENT AVEC RÉPONSE (Courriers 5-6):")
    print("   → Courrier 5: Demande de partenariat (entrant)")
    print("   → Affecter au responsable RH pour traitement")
    print("   → Créer le courrier 6 en réponse (sortant)")
    print("   → Lier les 2 courriers, valider et signer")
    print("   → Workflow: Réception → Affectation → Traitement → Réponse → Validation\n")
    
    print("✨ Vos courriers sont prêts pour la démo !\n")

if __name__ == "__main__":
    main()
